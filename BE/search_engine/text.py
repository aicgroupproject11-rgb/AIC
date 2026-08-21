from __future__ import annotations

import re
import unicodedata


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_text(value: str) -> str:
    """Lowercase text and remove Vietnamese accents for deterministic matching."""
    value = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(TOKEN_PATTERN.findall(value))


def tokenize(value: str) -> set[str]:
    return set(normalize_text(value).split())


def matched_phrases(normalized_text: str, phrases: list[str]) -> set[str]:
    padded = f" {normalized_text} "
    return {
        phrase
        for phrase in phrases
        if phrase and f" {phrase} " in padded
    }
