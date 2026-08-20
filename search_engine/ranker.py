import numpy as np

def rerank(query_full: np.ndarray, candidate_positions: list[int], search_index) -> list[tuple[int, float]]:
    if not candidate_positions:
        return []
    cand_vectors = search_index.full_vectors[candidate_positions]
    scores = cand_vectors @ query_full
    order = np.argsort(-scores)
    return [(candidate_positions[i], float(scores[i])) for i in order]