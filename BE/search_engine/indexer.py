from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .domains import DEFAULT_TAXONOMY_PATH, DomainCatalog, DomainRouter, Route
from .exceptions import SearchServiceUnavailable
from .manifest import ManifestRecord
from .query_analyzer import best_term_match


INDEX_FORMAT_VERSION = 2
DEFAULT_INDEX_DIR = Path(__file__).resolve().parent / "data" / "search_index"


@dataclass(frozen=True)
class RankedCandidate:
    position: int
    score: float
    clip_score: float
    object_score: float
    domain_score: float
    matched_objects: tuple[str, ...]


class HybridSearchIndex:
    def __init__(self, path: Path):
        self.path = path
        metadata_path = path / "metadata.json"
        if not metadata_path.is_file():
            raise SearchServiceUnavailable(
                f"Chưa có search index tại {path}. Chạy: python -m search_engine.cli build-index"
            )
        with metadata_path.open("r", encoding="utf-8") as handle:
            self.metadata = json.load(handle)
        if self.metadata.get("format_version") != INDEX_FORMAT_VERSION:
            raise SearchServiceUnavailable(
                "Search index khác phiên bản code; hãy build lại index."
            )

        self.full_vectors = np.load(path / "full_vectors.npy", mmap_mode="r")
        self.pca_components = np.load(path / "pca_components.npy")
        self.pca_mean = np.load(path / "pca_mean.npy")
        self.domain_scores = np.load(path / "domain_scores.npy", mmap_mode="r")
        self.bow_indptr = np.load(path / "bow_indptr.npy", mmap_mode="r")
        self.bow_indices = np.load(path / "bow_indices.npy", mmap_mode="r")
        self.bow_weights = np.load(path / "bow_weights.npy", mmap_mode="r")
        self.bow_idf = np.load(path / "bow_idf.npy", mmap_mode="r")

        with (path / "vocabulary.json").open("r", encoding="utf-8") as handle:
            self.vocabulary: list[str] = json.load(handle)
        if len(self.vocabulary) != len(self.bow_idf):
            raise SearchServiceUnavailable("Index hỏng: vocabulary không khớp object IDF")
        self.records = _load_records(path / "records.jsonl")
        if len(self.records) != len(self.full_vectors):
            raise SearchServiceUnavailable("Index hỏng: số record không khớp số vector")

        taxonomy_path = Path(os.getenv("KIS_DOMAIN_TAXONOMY", path / "taxonomy.json"))
        if not taxonomy_path.is_file():
            taxonomy_path = DEFAULT_TAXONOMY_PATH
        self.catalog = DomainCatalog.load(taxonomy_path)
        if self.catalog.ids != self.metadata.get("domain_ids"):
            raise SearchServiceUnavailable("Domain taxonomy đã đổi; hãy build lại index")
        prototypes = np.load(path / "domain_prototypes.npy")
        self.router = DomainRouter(self.catalog, prototypes)
        self.tree_files: dict[str, str] = self.metadata["tree_files"]
        self._trees = {}
        self._tree_lock = threading.Lock()

    @classmethod
    def load(cls, path: Path | str | None = None) -> "HybridSearchIndex":
        return cls(Path(path or os.getenv("KIS_INDEX_ROOT", DEFAULT_INDEX_DIR)).resolve())

    def reduce_query(self, query_vector: np.ndarray) -> np.ndarray:
        query = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        if query.shape[0] != self.full_vectors.shape[1]:
            raise ValueError(
                f"Query vector có {query.shape[0]} chiều, index cần {self.full_vectors.shape[1]} chiều"
            )
        return ((query - self.pca_mean) @ self.pca_components.T).astype(np.float32)

    def candidates(
        self,
        query_reduced: np.ndarray,
        route: Route,
        collection_ids: list[str],
        candidate_k: int,
    ) -> list[int]:
        positions, _trace = self.candidates_with_trace(
            query_reduced,
            route,
            collection_ids,
            candidate_k,
        )
        return positions

    def candidates_with_trace(
        self,
        query_reduced: np.ndarray,
        route: Route,
        collection_ids: list[str],
        candidate_k: int,
    ) -> tuple[list[int], dict]:
        selected: list[int] = []
        seen: set[int] = set()

        if collection_ids:
            collections = [value.upper() for value in collection_ids]
            routed_keys = [
                f"collection_domain:{collection_id}:{domain_id}"
                for collection_id in collections
                for domain_id in route.domain_ids
            ]
            fallback_keys = [f"collection:{collection_id}" for collection_id in collections]
        else:
            routed_keys = [f"domain:{domain_id}" for domain_id in route.domain_ids]
            fallback_keys = ["global"]

        routed_keys = [key for key in routed_keys if key in self.tree_files]
        fallback_keys = [key for key in fallback_keys if key in self.tree_files]
        per_tree = max(candidate_k // max(len(routed_keys), 1), 1)
        tree_trace = []
        for key in routed_keys:
            returned, unique = self._extend_nearest(selected, seen, key, query_reduced, per_tree)
            tree_trace.append(self._tree_trace(key, "routed", per_tree, returned, unique))

        # Global/collection fallback protects recall when the domain router is unsure.
        fallback_budget = max(candidate_k // 3, 50)
        for key in fallback_keys:
            returned, unique = self._extend_nearest(
                selected, seen, key, query_reduced, fallback_budget
            )
            tree_trace.append(
                self._tree_trace(key, "fallback", fallback_budget, returned, unique)
            )

        return selected, {
            "requested_candidate_k": candidate_k,
            "unique_candidate_count": len(selected),
            "collection_ids": [value.upper() for value in collection_ids],
            "selected_domains": list(route.domain_ids),
            "trees": tree_trace,
        }

    def rerank(
        self,
        query_vector: np.ndarray,
        route: Route,
        positions: list[int],
        *,
        top_k: int,
        clip_weight: float = 0.82,
        object_weight: float = 0.12,
        domain_weight: float = 0.06,
    ) -> list[RankedCandidate]:
        if not positions:
            return []
        query = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        query /= max(float(np.linalg.norm(query)), 1e-12)
        position_array = np.asarray(positions, dtype=np.int64)
        vectors = np.asarray(self.full_vectors[position_array], dtype=np.float32)
        clip_scores = np.clip(vectors @ query, -1.0, 1.0)
        clip_scores = (clip_scores + 1.0) / 2.0

        route_vector = np.asarray(
            [route.scores[domain_id] for domain_id in self.catalog.ids], dtype=np.float32
        )
        domain_values = np.asarray(self.domain_scores[position_array], dtype=np.float32)
        domain_scores = np.max(domain_values * route_vector[None, :], axis=1)

        query_object_scores = self.query_object_scores(route)
        object_scores = np.zeros(len(positions), dtype=np.float32)
        object_matches: list[tuple[str, ...]] = []
        for result_index, position in enumerate(positions):
            score, matches = self._object_score(position, query_object_scores)
            object_scores[result_index] = score
            object_matches.append(matches)

        final_scores = (
            clip_weight * clip_scores
            + object_weight * object_scores
            + domain_weight * domain_scores
        )
        order = np.argsort(-final_scores)[:top_k]
        return [
            RankedCandidate(
                position=positions[int(index)],
                score=float(final_scores[index]),
                clip_score=float(clip_scores[index]),
                object_score=float(object_scores[index]),
                domain_score=float(domain_scores[index]),
                matched_objects=object_matches[int(index)],
            )
            for index in order
        ]

    def query_object_scores(self, route: Route) -> dict[int, float]:
        object_candidates = (*route.keyword_candidates, *route.expanded_terms)
        return {
            term_index: score
            for term_index, term in enumerate(self.vocabulary)
            if (score := best_term_match(object_candidates, term)) >= 0.80
        }

    def close(self) -> None:
        for tree in self._trees.values():
            close = getattr(tree, "close", None)
            if close:
                close()
        self._trees.clear()

    def _object_score(
        self,
        position: int,
        query_term_scores: dict[int, float],
    ) -> tuple[float, tuple[str, ...]]:
        if not query_term_scores:
            return 0.0, ()
        start = int(self.bow_indptr[position])
        end = int(self.bow_indptr[position + 1])
        matches = []
        matched_weights = []
        for offset in range(start, end):
            term_index = int(self.bow_indices[offset])
            query_score = query_term_scores.get(term_index)
            if query_score is not None:
                term = self.vocabulary[term_index]
                matched_weights.append(
                    float(self.bow_weights[offset])
                    * float(self.bow_idf[term_index])
                    * query_score
                )
                matches.append(term)
        if not matched_weights:
            return 0.0, ()
        # Multiple corroborating objects improve the score without allowing long
        # detector outputs to dominate CLIP similarity.
        score = min(1.0, max(matched_weights) + 0.1 * (len(matched_weights) - 1))
        return score, tuple(sorted(set(matches)))

    def _extend_nearest(
        self,
        selected: list[int],
        seen: set[int],
        key: str,
        query: np.ndarray,
        count: int,
    ) -> tuple[int, int]:
        tree = self._get_tree(key)
        point = tuple(float(value) for value in query)
        bounds = point + point
        try:
            positions = tree.nearest(bounds, num_results=count)
        except TypeError:  # rtree 1.0 compatibility
            positions = tree.nearest(bounds, count)
        returned = 0
        unique = 0
        for position in positions:
            returned += 1
            numeric_position = int(position)
            if numeric_position not in seen:
                seen.add(numeric_position)
                selected.append(numeric_position)
                unique += 1
        return returned, unique

    def _tree_trace(
        self,
        key: str,
        role: str,
        requested: int,
        returned: int,
        unique: int,
    ) -> dict:
        return {
            "tree_key": key,
            "role": role,
            "entry_count": int(self.metadata.get("tree_counts", {}).get(key, 0)),
            "requested": requested,
            "returned": returned,
            "new_unique_candidates": unique,
        }

    def _get_tree(self, key: str):
        if key in self._trees:
            return self._trees[key]
        with self._tree_lock:
            if key not in self._trees:
                try:
                    from rtree import index as rtree_index
                except ImportError as exc:
                    raise SearchServiceUnavailable("Thiếu thư viện rtree/libspatialindex") from exc
                properties = rtree_index.Property()
                properties.dimension = int(self.pca_components.shape[0])
                prefix = self.path / "trees" / self.tree_files[key]
                if not prefix.with_suffix(".idx").is_file() or not prefix.with_suffix(".dat").is_file():
                    raise SearchServiceUnavailable(f"Index hỏng: thiếu R-tree {key}")
                self._trees[key] = rtree_index.Index(str(prefix), properties=properties)
        return self._trees[key]


def _load_records(path: Path) -> list[ManifestRecord]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            records.append(ManifestRecord(**item))
    return records


_index_cache = None
_index_cache_path = None
_index_lock = threading.Lock()


def get_index(path: Path | str | None = None) -> HybridSearchIndex:
    global _index_cache, _index_cache_path
    resolved = Path(path or os.getenv("KIS_INDEX_ROOT", DEFAULT_INDEX_DIR)).resolve()
    if _index_cache is None or _index_cache_path != resolved:
        with _index_lock:
            if _index_cache is None or _index_cache_path != resolved:
                if _index_cache is not None:
                    _index_cache.close()
                _index_cache = HybridSearchIndex.load(resolved)
                _index_cache_path = resolved
    return _index_cache


def reset_index_cache() -> None:
    global _index_cache, _index_cache_path
    with _index_lock:
        if _index_cache is not None:
            _index_cache.close()
        _index_cache = None
        _index_cache_path = None
