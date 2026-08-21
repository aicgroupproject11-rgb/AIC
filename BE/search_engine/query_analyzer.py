from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from .text import normalize_text


STOPWORDS = {
    "ai", "bi", "biet", "cach", "cac", "cho", "co", "cua", "duoc",
    "gi", "hay", "khong", "la", "lai", "lam", "mot", "nao", "nhu",
    "nhung", "phan", "sao", "the", "theo", "tim", "toi", "va", "ve",
    "vi", "voi", "please", "find", "search", "show", "the", "a", "an",
}
PROTECTED_TOKENS = {
    "ai", "iot", "sql", "html", "css", "python", "clip", "bus", "glass",
}


@dataclass(frozen=True)
class QueryAnalysis:
    original: str
    normalized: str
    tokens: tuple[str, ...]
    candidates: tuple[str, ...]


def analyze_query(query: str, *, max_candidates: int = 32) -> QueryAnalysis:
    normalized = normalize_text(query)
    tokens = tuple(token for token in normalized.split() if token)
    variants = _unique(
        [
            normalized,
            _remove_trailing_word_digits(normalized),
            _collapse_repeated_final_letters(normalized),
            _remove_telex_final_noise(normalized),
            _normalize_telex(normalized),
        ]
    )
    candidates: list[str] = []
    for variant in variants:
        _append_unique(candidates, variant)
        variant_tokens = variant.split()
        for size in (3, 2):
            for start in range(len(variant_tokens) - size + 1):
                phrase_tokens = variant_tokens[start : start + size]
                if all(token in STOPWORDS for token in phrase_tokens):
                    continue
                _append_unique(candidates, " ".join(phrase_tokens))
        for token in variant_tokens:
            if token not in STOPWORDS and len(token) > 1:
                _append_unique(candidates, token)
    return QueryAnalysis(
        original=query,
        normalized=normalized,
        tokens=tokens,
        candidates=tuple(candidates[:max_candidates]),
    )


def best_term_match(candidates: tuple[str, ...] | list[str], target: str) -> float:
    target = normalize_text(target)
    if not target:
        return 0.0
    target_tokens = target.split()
    best = 0.0
    for raw_candidate in candidates:
        candidate = normalize_text(raw_candidate)
        if not candidate:
            continue
        if candidate == target:
            return 1.0
        candidate_tokens = candidate.split()
        if _contains_phrase(candidate_tokens, target_tokens):
            best = max(best, 0.97)
        if len(candidate_tokens) >= 2 and _contains_phrase(target_tokens, candidate_tokens):
            coverage = len(candidate_tokens) / max(len(target_tokens), 1)
            if coverage >= 0.6:
                best = max(best, 0.88 * min(1.0, coverage))
        best = max(best, _fuzzy_score(candidate_tokens, target_tokens))
    return best


def match_terms(
    analysis: QueryAnalysis,
    terms: list[str] | tuple[str, ...],
    *,
    minimum_score: float = 0.80,
) -> dict[str, float]:
    result = {}
    for term in terms:
        normalized_term = normalize_text(term)
        score = best_term_match(analysis.candidates, normalized_term)
        if score >= minimum_score:
            result[normalized_term] = score
    return result


def _fuzzy_score(candidate_tokens: list[str], target_tokens: list[str]) -> float:
    if not candidate_tokens or not target_tokens:
        return 0.0
    if len(target_tokens) == 1:
        target = target_tokens[0]
        if len(target) < 5:
            return 0.0
        return max(
            (
                0.86 * similarity
                for token in candidate_tokens
                if len(token) >= 5
                and (similarity := SequenceMatcher(None, token, target).ratio()) >= 0.88
            ),
            default=0.0,
        )
    if len(candidate_tokens) < len(target_tokens):
        return 0.0
    best = 0.0
    for start in range(len(candidate_tokens) - len(target_tokens) + 1):
        window = candidate_tokens[start : start + len(target_tokens)]
        similarities = [
            SequenceMatcher(None, left, right).ratio()
            for left, right in zip(window, target_tokens)
        ]
        coverage = sum(score >= 0.8 for score in similarities) / len(target_tokens)
        average = sum(similarities) / len(similarities)
        if coverage >= 0.75 and average >= 0.86:
            best = max(best, 0.84 * coverage)
    return best


def _contains_phrase(tokens: list[str], phrase: list[str]) -> bool:
    if not tokens or not phrase or len(phrase) > len(tokens):
        return False
    return any(tokens[start : start + len(phrase)] == phrase for start in range(len(tokens) - len(phrase) + 1))


def _remove_trailing_word_digits(value: str) -> str:
    return " ".join(re.sub(r"\b([a-z]+)\d+\b", r"\1", value).split())


def _collapse_repeated_final_letters(value: str) -> str:
    output = []
    for token in value.split():
        if token not in PROTECTED_TOKENS and re.fullmatch(r"[a-z]{3,}", token) and token[-1] == token[-2]:
            token = token[:-1]
        output.append(token)
    return " ".join(output)


def _remove_telex_final_noise(value: str) -> str:
    output = []
    for token in value.split():
        if token not in PROTECTED_TOKENS and re.fullmatch(r"[a-z]{3,}[sfrxj]", token):
            token = token[:-1]
        output.append(token)
    return " ".join(output)


def _normalize_telex(value: str) -> str:
    """Recover accent-free Vietnamese from common unfinished Telex input.

    This deliberately activates only for tokens containing a Telex vowel or
    ``dd`` marker, so English words ending in ``s``/``f`` are not damaged.
    """
    output = []
    markers = ("dd", "aw", "aa", "ee", "oo", "ow", "uw")
    replacements = (
        ("dd", "d"),
        ("aw", "a"),
        ("aa", "a"),
        ("ee", "e"),
        ("oo", "o"),
        ("ow", "o"),
        ("uw", "u"),
    )
    for token in value.split():
        if token not in PROTECTED_TOKENS and any(marker in token for marker in markers):
            token = re.sub(r"[sfrxj]$", "", token)
            for source, target in replacements:
                token = token.replace(source, target)
        output.append(token)
    return " ".join(output)


def _append_unique(values: list[str], value: str) -> None:
    value = " ".join(value.split())
    if value and value not in values:
        values.append(value)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        _append_unique(result, value)
    return result
