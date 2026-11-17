"""Quality gate for translated Markdown.

The gate is deliberately mechanical. It cannot judge style, but it reliably
catches the failures that make a translation unusable: dropped sentences,
duplicated paragraphs, lost code, broken brackets, untranslated blocks, wrong
numeral script, and terminology drift against the glossary.

Every check returns a :class:`Finding` with a stable ``code`` so a CI job, a
skill, or a human reviewer can filter them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from .arabic import (
    ARABIC_LETTER_RE,
    ARABIC_MT_SMELLS,
    balance_brackets,
    normalise_digits,
    script_distribution,
    strip_diacritics,
)
from .glossary import Glossary
from .textutil import (
    compare_structures,
    length_ratio_band,
    numbers_in,
    quality_metrics,
    structure_fingerprint,
)

SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

FENCE_BLOCK = re.compile(r"```[^\n]*\n([\s\S]*?)```")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
LATIN_WORD = re.compile(r"\b[A-Za-z][A-Za-z'’-]{2,}\b")
DOUBLE_SPACE = re.compile(r"[ \t]{2,}")
SENTENCE_END = re.compile(r"[.!?؟।。！？]")


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    location: str = ""

    def render(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.severity.upper():5} {self.code:22} {self.message}{where}"


def _block_id(position: int) -> str:
    return f"line {position}"


# ---------------------------------------------------------------- individual checks


def check_length_ratio(
    source: str, target: str, source_language: str, target_language: str
) -> List[Finding]:
    metrics = quality_metrics(source, target)
    low, high = length_ratio_band(source_language, target_language)
    ratio = float(metrics["length_ratio"])
    if ratio == 0:
        return [Finding("length_ratio", "error", "target text is empty")]
    if ratio < low:
        return [
            Finding(
                "length_ratio",
                "error",
                f"target/source word ratio {ratio} is below the {low}-{high} band; "
                "content is probably missing",
            )
        ]
    if ratio > high:
        return [
            Finding(
                "length_ratio",
                "warn",
                f"target/source word ratio {ratio} is above the {low}-{high} band; "
                "check for duplicated or padded text",
            )
        ]
    return []


def check_duplicate_paragraphs(target: str, min_chars: int = 60) -> List[Finding]:
    seen: Dict[str, int] = {}
    findings: List[Finding] = []
    for position, paragraph in enumerate(re.split(r"\n\s*\n", target)):
        cleaned = paragraph.strip()
        if len(cleaned) < min_chars or cleaned.startswith(("```", "|")):
            continue
        key = re.sub(r"\s+", " ", cleaned)
        if key in seen:
            findings.append(
                Finding(
                    "duplicate_paragraph",
                    "error",
                    f"paragraph repeats the one at block {seen[key]}",
                    f"block {position}",
                )
            )
        else:
            seen[key] = position
    return findings


def check_structure(source: str, target: str) -> List[Finding]:
    return [
        Finding("structure", "error", f"{problem}")
        for problem in compare_structures(source, target)
    ]


def check_code_blocks(source: str, target: str) -> List[Finding]:
    findings: List[Finding] = []
    source_blocks = [match.group(1).strip() for match in FENCE_BLOCK.finditer(source)]
    target_blocks = [match.group(1).strip() for match in FENCE_BLOCK.finditer(target)]
    if len(source_blocks) != len(target_blocks):
        findings.append(
            Finding(
                "code_blocks",
                "error",
                f"source has {len(source_blocks)} fenced blocks, target has {len(target_blocks)}",
            )
        )
    for index, (src, tgt) in enumerate(zip(source_blocks, target_blocks), start=1):
        if src != tgt:
            findings.append(
                Finding(
                    "code_changed",
                    "error",
                    "code block content changed; code and commands must be copied verbatim",
                    f"block {index}",
                )
            )
    return findings


def check_inline_code(source: str, target: str) -> List[Finding]:
    source_spans = sorted(match.group(1) for match in INLINE_CODE.finditer(source))
    target_spans = sorted(match.group(1) for match in INLINE_CODE.finditer(target))
    if source_spans == target_spans:
        return []
    missing = [span for span in source_spans if span not in target_spans]
    added = [span for span in target_spans if span not in source_spans]
    detail = []
    if missing:
        detail.append("missing: " + ", ".join(f"`{s}`" for s in missing[:5]))
    if added:
        detail.append("added: " + ", ".join(f"`{s}`" for s in added[:5]))
    return [Finding("inline_code", "error", "; ".join(detail))]


def check_links(source: str, target: str) -> List[Finding]:
    findings: List[Finding] = []
    source_targets = [match.group(2) for match in LINK.finditer(source)]
    target_targets = [match.group(2) for match in LINK.finditer(target)]
    source_images = [match.group(2) for match in IMAGE.finditer(source)]
    target_images = [match.group(2) for match in IMAGE.finditer(target)]
    missing = [url for url in source_targets if url not in target_targets]
    if missing:
        findings.append(
            Finding(
                "links",
                "error",
                "link targets lost: " + ", ".join(missing[:5]),
            )
        )
    missing_images = [path for path in source_images if path not in target_images]
    if missing_images:
        findings.append(
            Finding(
                "images",
                "error",
                "image paths lost: " + ", ".join(missing_images[:5]),
            )
        )
    for match in IMAGE.finditer(target):
        if not match.group(1).strip():
            findings.append(Finding("image_alt", "warn", "image has an empty alt text"))
    return findings


def check_numbers(source: str, target: str) -> List[Finding]:
    source_numbers = numbers_in(source)
    target_numbers = numbers_in(target)
    if sorted(source_numbers) == sorted(target_numbers):
        return []
    missing = [value for value in source_numbers if value not in target_numbers]
    added = [value for value in target_numbers if value not in source_numbers]
    detail_parts = []
    if missing:
        detail_parts.append("missing: " + ", ".join(missing[:8]))
    if added:
        detail_parts.append("extra: " + ", ".join(added[:8]))
    return [
        Finding(
            "numbers",
            "warn",
            "numeric values differ between source and target ("
            + "; ".join(detail_parts)
            + "); verify against the original",
        )
    ]


def check_untranslated(source: str, target: str, threshold: float = 0.25) -> List[Finding]:
    """Flag target lines that are still mostly source-script text."""
    findings: List[Finding] = []
    source_distribution = script_distribution(source)
    target_distribution = script_distribution(target)
    source_latin = source_distribution["latin"] > 0.4
    source_arabic = source_distribution["arabic"] > 0.4
    in_fence = False
    for position, line in enumerate(target.splitlines(), start=1):
        stripped = line.strip()
        # Track fence state: code inside a fenced block is *supposed* to stay in
        # the source language, so reporting it as "untranslated" is pure noise
        # and trains reviewers to ignore the check.
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped or stripped.startswith(("|", "    ")):
            continue
        if "](http" in line or stripped.startswith("!["):
            continue
        distribution = script_distribution(line)
        if source_latin and target_distribution["arabic"] > 0.2:
            if distribution["latin"] > threshold and distribution["arabic"] < 0.1:
                findings.append(
                    Finding(
                        "untranslated",
                        "warn",
                        f"line looks untranslated ({int(distribution['latin'] * 100)}% Latin): "
                        + line.strip()[:80],
                        f"line {position}",
                    )
                )
        elif source_arabic and target_distribution["latin"] > 0.2:
            if distribution["arabic"] > threshold and distribution["latin"] < 0.1:
                findings.append(
                    Finding(
                        "untranslated",
                        "warn",
                        "line still in the source language: " + line.strip()[:80],
                        f"line {position}",
                    )
                )
    return findings


def check_link_text(source: str, target: str, threshold: float = 0.6) -> List[Finding]:
    """Link text is human-facing content and must be translated.

    A target that keeps ``[the parser notes](…)`` verbatim has translated the
    document but not the link, which readers notice immediately.
    """
    findings: List[Finding] = []
    source_links = {match.group(2): match.group(1) for match in LINK.finditer(source)}
    for match in LINK.finditer(target):
        text, url = match.group(1), match.group(2)
        original = source_links.get(url)
        if original is None or not original.strip():
            continue
        if text.strip() != original.strip():
            continue
        distribution = script_distribution(text)
        if distribution["arabic"] > threshold:
            continue
        findings.append(
            Finding(
                "link_text",
                "warn",
                f"link text left in the source language: [{text}]({url})",
            )
        )
    return findings


def check_brackets(target: str) -> List[Finding]:
    problems = balance_brackets(target)
    return [
        Finding("brackets", "error", problem) for problem in problems
    ]


def check_arabic_output(target: str, numerals: str = "preserve") -> List[Finding]:
    """Arabic-specific checks: punctuation, spacing, numerals, and MT tells."""
    findings: List[Finding] = []
    if not ARABIC_LETTER_RE.search(target):
        return findings
    for ascii_char, arabic_char in ((",", "،"), (";", "؛"), ("?", "؟")):
        if re.search(r"[\u0620-\u064A]\s*" + re.escape(ascii_char), target):
            findings.append(
                Finding(
                    "arabic_punctuation",
                    "warn",
                    f"ASCII {ascii_char!r} after Arabic letters; use {arabic_char!r}",
                )
            )
    if re.search(r"\s[،؛؟!.]", target):
        findings.append(
            Finding(
                "arabic_spacing",
                "warn",
                "space before punctuation; Arabic attaches punctuation to the word",
            )
        )
    for phrase, note in ARABIC_MT_SMELLS.items():
        if phrase.replace("...", "") in target and "..." not in phrase:
            findings.append(
                Finding("mt_smell", "info", f"phrase {phrase!r} — {note}")
            )
    if numerals == "western" and re.search(r"[\u0660-\u0669\u06F0-\u06F9]", target):
        findings.append(
            Finding(
                "numerals",
                "warn",
                "Arabic-Indic digits found but the requested script is western",
            )
        )
    if numerals == "arabic-indic" and re.search(r"(?<!`)\b\d{2,}\b(?!`)", target):
        findings.append(
            Finding(
                "numerals",
                "info",
                "western digits found; the requested script is Arabic-Indic "
                "(keep western digits inside code and URLs)",
            )
        )
    plain = strip_diacritics(target)
    if re.search(r"[\u0620-\u064A]\u0640", target):
        findings.append(Finding("tatweel", "info", "tatweel (ـ) found; avoid it in prose"))
    return findings


def check_terminology(target: str, glossary: Optional[Glossary]) -> List[Finding]:
    if glossary is None or not glossary.terms:
        return []
    findings: List[Finding] = []
    for term in glossary.terms:
        if not term.target or term.keep_as_is:
            continue
        forms = [term.source] + list(term.aliases)
        for form in forms:
            if len(form) < 3:
                continue
            pattern = re.compile(
                r"(?<![\w\u0620-\u064A])" + re.escape(form) + r"(?![\w\u0620-\u064A])"
            )
            match = pattern.search(target)
            if match:
                findings.append(
                    Finding(
                        "terminology",
                        "warn",
                        f"source form {form!r} survived translation; expected {term.target!r}",
                    )
                )
                break
        if term.target and term.target not in target and term.frequency >= 3:
            if any(form in target for form in forms):
                continue
            findings.append(
                Finding(
                    "terminology_absent",
                    "info",
                    f"high-frequency term {term.source!r} → {term.target!r} never appears; "
                    "check whether this chunk covers it",
                )
            )
    return findings


def check_headings(target: str, target_language: str) -> List[Finding]:
    findings: List[Finding] = []
    for match in HEADING.finditer(target):
        title = match.group(2).strip()
        if not title:
            findings.append(Finding("heading", "error", "empty heading"))
        if title.endswith((".", "،", "。")):
            findings.append(
                Finding("heading", "info", f"heading ends with punctuation: {title!r}")
            )
        if title.startswith("#"):
            findings.append(Finding("heading", "warn", f"malformed heading: {title!r}"))
    return findings


def check_whitespace(target: str) -> List[Finding]:
    findings: List[Finding] = []
    in_fence = False
    for position, line in enumerate(target.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        # Aligned code and table padding are intentional; only prose matters.
        if in_fence or stripped.startswith("|"):
            continue
        if DOUBLE_SPACE.search(line):
            findings.append(
                Finding("whitespace", "info", "repeated spaces", f"line {position}")
            )
            break
    if not target.endswith("\n"):
        findings.append(Finding("whitespace", "info", "file does not end with a newline"))
    if "\u00A0" in target:
        findings.append(Finding("whitespace", "info", "non-breaking spaces present"))
    return findings


def check_language_mix(target: str, target_language: str) -> List[Finding]:
    """Warn when a target is supposed to be Arabic but carries Latin prose."""
    if not target_language.startswith("ar"):
        return []
    distribution = script_distribution(target)
    if distribution["arabic"] < 0.3 and distribution["latin"] > 0.3:
        return [
            Finding(
                "language",
                "error",
                f"target is {int(distribution['latin'] * 100)}% Latin but the target "
                "language is Arabic",
            )
        ]
    latin_words = LATIN_WORD.findall(INLINE_CODE.sub("", target))
    if len(latin_words) > 40 and distribution["arabic"] < 0.5:
        return [
            Finding(
                "language",
                "warn",
                f"{len(latin_words)} Latin words outside code spans; confirm they are "
                "names or trademarks, not untranslated prose",
            )
        ]
    return []


# ---------------------------------------------------------------- gate


DEFAULT_CHECKS = (
    "length_ratio",
    "structure",
    "code_blocks",
    "inline_code",
    "links",
    "link_text",
    "numbers",
    "duplicate_paragraphs",
    "brackets",
    "untranslated",
    "language_mix",
    "arabic_output",
    "headings",
    "whitespace",
    "terminology",
)


def run_gate(
    source: str,
    target: str,
    source_language: str = "en",
    target_language: str = "ar",
    glossary: Optional[Glossary] = None,
    numerals: str = "preserve",
    checks: Sequence[str] = DEFAULT_CHECKS,
    max_errors: int = 0,
    max_warnings: int = 40,
) -> Dict[str, object]:
    """Run the selected checks and return a report dictionary."""
    findings: List[Finding] = []
    for name in checks:
        if name == "length_ratio":
            findings += check_length_ratio(source, target, source_language, target_language)
        elif name == "structure":
            findings += check_structure(source, target)
        elif name == "code_blocks":
            findings += check_code_blocks(source, target)
        elif name == "inline_code":
            findings += check_inline_code(source, target)
        elif name == "links":
            findings += check_links(source, target)
        elif name == "link_text":
            findings += check_link_text(source, target)
        elif name == "numbers":
            findings += check_numbers(source, target)
        elif name == "duplicate_paragraphs":
            findings += check_duplicate_paragraphs(target)
        elif name == "brackets":
            findings += check_brackets(target)
        elif name == "untranslated":
            findings += check_untranslated(source, target)
        elif name == "language_mix":
            findings += check_language_mix(target, target_language)
        elif name == "arabic_output":
            findings += check_arabic_output(target, numerals=numerals)
        elif name == "headings":
            findings += check_headings(target, target_language)
        elif name == "whitespace":
            findings += check_whitespace(target)
        elif name == "terminology":
            findings += check_terminology(target, glossary)
        else:
            findings.append(Finding("gate", "warn", f"unknown check {name!r}"))

    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.code))
    errors = sum(1 for item in findings if item.severity == "error")
    warnings = sum(1 for item in findings if item.severity == "warn")
    infos = sum(1 for item in findings if item.severity == "info")
    metrics = quality_metrics(source, target)
    return {
        "ok": errors <= max_errors and warnings <= max_warnings,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "findings": findings,
        "metrics": metrics,
        "structure": {
            "source": structure_fingerprint(source),
            "target": structure_fingerprint(target),
        },
    }


def render_report(report: Dict[str, object]) -> str:
    lines = []
    metrics = report["metrics"]
    lines.append(
        "words {source_words} → {target_words} (ratio {length_ratio})".format(**metrics)
    )
    lines.append(
        "sentences {source_sentences} → {target_sentences} (avg {source_avg_sentence} → {target_avg_sentence})".format(
            **metrics
        )
    )
    findings: List[Finding] = report["findings"]  # type: ignore[assignment]
    if not findings:
        lines.append("no findings")
    for finding in findings:
        lines.append(finding.render())
    lines.append(
        f"errors={report['errors']} warnings={report['warnings']} infos={report['infos']} "
        f"ok={str(report['ok']).lower()}"
    )
    return "\n".join(lines)
