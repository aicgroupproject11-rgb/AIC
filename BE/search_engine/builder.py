from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .domains import DEFAULT_TAXONOMY_PATH, DomainCatalog
from .embedding import get_encoder
from .exceptions import IndexBuildError
from .indexer import DEFAULT_INDEX_DIR, INDEX_FORMAT_VERSION
from .manifest import ManifestRecord, group_by_video, load_manifest
from .objects import load_object_terms, resolve_object_file


@dataclass(frozen=True)
class BuildOptions:
    pca_dimensions: int = 24
    pca_sample_size: int = 50_000
    transform_batch_size: int = 8_192
    domains_per_frame: int = 2
    object_min_score: float = 0.25
    object_max_terms: int = 20


def build_search_index(
    *,
    data_root: Path | str,
    manifest_path: Path | str | None = None,
    index_dir: Path | str | None = None,
    taxonomy_path: Path | str | None = None,
    options: BuildOptions | None = None,
    encoder=None,
) -> dict:
    """Build a persistent hybrid R-tree index from official AIC artifacts."""
    data_root = Path(data_root).resolve()
    manifest_path = Path(manifest_path or data_root / "manifest.csv").resolve()
    index_dir = Path(index_dir or os.getenv("KIS_INDEX_ROOT", DEFAULT_INDEX_DIR)).resolve()
    taxonomy_path = Path(taxonomy_path or os.getenv("KIS_DOMAIN_TAXONOMY", DEFAULT_TAXONOMY_PATH)).resolve()
    options = options or BuildOptions()
    records = load_manifest(manifest_path)
    grouped = group_by_video(records)
    catalog = DomainCatalog.load(taxonomy_path)

    temp_dir = index_dir.with_name(f".{index_dir.name}.building")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    try:
        shutil.copyfile(taxonomy_path, temp_dir / "taxonomy.json")
        dimension = _write_full_vectors(temp_dir, data_root, records, grouped)
        full_vectors = np.load(temp_dir / "full_vectors.npy", mmap_mode="r")

        encoder = encoder or get_encoder()
        prototypes = np.asarray(encoder.encode_texts(catalog.prompts), dtype=np.float32)
        prototypes = _normalize_rows(prototypes)
        if prototypes.shape != (len(catalog.domains), dimension):
            raise IndexBuildError(
                "CLIP model không tương thích clip-features-32: "
                f"prototype={prototypes.shape}, feature_dim={dimension}. "
                "Kiểm tra KIS_CLIP_MODEL/KIS_CLIP_PRETRAINED."
            )
        np.save(temp_dir / "domain_prototypes.npy", prototypes)

        vocabulary = _write_object_bags_and_domains(
            temp_dir, data_root, records, catalog, options
        )
        _write_bow_csr(temp_dir, vocabulary)
        _fit_and_transform_pca(temp_dir, full_vectors, options)
        _write_records(temp_dir, records)
        tree_files, tree_counts = _build_rtrees(temp_dir, records, catalog, options)

        metadata = {
            "format_version": INDEX_FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "manifest": str(manifest_path),
            "record_count": len(records),
            "feature_dimension": dimension,
            "pca_dimensions": int(np.load(temp_dir / "pca_components.npy", mmap_mode="r").shape[0]),
            "domain_ids": catalog.ids,
            "taxonomy_version": catalog.version,
            "domains_per_frame": options.domains_per_frame,
            "object_min_score": options.object_min_score,
            "object_weighting": "detector_confidence_x_normalized_idf",
            "tree_files": tree_files,
            "tree_counts": tree_counts,
            "clip_model": os.getenv("KIS_CLIP_MODEL", "ViT-B-32"),
            "clip_pretrained": os.getenv("KIS_CLIP_PRETRAINED", "openai"),
        }
        with (temp_dir / "metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)

        (temp_dir / "object_bags.jsonl").unlink(missing_ok=True)
        _replace_directory(temp_dir, index_dir)
        return metadata
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


def _write_full_vectors(
    output_dir: Path,
    data_root: Path,
    records: list[ManifestRecord],
    grouped: dict[str, list[tuple[int, ManifestRecord]]],
) -> int:
    first_file = None
    for video_id in grouped:
        candidate = data_root / "clip-features-32" / f"{video_id}.npy"
        if candidate.is_file():
            first_file = candidate
            break
    if first_file is None:
        raise IndexBuildError(f"Không tìm thấy file .npy trong {data_root / 'clip-features-32'}")
    sample = np.load(first_file, mmap_mode="r")
    if sample.ndim != 2:
        raise IndexBuildError(f"CLIP feature phải là ma trận 2 chiều: {first_file} có shape {sample.shape}")
    dimension = int(sample.shape[1])
    output = np.lib.format.open_memmap(
        output_dir / "full_vectors.npy", mode="w+", dtype=np.float32, shape=(len(records), dimension)
    )

    for number, (video_id, items) in enumerate(grouped.items(), start=1):
        feature_file = data_root / "clip-features-32" / f"{video_id}.npy"
        if not feature_file.is_file():
            raise IndexBuildError(f"Thiếu CLIP feature: {feature_file}")
        vectors = np.load(feature_file, mmap_mode="r")
        if vectors.ndim != 2 or vectors.shape[1] != dimension:
            raise IndexBuildError(f"Sai shape CLIP feature {feature_file}: {vectors.shape}")
        for global_position, record in items:
            if record.clip_vector_index < 0 or record.clip_vector_index >= len(vectors):
                raise IndexBuildError(
                    f"clip_vector_index={record.clip_vector_index} vượt shape {vectors.shape} của {video_id}"
                )
            value = np.asarray(vectors[record.clip_vector_index], dtype=np.float32)
            norm = float(np.linalg.norm(value))
            if not np.isfinite(norm) or norm <= 1e-12:
                raise IndexBuildError(f"Vector rỗng/NaN: {record.keyframe_id}")
            output[global_position] = value / norm
        if number % 100 == 0:
            print(f"[vectors] {number}/{len(grouped)} videos")
    output.flush()
    return dimension


def _write_object_bags_and_domains(
    output_dir: Path,
    data_root: Path,
    records: list[ManifestRecord],
    catalog: DomainCatalog,
    options: BuildOptions,
) -> list[str]:
    vocabulary: set[str] = set()
    object_domain_scores = np.lib.format.open_memmap(
        output_dir / "object_domain_scores.npy",
        mode="w+",
        dtype=np.float16,
        shape=(len(records), len(catalog.domains)),
    )
    with (output_dir / "object_bags.jsonl").open("w", encoding="utf-8") as handle:
        for position, record in enumerate(records):
            object_file = resolve_object_file(data_root, record.video_id, record.keyframe_number)
            bag = load_object_terms(
                object_file,
                min_score=options.object_min_score,
                max_terms=options.object_max_terms,
            )
            vocabulary.update(bag)
            object_domain_scores[position] = catalog.object_domain_scores(bag)
            handle.write(json.dumps(bag, ensure_ascii=False, separators=(",", ":")) + "\n")
            if (position + 1) % 20_000 == 0:
                print(f"[objects] {position + 1}/{len(records)} keyframes")
    object_domain_scores.flush()

    full_vectors = np.load(output_dir / "full_vectors.npy", mmap_mode="r")
    prototypes = np.load(output_dir / "domain_prototypes.npy")
    domain_scores = np.lib.format.open_memmap(
        output_dir / "domain_scores.npy",
        mode="w+",
        dtype=np.float16,
        shape=(len(records), len(catalog.domains)),
    )
    batch_size = options.transform_batch_size
    for start in range(0, len(records), batch_size):
        stop = min(start + batch_size, len(records))
        semantic = np.clip(np.asarray(full_vectors[start:stop]) @ prototypes.T, -1.0, 1.0)
        semantic = (semantic + 1.0) / 2.0
        object_scores = np.asarray(object_domain_scores[start:stop], dtype=np.float32)
        domain_scores[start:stop] = np.maximum(semantic, object_scores).astype(np.float16)
    domain_scores.flush()
    del object_domain_scores
    (output_dir / "object_domain_scores.npy").unlink(missing_ok=True)
    return sorted(vocabulary)


def _write_bow_csr(output_dir: Path, vocabulary: list[str]) -> None:
    term_to_index = {term: index for index, term in enumerate(vocabulary)}
    indptr = [0]
    indices: list[int] = []
    weights: list[float] = []
    document_frequency = np.zeros(len(vocabulary), dtype=np.int64)
    with (output_dir / "object_bags.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            bag = json.loads(line)
            for term, weight in sorted(bag.items(), key=lambda item: term_to_index[item[0]]):
                term_index = term_to_index[term]
                indices.append(term_index)
                weights.append(float(weight))
                document_frequency[term_index] += 1
            indptr.append(len(indices))
    np.save(output_dir / "bow_indptr.npy", np.asarray(indptr, dtype=np.int64))
    np.save(output_dir / "bow_indices.npy", np.asarray(indices, dtype=np.int32))
    np.save(output_dir / "bow_weights.npy", np.asarray(weights, dtype=np.float16))
    document_count = max(len(indptr) - 1, 1)
    idf = np.log((document_count + 1) / (document_frequency + 1)) + 1.0
    if len(idf):
        idf /= max(float(idf.max()), 1e-12)
    np.save(output_dir / "bow_idf.npy", idf.astype(np.float16))
    with (output_dir / "vocabulary.json").open("w", encoding="utf-8") as handle:
        json.dump(vocabulary, handle, ensure_ascii=False)


def _fit_and_transform_pca(output_dir: Path, full_vectors: np.ndarray, options: BuildOptions) -> None:
    try:
        from sklearn.decomposition import PCA
    except ImportError as exc:
        raise IndexBuildError("Thiếu scikit-learn để build PCA/R-tree") from exc
    dimensions = min(options.pca_dimensions, full_vectors.shape[0], full_vectors.shape[1])
    if dimensions < 2:
        raise IndexBuildError("Cần ít nhất 2 vector/chiều để build R-tree")
    sample_count = min(options.pca_sample_size, len(full_vectors))
    sample_positions = np.linspace(0, len(full_vectors) - 1, sample_count, dtype=np.int64)
    sample = np.asarray(full_vectors[sample_positions], dtype=np.float32)
    pca = PCA(n_components=dimensions, svd_solver="randomized", random_state=42)
    pca.fit(sample)
    np.save(output_dir / "pca_components.npy", pca.components_.astype(np.float32))
    np.save(output_dir / "pca_mean.npy", pca.mean_.astype(np.float32))

    reduced = np.lib.format.open_memmap(
        output_dir / "reduced.npy",
        mode="w+",
        dtype=np.float32,
        shape=(len(full_vectors), dimensions),
    )
    for start in range(0, len(full_vectors), options.transform_batch_size):
        stop = min(start + options.transform_batch_size, len(full_vectors))
        reduced[start:stop] = pca.transform(np.asarray(full_vectors[start:stop], dtype=np.float32))
    reduced.flush()


def _write_records(output_dir: Path, records: list[ManifestRecord]) -> None:
    with (output_dir / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, separators=(",", ":")) + "\n")


def _build_rtrees(
    output_dir: Path,
    records: list[ManifestRecord],
    catalog: DomainCatalog,
    options: BuildOptions,
) -> tuple[dict[str, str], dict[str, int]]:
    try:
        from rtree import index as rtree_index
    except ImportError as exc:
        raise IndexBuildError("Thiếu rtree/libspatialindex để build index") from exc

    reduced = np.load(output_dir / "reduced.npy", mmap_mode="r")
    domain_scores = np.load(output_dir / "domain_scores.npy", mmap_mode="r")
    tree_dir = output_dir / "trees"
    tree_dir.mkdir()
    collections = sorted({record.collection_id for record in records})
    keys = ["global"]
    keys.extend(f"collection:{collection_id}" for collection_id in collections)
    keys.extend(f"domain:{domain_id}" for domain_id in catalog.ids)
    keys.extend(
        f"collection_domain:{collection_id}:{domain_id}"
        for collection_id in collections
        for domain_id in catalog.ids
    )
    tree_files = {key: f"tree_{index:04d}" for index, key in enumerate(keys)}
    tree_counts = {key: 0 for key in keys}
    properties = rtree_index.Property()
    properties.dimension = reduced.shape[1]
    properties.overwrite = True
    trees = {
        key: rtree_index.Index(str(tree_dir / filename), properties=properties)
        for key, filename in tree_files.items()
    }
    try:
        for position, record in enumerate(records):
            point = tuple(float(value) for value in reduced[position])
            bounds = point + point
            trees["global"].insert(position, bounds)
            tree_counts["global"] += 1
            trees[f"collection:{record.collection_id}"].insert(position, bounds)
            tree_counts[f"collection:{record.collection_id}"] += 1
            domain_positions = np.argsort(-np.asarray(domain_scores[position], dtype=np.float32))[
                : options.domains_per_frame
            ]
            for domain_position in domain_positions:
                domain_id = catalog.domains[int(domain_position)].id
                trees[f"domain:{domain_id}"].insert(position, bounds)
                tree_counts[f"domain:{domain_id}"] += 1
                trees[f"collection_domain:{record.collection_id}:{domain_id}"].insert(position, bounds)
                tree_counts[f"collection_domain:{record.collection_id}:{domain_id}"] += 1
            if (position + 1) % 20_000 == 0:
                print(f"[rtrees] {position + 1}/{len(records)} keyframes")
    finally:
        for tree in trees.values():
            tree.close()
    return tree_files, tree_counts


def _replace_directory(source: Path, destination: Path) -> None:
    backup = destination.with_name(f".{destination.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.rename(backup)
    try:
        source.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)
