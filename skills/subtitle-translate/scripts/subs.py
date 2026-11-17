#!/usr/bin/env python3
"""Subtitle utilities: parse, measure, validate, and re-time SRT/VTT files.

Standard library only, so it runs anywhere Python runs.

    subs.py stats  input.srt
    subs.py check  source.srt translated.ar.srt
    subs.py shift  input.srt --by 1.5 --out shifted.srt
    subs.py wrap   input.srt --chars 42 --out wrapped.srt

The checker is the useful part: it verifies that a translation did not disturb
the timing grid, that every cue is readable, and that Arabic cues follow the
line-length and reading-speed limits.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

TIMESTAMP = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
)
VTT_HEADER = "WEBVTT"
ARABIC = re.compile(r"[\u0620-\u064A]")
TAGS = re.compile(r"<[^>]+>|\{\\[^}]*\}")


@dataclass
class Cue:
    index: int
    start_ms: int
    end_ms: int
    text: str
    identifier: str = ""
    settings: str = ""

    @property
    def duration(self) -> float:
        return max((self.end_ms - self.start_ms) / 1000.0, 0.0)

    @property
    def lines(self) -> List[str]:
        return self.text.split("\n") if self.text else []

    def plain(self) -> str:
        """Text without markup, for length measurements."""
        return TAGS.sub("", self.text).replace("\n", " ")

    def chars(self) -> int:
        return len(self.plain())

    def cps(self) -> float:
        return round(self.chars() / self.duration, 1) if self.duration else 0.0

    def is_arabic(self) -> bool:
        sample = self.plain()
        return bool(sample) and len(ARABIC.findall(sample)) / max(len(sample), 1) > 0.3


def parse_timestamp(value: str) -> int:
    value = value.replace(",", ".")
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1000
        + int(milliseconds.ljust(3, "0")[:3])
    )


def format_timestamp(milliseconds: int, use_comma: bool = True) -> str:
    milliseconds = max(int(milliseconds), 0)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    separator = "," if use_comma else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"


def parse(text: str) -> Tuple[List[Cue], bool]:
    """Parse SRT or VTT. Returns (cues, is_vtt)."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    is_vtt = normalised.startswith(VTT_HEADER)
    blocks = re.split(r"\n{2,}", normalised)
    cues: List[Cue] = []
    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip() != ""]
        if not lines:
            continue
        if lines[0].strip().startswith((VTT_HEADER, "NOTE", "STYLE", "REGION")):
            continue
        identifier = ""
        timing_index = None
        for position, line in enumerate(lines[:3]):
            if TIMESTAMP.search(line):
                timing_index = position
                break
        if timing_index is None:
            continue
        if timing_index == 1:
            identifier = lines[0].strip()
        match = TIMESTAMP.search(lines[timing_index])
        start = parse_timestamp(match.group("start"))
        end = parse_timestamp(match.group("end"))
        settings = lines[timing_index][match.end() :].strip()
        body = "\n".join(lines[timing_index + 1 :]).strip("\n")
        cues.append(
            Cue(
                index=len(cues) + 1,
                start_ms=start,
                end_ms=end,
                text=body,
                identifier=identifier,
                settings=settings,
            )
        )
    return cues, is_vtt


def serialise(cues: Sequence[Cue], is_vtt: bool = False) -> str:
    out: List[str] = []
    if is_vtt:
        out.append(VTT_HEADER)
        out.append("")
    for cue in cues:
        if is_vtt and cue.identifier:
            out.append(cue.identifier)
        if not is_vtt:
            out.append(str(cue.index))
        timing = (
            f"{format_timestamp(cue.start_ms, use_comma=not is_vtt)} --> "
            f"{format_timestamp(cue.end_ms, use_comma=not is_vtt)}"
        )
        if cue.settings:
            timing += " " + cue.settings
        out.append(timing)
        out.append(cue.text)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def read(path: str) -> Tuple[List[Cue], bool]:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return parse(handle.read())


def write(path: str, cues: Sequence[Cue], is_vtt: bool) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(serialise(cues, is_vtt))


