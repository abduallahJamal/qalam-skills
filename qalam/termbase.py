"""Terminology extraction from documents, codebases, and subtitle files.

``contains_arabic`` exists for one reason: the CLI prints Arabic counts and
terms, and a Windows console in the default code page raises
``UnicodeEncodeError`` on that output *before* any file is written. Detecting
the limitation lets the CLI fall back to ASCII instead of crashing.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .glossary import Glossary, Term, extract_terms
from .skillmd import iter_skill_files, load as load_skill

# ---------------------------------------------------------------- source reading


def strip_fenced_blocks(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "\n", text)


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :]
    return text


def read_markdown_sources(paths: Sequence[str], include_skills: bool = False) -> Dict[str, str]:
    """Map path -> prose text, with code and metadata removed.

    A SKILL.md is mostly instructions, so its body is prose; but when the
    caller only wants to learn a project's *vocabulary*, the frontmatter and
    code fences are noise and are dropped.
    """
    collected: Dict[str, str] = {}
    for path in paths:
        text = ""
        if os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for name in sorted(files):
                    if name.lower().endswith((".md", ".markdown", ".mdx", ".txt")):
                        full = os.path.join(root, name)
                        with open(full, "r", encoding="utf-8", errors="replace") as handle:
                            collected[full] = strip_fenced_blocks(strip_frontmatter(handle.read()))
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        if include_skills and os.path.basename(path) == "SKILL.md":
            doc = load_skill(path)
            text = doc.body
        collected[path] = strip_fenced_blocks(strip_frontmatter(text))
    return collected


def read_code_identifiers(paths: Sequence[str], limit_files: int = 400) -> Dict[str, int]:
    """Count identifier-like tokens across source files, per file type."""
    counter: Dict[str, int] = {}
    extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".cs",
        ".rb", ".php", ".swift", ".m", ".c", ".h", ".cpp", ".scala", ".ex", ".exs",
    }
    token = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
    files_seen = 0
    for path in paths:
        walker = os.walk(path) if os.path.isdir(path) else [(os.path.dirname(path), [], [os.path.basename(path)])]
        for root, dirs, files in walker:
            dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "dist", "build", "bin", "obj", ".venv", "venv"}]
            for name in files:
                if os.path.splitext(name)[1].lower() not in extensions:
                    continue
                files_seen += 1
                if files_seen > limit_files:
                    return counter
                full = os.path.join(root, name)
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as handle:
                        for match in token.finditer(handle.read()):
                            word = match.group(0)
                            if word.startswith("_") or len(word) < 4:
                                continue
                            counter[word] = counter.get(word, 0) + 1
                except OSError:
                    continue
    return counter


def shared_code_terms(counters: Sequence[Dict[str, int]], min_total: int = 3) -> List[str]:
    totals: Dict[str, int] = {}
    for counter in counters:
        for word, count in counter.items():
            totals[word] = totals.get(word, 0) + count
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, count in ranked if count >= min_total]


# ---------------------------------------------------------------- proposals


def propose_glossary(
    sources: Dict[str, str],
    min_frequency: int = 2,
    limit: int = 200,
) -> Glossary:
    texts = list(sources.values())
    terms = extract_terms(texts, min_frequency=min_frequency, limit=limit)
    return Glossary(terms=terms)


def suggest_for_code(
    identifiers: Sequence[str], glossary: Optional[Glossary] = None
) -> List[Term]:
    """Propose terms for identifiers that should stay untranslated in prose."""
    known = glossary or Glossary()
    proposals: List[Term] = []
    for identifier in identifiers:
        if known.find(identifier):
            continue
        proposals.append(
            Term(
                source=identifier,
                target=identifier,
                category="technical",
                keep_as_is=True,
                confidence="high",
                notes="code identifier; never translate, keep verbatim",
            )
        )
    return proposals


# ---------------------------------------------------------------- console safety


def contains_arabic(text: str) -> bool:
    return any("\u0600" <= char <= "\u06FF" or "\uFB50" <= char <= "\uFDFF" for char in text)


def console_encoding() -> str:
    return (getattr(sys.stdout, "encoding", None) or "ascii").lower()


def _encoding_can_encode_arabic(encoding: str) -> bool:
    try:
        "العربية".encode(encoding, errors="strict")
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def ascii_safe(text: str, marker: str = "[AR]") -> str:
    """Replace non-ASCII with explicit markers so nothing crashes on output."""
    if _encoding_can_encode_arabic(console_encoding()):
        return text
    out = []
    for char in text:
        if ord(char) < 128:
            out.append(char)
        elif contains_arabic(char):
            out.append(marker)
        else:
            out.append("?")
    return "".join(out)


def safe_print(text: str) -> None:
    """Print without ever raising on an ASCII-only console."""
    safe = ascii_safe(text)
    try:
        print(safe)
    except UnicodeEncodeError:
        print(safe.encode("ascii", errors="replace").decode("ascii"))


def prepare_console() -> None:
    """Best-effort UTF-8 console setup, ignoring hosts that cannot."""
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
