from __future__ import annotations

import numpy as np

from .embedding import get_encoder
from .indexer import get_index


def search(*, query: str, collection_ids: list[str], top_k: int) -> list[dict]:
    query = (query or "").strip()
    if not query:
        raise ValueError("Query is empty")
    if top_k < 1:
        raise ValueError("top_k must be positive")

    index, _clip_query, query_vector, route = _prepare_query(query)
    query_reduced = index.reduce_query(query_vector)
    candidate_k = max(top_k * 25, 500)
    positions = index.candidates(
        query_reduced,
        route,
        collection_ids=collection_ids,
        candidate_k=candidate_k,
    )
    ranked = index.rerank(query_vector, route, positions, top_k=top_k)

    results = []
    for rank, candidate in enumerate(ranked, start=1):
        record = index.records[candidate.position]
        frame_domain_scores = np.asarray(index.domain_scores[candidate.position], dtype=np.float32)
        domain_order = np.argsort(-frame_domain_scores)[:2]
        item = record.result_dict()
        item.update(
            {
                "rank": rank,
                "score": candidate.score,
                "domains": [index.catalog.domains[int(position)].id for position in domain_order],
                "matched_objects": list(candidate.matched_objects),
                "score_components": {
                    "clip": candidate.clip_score,
                    "object_bow": candidate.object_score,
                    "domain": candidate.domain_score,
                },
                "routed_domains": list(route.domain_ids),
            }
        )
        results.append(item)
    return results


def inspect(*, query: str, collection_ids: list[str], top_k: int) -> dict:
    query = (query or "").strip()
    if not query:
        raise ValueError("Query is empty")
    index, clip_query, query_vector, route = _prepare_query(query)
    candidate_k = max(top_k * 25, 500)
    positions, tree_trace = index.candidates_with_trace(
        index.reduce_query(query_vector),
        route,
        collection_ids,
        candidate_k,
    )
    object_scores = index.query_object_scores(route)
    routed = set(route.domain_ids)
    domains = sorted(
        (
            {
                "domain_id": domain_id,
                "selected": domain_id in routed,
                "score": route.scores[domain_id],
                "lexical_score": route.lexical_scores[domain_id],
            }
            for domain_id in index.catalog.ids
        ),
        key=lambda item: -item["score"],
    )
    return {
        "query": query,
        "clip_query": clip_query,
        "analysis": {
            "normalized_query": route.normalized_query,
            "keyword_candidates": list(route.keyword_candidates),
            "expanded_terms": list(route.expanded_terms),
            "matched_object_vocabulary": [
                {"term": index.vocabulary[position], "match_score": score}
                for position, score in sorted(object_scores.items(), key=lambda item: -item[1])
            ],
        },
        "routing": {
            "selected_domains": list(route.domain_ids),
            "domains": domains,
        },
        "candidate_trace": tree_trace,
        "index": {
            "format_version": index.metadata.get("format_version"),
            "record_count": index.metadata.get("record_count"),
            "feature_dimension": index.metadata.get("feature_dimension"),
            "pca_dimensions": index.metadata.get("pca_dimensions"),
            "tree_count": len(index.tree_files),
        },
    }


def _prepare_query(query: str):
    index = get_index()
    alias_terms = index.catalog.matched_alias_terms(query)
    clip_query = query
    if alias_terms:
        # OpenAI CLIP is strongest in English; keep the original sentence and add
        # deterministic English concepts from the Vietnamese alias dictionary.
        clip_query = f"{query}. Visual concepts: {', '.join(sorted(alias_terms))}."
    query_vector = get_encoder().encode_text(clip_query)
    route = index.router.route(query, query_vector)
    return index, clip_query, query_vector, route