@dataclass
class Findings:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def lint(
    cues: Sequence[Cue],
    max_chars: int = 42,
    max_lines: int = 2,
    max_cps: float = 17.0,
    hard_cps: float = 20.0,
    min_duration: float = 1.0,
    max_duration: float = 7.0,
    min_gap: float = 0.08,
) -> Findings:
    findings = Findings()
    previous: Optional[Cue] = None
    for cue in cues:
        label = f"cue {cue.index}"
        if not cue.text.strip():
            findings.error(f"{label}: empty text")
        if cue.end_ms <= cue.start_ms:
            findings.error(f"{label}: end is not after start")
        if cue.duration < min_duration:
            findings.warn(f"{label}: {cue.duration:.2f}s is shorter than {min_duration}s")
        if cue.duration > max_duration:
            findings.warn(f"{label}: {cue.duration:.2f}s is longer than {max_duration}s; consider a split")
        if len(cue.lines) > max_lines:
            findings.warn(f"{label}: {len(cue.lines)} lines (max {max_lines})")
        for line in cue.lines:
            if len(line) > max_chars:
                findings.warn(
                    f"{label}: line of {len(line)} chars exceeds {max_chars}"
                )
        speed = cue.cps()
        if speed > hard_cps:
            findings.error(f"{label}: {speed} cps exceeds the hard limit of {hard_cps}")
        elif speed > max_cps:
            findings.warn(f"{label}: {speed} cps exceeds {max_cps}")
        if previous is not None:
            if cue.start_ms < previous.end_ms:
                findings.error(
                    f"{label}: overlaps with cue {previous.index} by "
                    f"{(previous.end_ms - cue.start_ms) / 1000:.2f}s"
                )
            elif (cue.start_ms - previous.end_ms) / 1000.0 < min_gap:
                findings.warn(
                    f"{label}: gap of {(cue.start_ms - previous.end_ms) / 1000:.2f}s "
                    f"is below {min_gap}s"
                )
        previous = cue
    return findings


def compare(source: Sequence[Cue], target: Sequence[Cue]) -> Findings:
    findings = Findings()
    if len(source) != len(target):
        findings.error(
            f"cue count differs: source {len(source)}, target {len(target)}; "
            "splits must be reported, not silent"
        )
    for src, tgt in zip(source, target):
        if src.start_ms != tgt.start_ms or src.end_ms != tgt.end_ms:
            findings.error(
                f"cue {src.index}: timing changed "
                f"({format_timestamp(src.start_ms)}–{format_timestamp(src.end_ms)} → "
                f"{format_timestamp(tgt.start_ms)}–{format_timestamp(tgt.end_ms)})"
            )
    return findings


def stats(cues: Sequence[Cue]) -> dict:
    if not cues:
        return {"cues": 0}
    durations = [cue.duration for cue in cues]
    speeds = [cue.cps() for cue in cues]
    return {
        "cues": len(cues),
        "duration": format_timestamp(cues[-1].end_ms),
        "avg_duration": round(sum(durations) / len(durations), 2),
        "avg_cps": round(sum(speeds) / len(speeds), 1),
        "max_cps": max(speeds),
        "cues_over_17cps": sum(1 for speed in speeds if speed > 17),
        "max_chars": max(cue.chars() for cue in cues),
        "three_line_cues": sum(1 for cue in cues if len(cue.lines) > 2),
        "arabic_share": round(
            sum(1 for cue in cues if cue.is_arabic()) / len(cues), 2
        ),
    }


def wrap_lines(text: str, max_chars: int = 42, max_lines: int = 2) -> str:
    """Rewrap a cue at word boundaries without ever dropping words.

    Two-line cues are balanced (equal-ish line lengths read better than one full
    line and one short one). If the text cannot fit in *max_lines* within
    *max_chars*, every word is still emitted: the cue keeps however many lines
    it needs and the linter reports it, because silently deleting text is worse
    than an over-long cue that a translator can then shorten deliberately.
    """
    words = " ".join(text.split()).split(" ")
    if not words or words == [""]:
        return text
    joined = " ".join(words)
    if len(joined) <= max_chars:
        return joined

    if max_lines == 2:
        best: Optional[Tuple[int, str]] = None
        for split in range(1, len(words)):
            first, second = " ".join(words[:split]), " ".join(words[split:])
            if len(first) <= max_chars and len(second) <= max_chars:
                # Prefer a break near the middle of the word count as well as a
                # similar character count: a 5/1 word split reads badly even
                # when the character counts happen to line up.
                score = abs(len(first) - len(second)) + abs(split - (len(words) - split)) * 4
                if best is None or score < best[0]:
                    best = (score, f"{first}\n{second}")
        if best is not None:
            return best[1]

    if max_lines and max_lines > 2:
        best = None
        for split in range(1, len(words) - 1):
            first, rest = " ".join(words[:split]), words[split:]
            for second_split in range(1, len(rest)):
                second, third = " ".join(rest[:second_split]), " ".join(rest[second_split:])
                if all(len(part) <= max_chars for part in (first, second, third)):
                    lengths = (len(first), len(second), len(third))
                    score = max(lengths) - min(lengths)
                    if best is None or score < best[0]:
                        best = (score, f"{first}\n{second}\n{third}")
        if best is not None:
            return best[1]

    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def command_stats(args: argparse.Namespace) -> int:
    cues, _is_vtt = read(args.file)
    report = stats(cues)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    for key, value in report.items():
        print(f"{key:18} {value}")
    findings = lint(
        cues,
        max_chars=args.chars,
        max_cps=args.cps,
        hard_cps=args.hard_cps,
    )
    print()
    print(f"errors: {len(findings.errors)}  warnings: {len(findings.warnings)}")
    for message in findings.errors[:20]:
        print("  error", message)
    for message in findings.warnings[:20]:
        print("  warn ", message)
    return 1 if findings.errors else 0


