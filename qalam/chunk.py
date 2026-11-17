"""Chunking for long documents.

Chunks are the unit of work for a translating sub-agent, so they must be:

* small enough that a model can hold one in context and finish it,
* cut on structure (headings, blank lines) rather than mid-sentence,
* balanced so fenced code blocks and tables stay whole,
* resumable, because a translation run is planned to be interrupted.

The chunker never rewrites your text. It only records byte ranges, and every
chunk carries a hash so a later run can tell whether the source changed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

FENCE = re.compile(r"^(```|~~~)\s*([\w+-]*)")
HEADING = re.compile(r"^(#{1,6})\s+\S")
BLANK = re.compile(r"^\s*$")


@dataclass
class Chunk:
    index: int
    text: str
    start_line: int           # 1-based, inclusive
    end_line: int             # 1-based, inclusive
    heading_path: Tuple[str, ...] = ()
    has_code: bool = False
    has_table: bool = False
    chars: int = field(init=False)
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        self.chars = len(self.text)
        self.sha256 = hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def id(self) -> str:
        return f"chunk{self.index:04d}"

    def summary(self) -> str:
        title = " › ".join(self.heading_path) if self.heading_path else "(no heading)"
        flags = []
        if self.has_code:
            flags.append("code")
        if self.has_table:
            flags.append("table")
        flag_text = f" [{', '.join(flags)}]" if flags else ""
        return f"{self.id}  lines {self.start_line}-{self.end_line}  {self.chars} chars{flag_text}  {title}"


class ChunkingError(ValueError):
    pass


def _classify(lines: List[str]) -> Tuple[List[bool], List[bool], List[str]]:
    """Return per-line (in_fence, is_table, heading_path_at_line)."""
    in_fence = False
    fence_marker = ""
    heading_stack: List[Tuple[int, str]] = []
    in_fence_flags: List[bool] = []
    table_flags: List[bool] = []
    paths: List[str] = []
    for line in lines:
        match = FENCE.match(line)
        if match:
            if not in_fence:
                in_fence = True
                fence_marker = match.group(1)
            elif line.startswith(fence_marker):
                in_fence_flags.append(True)
                table_flags.append(False)
                paths.append(" › ".join(h[1] for h in heading_stack))
                in_fence = False
                continue
            in_fence_flags.append(True)
            table_flags.append(False)
            paths.append(" › ".join(h[1] for h in heading_stack))
            continue
        if in_fence:
            in_fence_flags.append(True)
            table_flags.append(False)
            paths.append(" › ".join(h[1] for h in heading_stack))
            continue
        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            title = line[level:].strip()
            heading_stack = [h for h in heading_stack if h[0] < level] + [(level, title)]
        in_fence_flags.append(False)
        table_flags.append(line.lstrip().startswith("|"))
        paths.append(" › ".join(h[1] for h in heading_stack))
    return in_fence_flags, table_flags, paths


def _split_points(
    lines: List[str], in_fence: List[bool], table: List[bool]
) -> List[int]:
    """Indices where a chunk may legitimately start (0-based, blank-line gaps)."""
    points = [0]
    for index in range(1, len(lines)):
        if in_fence[index] or in_fence[index - 1]:
            continue
        if BLANK.match(lines[index - 1]) and not BLANK.match(lines[index]):
            if not table[index - 1] and not table[index]:
                points.append(index)
    return points


def split_text(
    text: str,
    target_chars: int = 6000,
    max_chars: int = 12000,
    preserve_code: bool = True,
) -> List[Chunk]:
    """Split *text* into chunks of roughly *target_chars* characters.

    A chunk never exceeds *max_chars* unless a single fenced code block or
    table is larger than that, because splitting either would corrupt them.
    """
    if target_chars < 200:
        raise ChunkingError("target_chars must be at least 200")
    if max_chars < target_chars:
        raise ChunkingError("max_chars must be >= target_chars")

    lines = text.splitlines()
    if not lines:
        return []
    in_fence, table, paths = _classify(lines)
    points = _split_points(lines, in_fence, table)

    chunks: List[Chunk] = []
    start = 0
    while start < len(lines):
        budget_end = None
        cursor = start
        chars = 0
        while cursor < len(lines):
            chars += len(lines[cursor]) + 1
            if chars > max_chars and cursor > start:
                budget_end = cursor
                break
            cursor += 1
        if budget_end is None:
            budget_end = len(lines)

        cut = budget_end
        if budget_end < len(lines):
            candidates = [p for p in points if start < p <= budget_end]
            if candidates:
                cut = candidates[-1]
            elif preserve_code:
                # Try to extend to the next legal split rather than cut code.
                forward = [p for p in points if p > budget_end]
                if forward and forward[0] - start <= max_chars * 2:
                    cut = forward[0]

        body = "\n".join(lines[start:cut]).strip("\n")
        if body:
            chunks.append(
                Chunk(
                    index=len(chunks) + 1,
                    text=body,
                    start_line=start + 1,
                    end_line=cut,
                    heading_path=tuple(x for x in paths[start].split(" › ") if x),
                    has_code=any(in_fence[start:cut]),
                    has_table=any(table[start:cut]),
                )
            )
        start = cut

    for chunk in chunks:
        if chunk.chars > max_chars:
            chunk.text = chunk.text  # kept whole on purpose; reported by check()
    return chunks


def check_chunks(chunks: Iterable[Chunk], max_chars: int = 12000) -> List[str]:
    """Post-conditions: order, contiguity, and size."""
    problems: List[str] = []
    items = list(chunks)
    for position, chunk in enumerate(items, start=1):
        if chunk.index != position:
            problems.append(f"chunk {position} has index {chunk.index}")
        if chunk.chars > max_chars:
            problems.append(
                f"{chunk.id} is {chunk.chars} chars (> {max_chars}); it is an "
                "unsplittable block, keep it whole"
            )
    for previous, current in zip(items, items[1:]):
        if current.start_line != previous.end_line + 1:
            problems.append(
                f"{previous.id} ends at line {previous.end_line} but "
                f"{current.id} starts at line {current.start_line}"
            )
    return problems


def write_chunks(
    text: str, out_dir: str, target_chars: int = 6000, max_chars: int = 12000
) -> List[Chunk]:
    """Write ``chunkNNNN.md`` files and return the chunk metadata."""
    import json
    import os

    chunks = split_text(text, target_chars=target_chars, max_chars=max_chars)
    os.makedirs(out_dir, exist_ok=True)
    for chunk in chunks:
        with open(os.path.join(out_dir, f"{chunk.id}.md"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(chunk.text + "\n")
    manifest = {
        "version": 1,
        "target_chars": target_chars,
        "max_chars": max_chars,
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "chunks": [
            {
                "id": chunk.id,
                "file": f"{chunk.id}.md",
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chars": chunk.chars,
                "sha256": chunk.sha256,
                "heading_path": list(chunk.heading_path),
                "has_code": chunk.has_code,
                "has_table": chunk.has_table,
            }
            for chunk in chunks
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return chunks


def merge_outputs(source_dir: str, out_dir: str, output_path: str) -> Tuple[int, List[str]]:
    """Concatenate ``output_chunkNNNN.md`` in index order.

    Returns ``(chunks_merged, warnings)``. A missing translation is a warning,
    never silently skipped: the caller decides whether that is fatal.
    """
    import os
    import re as _re

    pattern = _re.compile(r"^output_chunk(\d+)\.md$")
    found: List[Tuple[int, str]] = []
    for name in sorted(os.listdir(out_dir)):
        match = pattern.match(name)
        if match:
            found.append((int(match.group(1)), name))
    warnings: List[str] = []
    if not found:
        raise ChunkingError(f"no output_chunkNNNN.md files in {out_dir}")
    found.sort()
    ids = [index for index, _ in found]

    # The expected set comes from the source directory when it is available:
    # an output that was never written leaves no gap in the numbering, so a
    # range check alone would silently drop a whole chunk of the book.
    expected: List[int] = list(range(1, max(ids) + 1))
    if os.path.isdir(source_dir):
        source_pattern = _re.compile(r"^chunk(\d+)\.md$")
        source_ids = sorted(
            int(match.group(1))
            for name in os.listdir(source_dir)
            if (match := source_pattern.match(name))
        )
        if source_ids:
            expected = source_ids
    missing = sorted(set(expected) - set(ids))
    if missing:
        warnings.append(
            "missing translations for: " + ", ".join(f"chunk{i:04d}" for i in missing)
        )
    parts: List[str] = []
    for index, name in found:
        with open(os.path.join(out_dir, name), "r", encoding="utf-8") as handle:
            body = handle.read().strip("\n")
        if not body.strip():
            warnings.append(f"{name} is blank")
            continue
        parts.append(body)
    merged = "\n\n".join(parts).strip("\n") + "\n"
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(merged)
    return len(found), warnings
