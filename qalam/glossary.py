"""Term base: build, store, query, and render a glossary.

A glossary is the single mechanism that keeps a long document consistent when
each chunk is translated by a different agent with a fresh context.  Every
entry is a *decision*: this source form becomes that target form, everywhere.

The file is plain JSON so a human can edit it in any editor, and edits are
picked up by the next run without any migration step.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .arabic import normalise_arabic

CATEGORIES = ("person", "place", "org", "product", "technical", "title", "other")

PROTECTED = re.compile(r"(`[^`]*`|```[\s\S]*?```|\]\([^)]*\)|<[^>]+>|https?://\S+)")
CAPITALISED_SEQ = re.compile(r"\b(?:[A-Z][\w'’-]+)(?:[ \t]+[A-Z][\w'’-]+)*")
ARABIC_SEQ = re.compile(r"[\u0620-\u064A][\u0620-\u064A\u064B-\u065F\u0670]*")
STOPWORDS = {
    "The", "A", "An", "And", "Or", "But", "If", "It", "Its", "This", "That",
    "These", "Those", "There", "Then", "Than", "When", "Where", "While", "While",
    "He", "She", "They", "We", "You", "I", "His", "Her", "Their", "Our", "Your",
    "In", "On", "At", "By", "For", "From", "To", "With", "Of", "As", "Is", "Are",
    "Was", "Were", "Be", "Been", "Being", "Not", "No", "Yes", "Chapter", "Part",
    "Figure", "Table", "Example", "Note", "Step", "However", "Although", "Because",
    "Which", "Who", "What", "How", "Why", "All", "Some", "Any", "Each", "Every",
}


@dataclass
class Term:
    source: str
    target: str = ""
    category: str = "other"
    aliases: List[str] = field(default_factory=list)
    gender: str = "unknown"          # masculine / feminine / plural / unknown
    confidence: str = "medium"       # high / medium / low
    frequency: int = 0
    keep_as_is: bool = False
    notes: str = ""

    def key(self) -> str:
        return normalise_arabic(self.source, keep_diacritics=False).lower()

    def to_dict(self) -> Dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "category": self.category,
            "aliases": list(self.aliases),
            "gender": self.gender,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "keep_as_is": self.keep_as_is,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Term":
        category = str(data.get("category") or "other")
        if category not in CATEGORIES:
            category = "other"
        return cls(
            source=str(data.get("source") or "").strip(),
            target=str(data.get("target") or "").strip(),
            category=category,
            aliases=[str(a) for a in data.get("aliases") or []],
            gender=str(data.get("gender") or "unknown"),
            confidence=str(data.get("confidence") or "medium"),
            frequency=int(data.get("frequency") or 0),
            keep_as_is=bool(data.get("keep_as_is") or False),
            notes=str(data.get("notes") or ""),
        )


class Glossary:
    def __init__(self, terms: Optional[Iterable[Term]] = None) -> None:
        self.terms: List[Term] = list(terms or [])

    # -- storage ------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "Glossary":
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        terms = [Term.from_dict(item) for item in data.get("terms", [])]
        return cls(terms)

    def save(self, path: str) -> None:
        payload = {"version": 1, "terms": [term.to_dict() for term in self.terms]}
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)

    def merge(self, other: "Glossary") -> None:
        """Add missing terms from *other*; never overwrite a human decision."""
        existing = {term.key() for term in self.terms}
        for term in other.terms:
            if term.key() not in existing:
                self.terms.append(term)
                existing.add(term.key())

    # -- lookup -------------------------------------------------------------
    def find(self, surface: str) -> Optional[Term]:
        key = normalise_arabic(surface, keep_diacritics=False).lower()
        for term in self.terms:
            if term.key() == key:
                return term
            for alias in term.aliases:
                if normalise_arabic(alias, keep_diacritics=False).lower() == key:
                    return term
        return None

    def matching(self, text: str) -> List[Term]:
        """Terms whose source or alias occurs in *text* (longest first)."""
        haystack = normalise_arabic(text, keep_diacritics=False).lower()
        hits: List[Tuple[int, Term]] = []
        for term in self.terms:
            forms = [term.source] + list(term.aliases)
            best = 0
            for form in forms:
                needle = normalise_arabic(form, keep_diacritics=False).lower()
                if len(needle) < 2:
                    continue
                if needle in haystack:
                    best = max(best, len(needle))
            if best:
                hits.append((best, term))
        hits.sort(key=lambda pair: (-pair[0], pair[1].source))
        return [term for _length, term in hits]

    def count_frequencies(self, texts: Sequence[str]) -> None:
        """Update ``frequency`` for every term across the supplied texts."""
        combined = "\n".join(texts)
        haystack = normalise_arabic(combined, keep_diacritics=False).lower()
        for term in self.terms:
            total = 0
            for form in [term.source] + list(term.aliases):
                needle = normalise_arabic(form, keep_diacritics=False).lower()
                if len(needle) < 2:
                    continue
                total += haystack.count(needle)
            term.frequency = total

    # -- rendering ----------------------------------------------------------
    def to_markdown_table(self, terms: Optional[Sequence[Term]] = None) -> str:
        rows = terms if terms is not None else self.terms
        if not rows:
            return ""
        header = "| source | target | category | gender | aliases | note |"
        rule = "| --- | --- | --- | --- | --- | --- |"
        lines = [header, rule]
        for term in rows:
            target = term.target if term.target else ("(keep as-is)" if term.keep_as_is else "—")
            aliases = "، ".join(term.aliases) if term.aliases else "—"
            note = term.notes.replace("|", "\\|") if term.notes else "—"
            lines.append(
                f"| {term.source} | {target} | {term.category} | {term.gender} | {aliases} | {note} |"
            )
        return "\n".join(lines)

    def stats(self) -> Dict[str, object]:
        categories: Dict[str, int] = {}
        missing = 0
        for term in self.terms:
            categories[term.category] = categories.get(term.category, 0) + 1
            if not term.target and not term.keep_as_is:
                missing += 1
        return {
            "terms": len(self.terms),
            "untranslated": missing,
            "categories": categories,
        }


def _mask(text: str) -> Tuple[str, List[str]]:
    saved: List[str] = []

    def replace(match: re.Match) -> str:
        saved.append(match.group(0))
        return f" \uE000{len(saved) - 1}\uE000 "

    return PROTECTED.sub(replace, text), saved


def _collapse_runs(words: Sequence[str]) -> List[str]:
    """Collapse consecutive identical words: ["A","A","B"] -> ["A","B"].

    Verbatim repetition ("GitHub GitHub GitHub" in a list) is a repetition, not a
    three-word proper noun. Counting it as a phrase hides the single-word term
    that the glossary actually needs.
    """
    collapsed: List[str] = []
    for word in words:
        if collapsed and collapsed[-1].lower() == word.lower():
            continue
        collapsed.append(word)
    return collapsed


def _ngrams(words: Sequence[str], sizes: Sequence[int] = (2, 3, 4)) -> List[str]:
    grams: List[str] = []
    for size in sizes:
        for start in range(0, max(len(words) - size + 1, 0)):
            gram = " ".join(words[start : start + size])
            if len(gram) <= 60:
                grams.append(gram)
    return grams


def extract_terms(
    texts: Sequence[str],
    min_frequency: int = 2,
    limit: int = 200,
    include_capitalised: bool = True,
) -> List[Term]:
    """Heuristically propose candidate terms from source text.

    This is a *proposal* step: the agent reviews the list and fills in targets.
    Single-word capitalised names are counted per occurrence, while multi-word
    sequences are counted after collapsing verbatim runs, so ``GitHub`` is found
    whether it appears once per paragraph or three times in a row.
    """
    unigrams: Dict[str, int] = {}
    phrases: Dict[str, int] = {}
    original: Dict[str, str] = {}

    def bump(key: str, surface: str, amount: int = 1) -> None:
        if key not in original:
            original[key] = surface
        if " " in key:
            phrases[key] = phrases.get(key, 0) + amount
        else:
            unigrams[key] = unigrams.get(key, 0) + amount

    for text in texts:
        masked, _saved = _mask(text)
        if include_capitalised:
            for match in CAPITALISED_SEQ.finditer(masked):
                words = match.group(0).split()
                for word in words:
                    if word in STOPWORDS or len(word) < 3:
                        continue
                    bump(word.lower(), word)
                collapsed = _collapse_runs(
                    [word for word in words if word not in STOPWORDS]
                )
                if len(collapsed) >= 2:
                    for gram in _ngrams(collapsed):
                        bump(gram.lower(), gram)
        for match in ARABIC_SEQ.finditer(masked):
            token = match.group(0)
            if len(token) < 4:
                continue
            key = normalise_arabic(token, keep_diacritics=False)
            bump(key, token)

    ranked: List[Tuple[int, int, str, str]] = []
    for key, count in unigrams.items():
        if count >= min_frequency:
            ranked.append((count, 0, key, original[key]))
    for key, count in phrases.items():
        if count >= min_frequency:
            # Phrases sort before unigrams of equal frequency: a repeated proper
            # noun phrase is a stronger signal than its head word.
            ranked.append((count, 1, key, original[key]))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))

    terms: List[Term] = []
    seen: set = set()
    for count, _rank, key, surface in ranked:
        if key in seen:
            continue
        seen.add(key)
        terms.append(
            Term(
                source=surface,
                target="",
                category="other",
                confidence="low",
                frequency=count,
            )
        )
        if len(terms) >= limit:
            break
    return terms


def apply_replacements(text: str, glossary: Glossary) -> Tuple[str, List[str]]:
    """Apply known targets to leftover source forms (used for spot checks)."""
    problems: List[str] = []
    output = text
    for term in sorted(glossary.terms, key=lambda item: -len(item.source)):
        if not term.target or term.keep_as_is:
            continue
        forms = [term.source] + list(term.aliases)
        for form in forms:
            pattern = re.compile(r"(?<![\w\u0620-\u064A])" + re.escape(form) + r"(?![\w\u0620-\u064A])")
            if pattern.search(output):
                problems.append(
                    f"source term {form!r} still appears in the target text; "
                    f"expected {term.target!r}"
                )
    return output, problems
