"""Resumable run state and a selective re-translation planner.

A book translation is long enough that it will be interrupted.  This module
records, per chunk, what the translation was produced from: the source hash and
the exact set of glossary entries that applied to it.  On the next run it can
then answer one question precisely:

    which chunks must be translated again?

The answer is "a chunk whose source text changed, or whose applicable terms
changed" — nothing else.  Editing one glossary line re-translates only the
chunks that contain that term, instead of the whole book.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .arabic import normalise_arabic
from .glossary import Glossary, Term

STATE_FILE = "run_state.json"
STATE_VERSION = 1


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def term_signature(term: Term) -> str:
    """Identity of a glossary decision, including aliases.

    Aliases are part of the signature on purpose: adding an alias changes what
    a chunk is allowed to translate, so it must invalidate the chunks that use
    it. This mirrors the defect fixed upstream in translate-book, where an alias
    edit silently left stale translations in place.
    """
    payload = "\u241F".join(
        [
            normalise_arabic(term.source, keep_diacritics=False),
            normalise_arabic(term.target, keep_diacritics=False),
            term.category,
            term.gender,
            "keep" if term.keep_as_is else "translate",
            "\u241E".join(sorted(normalise_arabic(a, keep_diacritics=False) for a in term.aliases)),
        ]
    )
    return _hash(payload)[:16]


def applicable_terms(text: str, glossary: Optional[Glossary]) -> List[Term]:
    if glossary is None:
        return []
    return glossary.matching(text)


def chunk_terms_signature(text: str, glossary: Optional[Glossary]) -> str:
    terms = applicable_terms(text, glossary)
    payload = "\u241F".join(sorted(term_signature(term) for term in terms))
    return _hash(payload)[:16]


@dataclass
class ChunkState:
    chunk_id: str
    source_sha256: str
    terms_signature: str
    output_sha256: str = ""
    target_language: str = ""
    status: str = "translated"     # translated / failed / review
    note: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "chunk_id": self.chunk_id,
            "source_sha256": self.source_sha256,
            "terms_signature": self.terms_signature,
            "output_sha256": self.output_sha256,
            "target_language": self.target_language,
            "status": self.status,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ChunkState":
        return cls(
            chunk_id=str(data.get("chunk_id", "")),
            source_sha256=str(data.get("source_sha256", "")),
            terms_signature=str(data.get("terms_signature", "")),
            output_sha256=str(data.get("output_sha256", "")),
            target_language=str(data.get("target_language", "")),
            status=str(data.get("status", "translated")),
            note=str(data.get("note", "")),
        )


class RunState:
    def __init__(self, chunks: Optional[Dict[str, ChunkState]] = None) -> None:
        self.chunks: Dict[str, ChunkState] = chunks or {}

    @classmethod
    def path_for(cls, directory: str) -> str:
        return os.path.join(directory, STATE_FILE)

    @classmethod
    def load(cls, directory: str) -> "RunState":
        path = cls.path_for(directory)
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("version") != STATE_VERSION:
            raise ValueError(
                f"{path} was written by a different run_state version "
                f"({data.get('version')}); move it aside to start fresh"
            )
        chunks = {
            key: ChunkState.from_dict(value) for key, value in data.get("chunks", {}).items()
        }
        return cls(chunks)

    def save(self, directory: str) -> None:
        path = self.path_for(directory)
        temporary = path + ".tmp"
        payload = {
            "version": STATE_VERSION,
            "chunks": {key: value.to_dict() for key, value in sorted(self.chunks.items())},
        }
        with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)

    def record(
        self,
        chunk_id: str,
        source_text: str,
        output_text: str,
        glossary: Optional[Glossary],
        target_language: str,
        status: str = "translated",
        note: str = "",
    ) -> ChunkState:
        if not output_text.strip():
            raise ValueError(
                f"{chunk_id}: refusing to record an empty translation as done"
            )
        state = ChunkState(
            chunk_id=chunk_id,
            source_sha256=_hash(source_text),
            terms_signature=chunk_terms_signature(source_text, glossary),
            output_sha256=_hash(output_text),
            target_language=target_language,
            status=status,
            note=note,
        )
        self.chunks[chunk_id] = state
        return state


@dataclass
class Plan:
    translate: List[str] = field(default_factory=list)
    record_only: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    reasons: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "translation_chunk_ids": self.translate,
            "record_only_chunk_ids": self.record_only,
            "unchanged_chunk_ids": self.unchanged,
            "reasons": self.reasons,
        }


CHUNK_FILE = re.compile(r"^chunk(\d+)\.md$")
OUTPUT_FILE = re.compile(r"^output_chunk(\d+)\.md$")


def read_pairs(directory: str) -> List[Tuple[str, str, Optional[str]]]:
    """Return ``(chunk_id, source_text, output_text_or_None)`` in order."""
    sources: Dict[str, str] = {}
    outputs: Dict[str, str] = {}
    for name in sorted(os.listdir(directory)):
        match = CHUNK_FILE.match(name)
        if match:
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                sources[f"chunk{int(match.group(1)):04d}"] = handle.read()
            continue
        match = OUTPUT_FILE.match(name)
        if match:
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                outputs[f"chunk{int(match.group(1)):04d}"] = handle.read()
    pairs: List[Tuple[str, str, Optional[str]]] = []
    for chunk_id in sorted(sources):
        pairs.append((chunk_id, sources[chunk_id], outputs.get(chunk_id)))
    return pairs


def plan(
    directory: str,
    glossary: Optional[Glossary] = None,
    target_language: str = "",
    retranslate_untracked: bool = False,
) -> Plan:
    """Decide what to translate, what to record, and what to leave alone."""
    state = RunState.load(directory)
    result = Plan()
    for chunk_id, source_text, output_text in read_pairs(directory):
        expected_source = _hash(source_text)
        expected_terms = chunk_terms_signature(source_text, glossary)
        recorded = state.chunks.get(chunk_id)

        if output_text is None or not output_text.strip():
            result.translate.append(chunk_id)
            result.reasons[chunk_id] = "no_output" if output_text is None else "blank_output"
            continue
        if recorded is None:
            if retranslate_untracked:
                result.translate.append(chunk_id)
                result.reasons[chunk_id] = "untracked"
            else:
                # An output exists but has no state record: it was produced
                # before run_state existed. Record it rather than paying to
                # translate it again, unless the caller asked for a full redo.
                result.record_only.append(chunk_id)
                result.reasons[chunk_id] = "untracked_output"
            continue
        if recorded.source_sha256 != expected_source:
            result.translate.append(chunk_id)
            result.reasons[chunk_id] = "source_changed"
            continue
        if recorded.terms_signature != expected_terms:
            result.translate.append(chunk_id)
            result.reasons[chunk_id] = "glossary_changed"
            continue
        if target_language and recorded.target_language and recorded.target_language != target_language:
            result.translate.append(chunk_id)
            result.reasons[chunk_id] = "target_language_changed"
            continue
        if recorded.status != "translated":
            result.translate.append(chunk_id)
            result.reasons[chunk_id] = f"status_{recorded.status}"
            continue
        if _hash(output_text) != recorded.output_sha256:
            result.translate.append(chunk_id)
            result.reasons[chunk_id] = "output_modified"
            continue
        result.unchanged.append(chunk_id)
    return result


def certify(directory: str, glossary: Optional[Glossary] = None, target_language: str = "") -> List[str]:
    """Record every valid existing output; print-ready list of problems."""
    state = RunState.load(directory)
    problems: List[str] = []
    for chunk_id, source_text, output_text in read_pairs(directory):
        if output_text is None or not output_text.strip():
            problems.append(f"{chunk_id}: no usable output")
            continue
        state.record(chunk_id, source_text, output_text, glossary, target_language)
    state.save(directory)
    return problems
