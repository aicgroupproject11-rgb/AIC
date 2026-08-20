from .embedding import get_encoder
from .indexer import get_index, SearchServiceUnavailable  # noqa: F401  (re-export cho apps.kis dùng)
from .ranker import rerank
from .manifest import get_manifest_row

def search(*, query: str, collection_ids: list[str], top_k: int) -> list[dict]:
    query = (query or "").strip()
    if not query:
        raise ValueError("Query is empty")

    encoder = get_encoder()
    idx = get_index() 
    query_full = encoder.encode_text(query)
    query_reduced = idx.pca.transform(query_full.reshape(1, -1))[0].astype("float32")
    candidate_k = max(top_k * 10, 200)
    candidate_positions = idx.candidates(query_reduced, k=candidate_k)
    if collection_ids:
        allowed = set(collection_ids)
        candidate_positions = [
            pos for pos in candidate_positions
            if idx.collection_ids[pos] in allowed
        ]
    ranked = rerank(query_full, candidate_positions, idx)[:top_k]
    results = []
    for i, (pos, score) in enumerate(ranked, start=1):
        keyframe_id = idx.ids[pos]
        row = get_manifest_row(keyframe_id)
        results.append({
            "rank": i,
            "keyframe_id": row["keyframe_id"],
            "collection_id": row["collection_id"],
            "video_id": row["video_id"],
            "frame_number": int(row["frame_number"]),
            "timestamp_ms": int(row["timestamp_ms"]),
            "image_path": row["image_path"],
            "video_path": row["video_path"] or f"videos/{row['video_id']}.mp4",
            "score": score,
        })
    return results