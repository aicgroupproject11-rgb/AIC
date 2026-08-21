from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .query_analyzer import analyze_query, best_term_match
from .text import normalize_text, tokenize


DEFAULT_TAXONOMY_PATH = Path(__file__).with_name("domain_taxonomy.json")


@dataclass(frozen=True)
class Domain:
    id: str
    prompt: str
    terms: tuple[str, ...]


@dataclass(frozen=True)
class Route:
    domain_ids: tuple[str, ...]
    scores: dict[str, float]
    lexical_scores: dict[str, float]
    expanded_terms: tuple[str, ...]
    normalized_query: str
    keyword_candidates: tuple[str, ...]


class DomainCatalog:
    def __init__(self, domains: list[Domain], aliases: dict[str, str], version: int = 1):
        if not domains:
            raise ValueError("Domain taxonomy must contain at least one domain")
        self.domains = domains
        self.aliases = aliases
        self.version = version
        self._domain_by_id = {domain.id: domain for domain in domains}
        if len(self._domain_by_id) != len(domains):
            raise ValueError("Domain IDs must be unique")

    @classmethod
    def load(cls, path: Path | str = DEFAULT_TAXONOMY_PATH) -> "DomainCatalog":
        with Path(path).open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        domains = [
            Domain(
                id=item["id"],
                prompt=item["prompt"],
                terms=tuple(normalize_text(term) for term in item.get("terms", [])),
            )
            for item in raw["domains"]
        ]
        aliases = {
            normalize_text(source): normalize_text(target)
            for source, target in raw.get("aliases", {}).items()
        }
        return cls(domains=domains, aliases=aliases, version=int(raw.get("version", 1)))

    @property
    def ids(self) -> list[str]:
        return [domain.id for domain in self.domains]

    @property
    def prompts(self) -> list[str]:
        return [domain.prompt for domain in self.domains]

    def expand_query(self, query: str) -> set[str]:
        analysis = analyze_query(query)
        result = set(analysis.tokens)
        for target in self.matched_alias_terms(query):
            result.update(tokenize(target))
        return result

    def matched_alias_terms(self, query: str) -> set[str]:
        analysis = analyze_query(query)
        return {
            target
            for source, target in self.aliases.items()
            if best_term_match(analysis.candidates, source) >= 0.80
        }

    def lexical_scores(self, text: str) -> np.ndarray:
        analysis = analyze_query(text)
        alias_terms = self.matched_alias_terms(text)
        candidates = (*analysis.candidates, *sorted(alias_terms))
        scores = np.zeros(len(self.domains), dtype=np.float32)
        for index, domain in enumerate(self.domains):
            matches = sorted(
                (
                    best_term_match(candidates, term) * (1.2 if len(term.split()) > 1 else 1.0)
                    for term in domain.terms
                ),
                reverse=True,
            )
            scores[index] = sum(score for score in matches[:3] if score >= 0.80)
        if scores.max(initial=0.0) > 0:
            scores /= scores.max()
        return scores

    def object_domain_scores(self, object_terms: Iterable[str]) -> np.ndarray:
        normalized_terms = {normalize_text(term) for term in object_terms if term}
        object_tokens = set().union(*(tokenize(term) for term in normalized_terms)) if normalized_terms else set()
        scores = np.zeros(len(self.domains), dtype=np.float32)
        for index, domain in enumerate(self.domains):
            domain_tokens = set().union(*(tokenize(term) for term in domain.terms))
            overlap = object_tokens & domain_tokens
            if overlap:
                scores[index] = min(1.0, len(overlap) / 2.0)
        return scores


class DomainRouter:
    def __init__(
        self,
        catalog: DomainCatalog,
        prototypes: np.ndarray,
        *,
        lexical_weight: float = 0.65,
        max_domains: int = 3,
        relative_threshold: float = 0.60,
    ):
        if prototypes.shape[0] != len(catalog.domains):
            raise ValueError("Prototype count does not match domain taxonomy")
        self.catalog = catalog
        self.prototypes = _normalize_rows(np.asarray(prototypes, dtype=np.float32))
        self.lexical_weight = lexical_weight
        self.max_domains = max_domains
        self.relative_threshold = relative_threshold

    def route(self, query: str, query_vector: np.ndarray) -> Route:
        analysis = analyze_query(query)
        lexical = self.catalog.lexical_scores(query)
        query_vector = _normalize_vector(query_vector)
        semantic = np.clip(self.prototypes @ query_vector, -1.0, 1.0)
        semantic = (semantic + 1.0) / 2.0

        # Explicit words should dominate routing; semantic routing is the fallback
        # for descriptions that do not occur in the fixed vocabulary.
        lexical_weight = self.lexical_weight if lexical.max(initial=0.0) > 0 else 0.0
        combined = lexical_weight * lexical + (1.0 - lexical_weight) * semantic
        order = np.argsort(-combined)
        best = float(combined[order[0]])
        selected = [
            int(index)
            for index in order[: self.max_domains]
            if float(combined[index]) >= best * self.relative_threshold
        ]
        if not selected:
            selected = [int(order[0])]

        score_map = {
            domain.id: float(combined[index])
            for index, domain in enumerate(self.catalog.domains)
        }
        lexical_map = {
            domain.id: float(lexical[index])
            for index, domain in enumerate(self.catalog.domains)
        }
        return Route(
            domain_ids=tuple(self.catalog.domains[index].id for index in selected),
            scores=score_map,
            lexical_scores=lexical_map,
            expanded_terms=tuple(sorted(self.catalog.expand_query(query))),
            normalized_query=analysis.normalized,
            keyword_candidates=analysis.candidates,
        )


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)


def _normalize_vector(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float32).reshape(-1)
    return value / max(float(np.linalg.norm(value)), 1e-12)
