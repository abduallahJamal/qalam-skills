"""Text statistics and structural helpers shared by the CLI and the QA gate."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .arabic import (
    ARABIC_LETTER_RE,
    LANGUAGE_NAMES,
    estimate_direction,
    language_is_rtl,
    normalise_digits,
    script_distribution,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟。！？])\s+|\n{2,}")
WORD_RE = re.compile(r"[\w\u0620-\u064A\u064B-\u065F\u0670'’-]+")


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def sentence_count(text: str) -> int:
    parts = [part for part in SENTENCE_SPLIT.split(text) if part and part.strip()]
    return max(len(parts), 1 if text.strip() else 0)


def average_sentence_length(text: str) -> float:
    count = sentence_count(text)
    if not count:
        return 0.0
    return round(word_count(text) / count, 1)


def detect_language(text: str) -> Dict[str, object]:
    """Guess the language of a sample without any model call."""
    sample = text[:4000]
    distribution = script_distribution(sample)
    direction = estimate_direction(sample)
    if distribution["arabic"] > 0.35:
        guess = "ar"
        confidence = "high" if distribution["arabic"] > 0.6 else "medium"
    elif distribution["latin"] > 0.35:
        guess = "en"
        confidence = "medium"   # Latin script covers many languages
    else:
        guess = "unknown"
        confidence = "low"
    letters = [char for char in sample if char.isalpha()]
    size_ratio = (
        sum(1 for char in letters if char.isupper()) / len(letters) if letters else 0.0
    )
    return {
        "guess": guess,
        "confidence": confidence,
        "direction": direction,
        "script": {key: round(value, 3) for key, value in distribution.items()},
        "uppercase_ratio": round(size_ratio, 3),
        "ratio_hint": _ratio_hint(distribution, size_ratio),
    }


def _ratio_hint(distribution: Dict[str, float], uppercase_ratio: float) -> str:
    if distribution["arabic"] > 0.35:
        return "Semitic-script text; expect harakat to be sparse, numbers may be Arabic-Indic"
    if distribution["latin"] > 0.35:
        if uppercase_ratio < 0.02:
            return "Latin script with few capitals: may be a capital-poor language (Arabic-transliterated, CJK romanisation, or lowercased input)"
        return "Latin script; rely on source metadata for the exact language"
    return "Insufficient letters for a reliable guess"


def quality_metrics(source: str, target: str) -> Dict[str, object]:
    """Length ratio and structure deltas between a source and its translation."""
    source_words = word_count(source)
    target_words = word_count(target)
    ratio = round(target_words / source_words, 3) if source_words else 0.0
    return {
        "source_words": source_words,
        "target_words": target_words,
        "length_ratio": ratio,
        "source_sentences": sentence_count(source),
        "target_sentences": sentence_count(target),
        "source_avg_sentence": average_sentence_length(source),
        "target_avg_sentence": average_sentence_length(target),
        "source_direction": estimate_direction(source),
        "target_direction": estimate_direction(target),
    }


def length_ratio_band(source_language: str, target_language: str) -> Tuple[float, float]:
    """Expected target/source word ratio for a language pair.

    Arabic states the same idea in fewer words than English, so an Arabic
    translation of an English book typically lands between 0.75 and 1.0.  A
    ratio far outside the band usually means dropped or invented content, not
    a style choice.
    """
    source = (source_language or "").split("-")[0].lower()
    target = (target_language or "").split("-")[0].lower()
    base = 0.95
    if target == "ar" and source == "en":
        return (0.72, 1.05)
    if source == "ar" and target == "en":
        return (0.95, 1.45)
    if language_is_rtl(target) != language_is_rtl(source):
        base = 0.85
    if target in {"zh", "ja", "ko"}:
        return (0.35, 0.75)
    return (base * 0.7, base * 1.35)


def structure_fingerprint(text: str) -> Dict[str, object]:
    """Count the structures a translation must preserve one-for-one."""
    lines = text.splitlines()
    fence_count = sum(1 for line in lines if line.strip().startswith(("```", "~~~")))
    return {
        "headings": sum(1 for line in lines if re.match(r"^#{1,6}\s+\S", line)),
        "fences": fence_count // 2 if fence_count % 2 == 0 else fence_count,
        "links": len(re.findall(r"\]\([^)]+\)", text)),
        "images": len(re.findall(r"!\[[^\]]*\]\([^)]+\)", text)),
        "tables": sum(1 for line in lines if line.strip().startswith("|")),
        "list_items": sum(1 for line in lines if re.match(r"^\s*([-*+]|\d+[.)])\s+", line)),
    }


def compare_structures(source: str, target: str) -> List[str]:
    """Differences that indicate a broken translation rather than a style choice."""
    src = structure_fingerprint(source)
    tgt = structure_fingerprint(target)
    problems: List[str] = []
    for key in ("headings", "fences", "links", "images"):
        if src[key] != tgt[key]:
            problems.append(f"{key}: source {src[key]}, target {tgt[key]}")
    if src["tables"] and not tgt["tables"]:
        problems.append("tables disappeared in the target text")
    return problems


def language_label(code: str) -> str:
    """Human-readable name for a language code, with its Arabic name."""
    base = (code or "").split("-")[0].lower()
    name, arabic_name = LANGUAGE_NAMES.get(base, (code, code))
    if name == code:
        return code
    return f"{name} ({arabic_name})"


def numbers_in(text: str) -> List[str]:
    """All numeric tokens, digit script folded to ASCII, in order."""
    return re.findall(r"\d+(?:[.,]\d+)*", normalise_digits(text))