def command_check(args: argparse.Namespace) -> int:
    source_cues, _ = read(args.source)
    target_cues, is_vtt = read(args.target)
    findings = lint(
        target_cues,
        max_chars=args.chars,
        max_cps=args.cps,
        hard_cps=args.hard_cps,
    )
    if not args.allow_split:
        comparison = compare(source_cues, target_cues)
        findings.errors.extend(comparison.errors)
    else:
        print("note: cue counts may differ because --allow-split is set")
    print(f"source cues: {len(source_cues)}  target cues: {len(target_cues)}")
    print(f"errors: {len(findings.errors)}  warnings: {len(findings.warnings)}")
    for message in findings.errors:
        print("  error", message)
    for message in findings.warnings[:40]:
        print("  warn ", message)
    return 1 if findings.errors else 0


def command_shift(args: argparse.Namespace) -> int:
    cues, is_vtt = read(args.file)
    offset = int(args.by * 1000)
    shifted = [
        Cue(
            index=cue.index,
            start_ms=max(cue.start_ms + offset, 0),
            end_ms=max(cue.end_ms + offset, 0),
            text=cue.text,
            identifier=cue.identifier,
            settings=cue.settings,
        )
        for cue in cues
    ]
    write(args.out, shifted, is_vtt)
    print(f"shifted {len(shifted)} cue(s) by {args.by:+.3f}s → {args.out}")
    return 0


def command_wrap(args: argparse.Namespace) -> int:
    cues, is_vtt = read(args.file)
    rewrapped = [
        Cue(
            index=cue.index,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            text=wrap_lines(cue.text, args.chars, args.lines),
            identifier=cue.identifier,
            settings=cue.settings,
        )
        for cue in cues
    ]
    write(args.out, rewrapped, is_vtt)
    changed = sum(1 for a, b in zip(cues, rewrapped) if a.text != b.text)
    print(f"rewrapped {changed} of {len(cues)} cue(s) → {args.out}")
    return 0


def command_dump(args: argparse.Namespace) -> int:
    cues, _ = read(args.file)
    for cue in cues:
        print(f"{cue.index:4} {format_timestamp(cue.start_ms)} {cue.duration:5.2f}s {cue.cps():5.1f}cps")
        for line in cue.lines:
            print("     |", line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SRT/VTT subtitle utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    stats_parser = sub.add_parser("stats", help="measure a subtitle file")
    stats_parser.add_argument("file")
    stats_parser.add_argument("--chars", type=int, default=42)
    stats_parser.add_argument("--cps", type=float, default=17.0)
    stats_parser.add_argument("--hard-cps", type=float, default=20.0)
    stats_parser.add_argument("--json", action="store_true")
    stats_parser.set_defaults(func=command_stats)

    check_parser = sub.add_parser("check", help="validate a translation against its source")
    check_parser.add_argument("source")
    check_parser.add_argument("target")
    check_parser.add_argument("--chars", type=int, default=42)
    check_parser.add_argument("--cps", type=float, default=17.0)
    check_parser.add_argument("--hard-cps", type=float, default=20.0)
    check_parser.add_argument("--allow-split", action="store_true")
    check_parser.set_defaults(func=command_check)

    shift_parser = sub.add_parser("shift", help="shift all cues by N seconds")
    shift_parser.add_argument("file")
    shift_parser.add_argument("--by", type=float, required=True)
    shift_parser.add_argument("--out", required=True)
    shift_parser.set_defaults(func=command_shift)

    wrap_parser = sub.add_parser("wrap", help="rewrap cue lines")
    wrap_parser.add_argument("file")
    wrap_parser.add_argument("--chars", type=int, default=42)
    wrap_parser.add_argument("--lines", type=int, default=2)
    wrap_parser.add_argument("--out", required=True)
    wrap_parser.set_defaults(func=command_wrap)

    dump_parser = sub.add_parser("dump", help="print cues with metrics")
    dump_parser.add_argument("file")
    dump_parser.set_defaults(func=command_dump)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
