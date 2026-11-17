"""Translation memory: do not pay twice for the same sentence.

A TM entry maps a normalised source sentence to a human-approved target
sentence.  When a document is re-translated, or a new document quotes an
earlier one, those sentences are reused verbatim, which keeps terminology and
voice stable and cuts the work a sub-agent must do.

Only sentences above a minimum length are stored; short strings ("Yes", "Ok")
match by accident and make reuse worse, not better.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .arabic import normalise_arabic, strip_diacritics

SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟۔。！？])\s+(?=[^\s])")
MIN_SOURCE_CHARS = 24
MIN_TARGET_CHARS = 10


def normalise_key(text: str) -> str:
    """Stable key for a sentence: same words, punctuation, and case fold."""
    folded = normalise_arabic(strip_diacritics(text), keep_diacritics=False)
    folded = re.sub(r"[\s\u00A0]+", " ", folded).strip().lower()
    # Drop all punctuation so "Hello, World!" and "hello world" share a key,
    # while letters, digits, and Arabic marks keep their identity.
    folded = re.sub(r"[^\w\s\u0620-\u064A]", "", folded)
    return re.sub(r"\s+", " ", folded).strip()


def split_sentences(text: str) -> List[str]:
    pieces: List[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph or paragraph.startswith(("```", "|")):
            pieces.append(paragraph)
            continue
        pieces.extend(part.strip() for part in SENTENCE_SPLIT.split(paragraph) if part.strip())
    return pieces


@dataclass
class MemoryEntry:
    source: str
    target: str
    source_language: str
    target_language: str
    glossary_hash: str = ""
    approved: bool = True

    @property
    def key(self) -> str:
        digest = hashlib.sha256(
            (normalise_key(self.source) + "\u241F" + self.target_language).encode("utf-8")
        ).hexdigest()
        return digest[:32]


class TranslationMemory:
    def __init__(self, entries: Optional[Iterable[MemoryEntry]] = None) -> None:
        self.entries: Dict[str, MemoryEntry] = {}
        for entry in entries or []:
            self.entries[entry.key] = entry

    @classmethod
    def load(cls, path: str) -> "TranslationMemory":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        entries = [
            MemoryEntry(
                source=item["source"],
                target=item["target"],
                source_language=item.get("source_language", ""),
                target_language=item.get("target_language", ""),
                glossary_hash=item.get("glossary_hash", ""),
                approved=item.get("approved", True),
            )
            for item in data.get("entries", [])
        ]
        return cls(entries)

    def save(self, path: str) -> None:
        payload = {
            "version": 1,
            "entries": [
                {
                    "key": entry.key,
                    "source": entry.source,
                    "target": entry.target,
                    "source_language": entry.source_language,
                    "target_language": entry.target_language,
                    "glossary_hash": entry.glossary_hash,
                    "approved": entry.approved,
                }
                for entry in self.entries.values()
            ],
        }
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def lookup(self, source: str, target_language: str) -> Optional[MemoryEntry]:
        digest = hashlib.sha256(
            (normalise_key(source) + "\u241F" + target_language).encode("utf-8")
        ).hexdigest()[:32]
        return self.entries.get(digest)

    def add(self, entry: MemoryEntry) -> None:
        if len(entry.source) < MIN_SOURCE_CHARS or len(entry.target) < MIN_TARGET_CHARS:
            return
        if not entry.target.strip() or entry.target.strip() == entry.source.strip():
            return
        self.entries[entry.key] = entry

    def reuse(
        self, source_text: str, target_language: str
    ) -> Tuple[str, List[Tuple[str, str]], int]:
        """Replace reusable sentences; return (prefilled, leftovers, hit count)."""
        hits: List[Tuple[str, str]] = []
        leftovers: List[str] = []
        for sentence in split_sentences(source_text):
            if not sentence.strip():
                continue
            entry = self.lookup(sentence, target_language)
            if entry and entry.approved:
                hits.append((sentence, entry.target))
            else:
                leftovers.append(sentence)
        return ("\n".join(target for _src, target in hits), leftovers, len(hits))

    def learn_from_pair(
        self,
        source_path: str,
        target_path: str,
        source_language: str,
        target_language: str,
        glossary_hash: str = "",
    ) -> int:
        """Align paragraphs one-to-one and store them as approved pairs."""
        with open(source_path, "r", encoding="utf-8") as handle:
            source_blocks = [b.strip() for b in re.split(r"\n\s*\n", handle.read()) if b.strip()]
        with open(target_path, "r", encoding="utf-8") as handle:
            target_blocks = [b.strip() for b in re.split(r"\n\s*\n", handle.read()) if b.strip()]
        if len(source_blocks) != len(target_blocks):
            raise ValueError(
                f"paragraph counts differ (source {len(source_blocks)}, target {len(target_blocks)}); "
                "align the files before learning from them"
            )
        added = 0
        for source_block, target_block in zip(source_blocks, target_blocks):
            if source_block.startswith(("```", "|", "#")) or target_block.startswith(("```", "|", "#")):
                continue
            if len(source_block) < MIN_SOURCE_CHARS:
                continue
            entry = MemoryEntry(
                source=source_block,
                target=target_block,
                source_language=source_language,
                target_language=target_language,
                glossary_hash=glossary_hash,
            )
            self.add(entry)
            added += 1
        return added

    def stats(self) -> Dict[str, int]:
        return {"entries": len(self.entries)}
