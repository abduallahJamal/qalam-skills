"""Qalam — a portable, Arabic-first skill pack for coding agents.

The package has no third-party dependencies and no network calls. Every
subcommand of :mod:`qalam.cli` is a thin wrapper around the modules exported
here, so the same behaviour is available from a skill, a script, or a test.
"""

from __future__ import annotations

from .arabic import (  # noqa: F401
    ARABIC_MT_SMELLS,
    LTR,
    NEUTRAL,
    RTL,
    balance_brackets,
    estimate_direction,
    language_is_rtl,
    normalise_arabic,
    normalise_digits,
    script_distribution,
    strip_diacritics,
    to_digits,
)
from .chunk import (  # noqa: F401
    Chunk,
    ChunkingError,
    check_chunks,
    merge_outputs,
    split_text,
    write_chunks,
)
from .glossary import Glossary, Term, apply_replacements, extract_terms  # noqa: F401
from .install import (  # noqa: F401
    TOOL_PATHS,
    Action,
    InstallError,
    discover_skills,
    doctor,
    install_many,
    install_skill,
    uninstall_skill,
    write_cursor_rule,
)
from .qa import Finding, render_report, run_gate  # noqa: F401
from .render import build_html, write_preview  # noqa: F401
from .runstate import Plan, RunState, certify, plan, chunk_terms_signature  # noqa: F401
from .scaffold import scaffold  # noqa: F401
from .skillmd import SkillDoc, SkillError, emit, load, parse_markdown  # noqa: F401
from .termbase import (  # noqa: F401
    ascii_safe,
    contains_arabic,
    prepare_console,
    propose_glossary,
    read_code_identifiers,
    read_markdown_sources,
    safe_print,
    shared_code_terms,
    suggest_for_code,
)
from .textutil import (  # noqa: F401
    detect_language,
    language_label,
    length_ratio_band,
    quality_metrics,
    structure_fingerprint,
)
from .tm import MemoryEntry, TranslationMemory  # noqa: F401

__version__ = "1.0.0"
__all__ = [
    "ARABIC_MT_SMELLS",
    "Action",
    "Chunk",
    "ChunkingError",
    "Finding",
    "Glossary",
    "InstallError",
    "LTR",
    "MemoryEntry",
    "NEUTRAL",
    "Plan",
    "RTL",
    "RunState",
    "SkillDoc",
    "SkillError",
    "TOOL_PATHS",
    "Term",
    "TranslationMemory",
    "apply_replacements",
    "ascii_safe",
    "balance_brackets",
    "build_html",
    "certify",
    "check_chunks",
    "chunk_terms_signature",
    "contains_arabic",
    "detect_language",
    "discover_skills",
    "doctor",
    "emit",
    "estimate_direction",
    "extract_terms",
    "install_many",
    "install_skill",
    "language_is_rtl",
    "language_label",
    "length_ratio_band",
    "load",
    "merge_outputs",
    "normalise_arabic",
    "normalise_digits",
    "parse_markdown",
    "plan",
    "prepare_console",
    "propose_glossary",
    "quality_metrics",
    "read_code_identifiers",
    "read_markdown_sources",
    "render_report",
    "run_gate",
    "safe_print",
    "scaffold",
    "script_distribution",
    "shared_code_terms",
    "split_text",
    "strip_diacritics",
    "structure_fingerprint",
    "suggest_for_code",
    "to_digits",
    "uninstall_skill",
    "write_chunks",
    "write_cursor_rule",
    "write_preview",
    "__version__",
]
