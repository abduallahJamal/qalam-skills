"""Command line interface: ``python -m qalam <command>``.

The CLI is what the skills call. Keeping every deterministic step here (instead
of describing it in prose) is what makes the same skill behave identically in
Claude Code, Codex, Cursor, and OpenCode: the model decides *what* to do, the
tool decides *how* the numbers come out.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .arabic import language_is_rtl, normalise_arabic
from .chunk import ChunkingError, check_chunks, merge_outputs, split_text, write_chunks
from .glossary import Glossary, Term, apply_replacements, extract_terms
from .install import (
    TOOL_NOTES,
    TOOL_PATHS,
    InstallError,
    doctor,
    install_many,
    installed_skills,
    uninstall_skill,
    write_cursor_rule,
)
from .qa import DEFAULT_CHECKS, render_report, run_gate
from .render import write_preview
from .runstate import RunState, certify, plan as plan_run
from .scaffold import scaffold
from .skillmd import SkillError, iter_skill_files, load as load_skill
from .termbase import (
    prepare_console,
    propose_glossary,
    read_code_identifiers,
    read_markdown_sources,
    safe_print,
    shared_code_terms,
    suggest_for_code,
)
from .textutil import detect_language, language_label, length_ratio_band, quality_metrics
from .tm import MemoryEntry, TranslationMemory

DEFAULT_TOOLS = ("claude", "codex", "cursor", "opencode")


def _skills_root() -> Path:
    """The skills directory that ships next to this package."""
    return Path(__file__).resolve().parent.parent / "skills"


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")


def _json_print(payload: object) -> None:
    safe_print(json.dumps(payload, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- install


def cmd_install(args: argparse.Namespace) -> int:
    tools = args.tools or list(DEFAULT_TOOLS)
    actions = install_many(
        _skills_root(),
        tools,
        scope=args.scope,
        mode=args.mode,
        force=args.force,
        dry_run=args.dry_run,
        cursor_rule=args.cursor_rule,
    )
    for action in actions:
        safe_print(action.render())
    counts = {}
    for action in actions:
        counts[action.mode] = counts.get(action.mode, 0) + 1
    safe_print("")
    safe_print("summary: " + ", ".join(f"{mode}={count}" for mode, count in sorted(counts.items())))
    if counts.get("conflict"):
        safe_print("")
        safe_print("Some targets already existed. Re-run with --force to replace them;")
        safe_print("the previous folder is moved into .qalam-backups/, never deleted.")
        return 2
    safe_print("")
    for tool in tools:
        safe_print(f"note ({tool}): {TOOL_NOTES[tool]}")
    if args.dry_run:
        safe_print("dry run: nothing was written")
    else:
        safe_print("Restart the agent (or start a new session) so it re-reads skills.")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    names = args.skill or [path.name for path in sorted(_skills_root().glob("*/SKILL.md"))]
    names = [Path(name).parent.name if name.endswith("SKILL.md") else name for name in names]
    tools = args.tools or list(DEFAULT_TOOLS)
    for tool in tools:
        for action in uninstall_skill(names, tool, args.scope, dry_run=args.dry_run):
            safe_print(action.render())
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    rows = doctor(_skills_root())
    safe_print(f"{'tool':10} {'scope':8} status")
    safe_print("-" * 60)
    missing = 0
    for tool, scope, status in rows:
        safe_print(f"{tool:10} {scope:8} {status}")
        if status in ("not installed", "empty"):
            missing += 1
    safe_print("")
    safe_print(f"{len(TOOL_PATHS)} tools x 2 scopes checked; {missing} empty locations")
    if args.details:
        for tool in TOOL_PATHS:
            safe_print("")
            safe_print(f"[{tool}] {TOOL_NOTES[tool]}")
            for scope in ("user", "project"):
                found = installed_skills(tool, scope)
                listing = ", ".join(f"{name} ({kind})" for name, kind in found) or "—"
                safe_print(f"  {scope:8} {listing}")
    return 0


def cmd_rule(args: argparse.Namespace) -> int:
    path = write_cursor_rule(Path(args.project).resolve(), dry_run=args.dry_run)
    safe_print(("would write " if args.dry_run else "wrote ") + str(path))
    return 0


# ---------------------------------------------------------------- skills


def cmd_skill_check(args: argparse.Namespace) -> int:
    targets = args.paths or [str(_skills_root())]
    failures = 0
    for target in targets:
        path = Path(target)
        files = [str(path)] if path.is_file() else list(iter_skill_files(str(path)))
        if not files:
            safe_print(f"no SKILL.md under {target}")
            failures += 1
            continue
        for file in sorted(files):
            try:
                doc = load_skill(file, strict=args.strict)
            except SkillError as error:
                safe_print(f"FAIL  {file}")
                for line in str(error).splitlines():
                    safe_print("      " + line)
                failures += 1
                continue
            warnings = doc.warning_messages(strict=args.strict)
            status = "WARN" if warnings else "OK  "
            safe_print(f"{status}  {doc.name:22} {len(doc.body):6} chars  {file}")
            for warning in warnings:
                safe_print("      warn: " + warning)
    safe_print("")
    safe_print(f"{failures} file(s) failed validation")
    return 1 if failures else 0


def cmd_skill_scaffold(args: argparse.Namespace) -> int:
    try:
        result = scaffold(
            name=args.name,
            description=args.description,
            root=Path(args.root).resolve(),
            with_test=not args.no_test,
            force=args.force,
        )
    except (ValueError, FileExistsError) as error:
        safe_print(f"error: {error}")
        return 2
    safe_print(f"created {result.directory}")
    for file in result.files:
        safe_print("  " + str(file.relative_to(result.directory)))
    safe_print("")
    safe_print("next: fill in the procedure, then run `python -m qalam skill check`")
    return 0


# ---------------------------------------------------------------- glossary


def cmd_glossary_build(args: argparse.Namespace) -> int:
    sources = read_markdown_sources(args.paths)
    if not sources:
        safe_print("no readable Markdown sources")
        return 2
    if args.code:
        counters = [read_code_identifiers([path]) for path in args.paths]
        identifiers = shared_code_terms(counters, min_total=args.code_min_frequency)
    else:
        identifiers = []
    if args.from_glossary:
        glossary = Glossary.load(args.from_glossary)
        terms = extract_terms(sources.values(), min_frequency=args.min_frequency, limit=args.limit)
        glossary.merge(Glossary(terms))
    else:
        glossary = propose_glossary(
            sources, min_frequency=args.min_frequency, limit=args.limit
        )
    glossary.count_frequencies(list(sources.values()))
    for term in suggest_for_code(identifiers, glossary):
        glossary.terms.append(term)
    if args.out:
        glossary.save(args.out)
        safe_print(f"wrote {args.out} ({len(glossary.terms)} terms)")
        if args.print:
            safe_print("")
            safe_print(glossary.to_markdown_table())
        safe_print("")
        safe_print("Targets are empty on purpose: fill them in, then re-run with")
        safe_print("`--from-glossary` to keep your decisions while adding new terms.")
        return 0
    safe_print(glossary.to_markdown_table())
    return 0


def cmd_glossary_terms(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary)
    text = _read(args.chunk)
    terms = glossary.matching(text)
    top = sorted(glossary.terms, key=lambda term: -term.frequency)[: args.top_n]
    merged = {term.key(): term for term in terms}
    for term in top:
        merged.setdefault(term.key(), term)
    ordered = sorted(merged.values(), key=lambda term: (-term.frequency, term.source))
    table = glossary.to_markdown_table(ordered)
    if not table:
        return 0
    safe_print(table)
    return 0


def cmd_glossary_show(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary)
    if args.json:
        _json_print({"version": 1, "terms": [term.to_dict() for term in glossary.terms]})
        return 0
    stats = glossary.stats()
    safe_print(
        f"{stats['terms']} terms, {stats['untranslated']} without a target, "
        f"categories: {stats['categories']}"
    )
    safe_print("")
    safe_print(glossary.to_markdown_table())
    return 0


def cmd_glossary_audit(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary)
    problems: List[str] = []
    seen = {}
    for term in glossary.terms:
        if not term.source.strip():
            problems.append("term with an empty source")
            continue
        key = term.key()
        if key in seen:
            problems.append(f"duplicate source {term.source!r} (also {seen[key]!r})")
        seen[key] = term.source
        for alias in term.aliases:
            alias_key = normalise_arabic(alias, keep_diacritics=False).lower()
            if alias_key in seen and seen[alias_key] != term.source:
                problems.append(
                    f"alias {alias!r} also used as a source form of {seen[alias_key]!r}"
                )
            seen.setdefault(alias_key, term.source)
        if not term.target and not term.keep_as_is:
            problems.append(f"{term.source!r} has no target (frequency {term.frequency})")
        if term.keep_as_is and term.target and term.target != term.source:
            problems.append(
                f"{term.source!r} is marked keep_as_is but has a different target; "
                "pick one"
            )
    safe_print("\n".join(problems) if problems else "glossary is consistent")
    return 1 if problems else 0


def cmd_glossary_apply(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary)
    text = _read(args.text)
    output, problems = apply_replacements(text, glossary)
    if args.out:
        _write(args.out, output)
        safe_print(f"wrote {args.out}")
    for problem in problems:
        safe_print("warn  " + problem)
    return 1 if problems and args.strict else 0


# ---------------------------------------------------------------- pipeline


def cmd_chunk(args: argparse.Namespace) -> int:
    text = _read(args.file)
    try:
        chunks = write_chunks(
            text,
            args.out_dir,
            target_chars=args.target_chars,
            max_chars=args.max_chars,
        )
    except ChunkingError as error:
        safe_print(f"error: {error}")
        return 2
    for chunk in chunks:
        safe_print(chunk.summary())
    problems = check_chunks(chunks, args.max_chars)
    safe_print("")
    safe_print(f"{len(chunks)} chunks written to {args.out_dir}")
    for problem in problems:
        safe_print("warn  " + problem)
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    try:
        count, warnings = merge_outputs(args.source_dir, args.translated_dir, args.out)
    except ChunkingError as error:
        safe_print(f"error: {error}")
        return 2
    safe_print(f"merged {count} chunk(s) into {args.out}")
    for warning in warnings:
        safe_print("warn  " + warning)
    return 1 if warnings and args.strict else 0


def cmd_plan(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary) if args.glossary else None
    result = plan_run(
        args.directory,
        glossary=glossary,
        target_language=args.target_language,
        retranslate_untracked=args.retranslate_untracked,
    )
    if args.json:
        _json_print(result.to_dict())
    else:
        safe_print(f"translate:    {len(result.translate):4}  {' '.join(result.translate[:12])}")
        safe_print(f"record only:  {len(result.record_only):4}  {' '.join(result.record_only[:12])}")
        safe_print(f"unchanged:    {len(result.unchanged):4}")
        if result.reasons:
            safe_print("")
            for chunk_id, reason in sorted(result.reasons.items())[:20]:
                safe_print(f"  {chunk_id}: {reason}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary) if args.glossary else None
    state = RunState.load(args.directory)
    recorded = 0
    for chunk_id in args.chunks:
        source_path = os.path.join(args.directory, f"{chunk_id}.md")
        output_path = os.path.join(args.directory, f"output_{chunk_id}.md")
        if not os.path.exists(source_path):
            safe_print(f"warn  {chunk_id}: source file missing")
            continue
        if not os.path.exists(output_path):
            safe_print(f"warn  {chunk_id}: output file missing")
            continue
        try:
            state.record(
                chunk_id,
                _read(source_path),
                _read(output_path),
                glossary,
                args.target_language,
                status=args.status,
            )
        except ValueError as error:
            safe_print(f"warn  {error}")
            continue
        recorded += 1
    state.save(args.directory)
    safe_print(f"recorded {recorded} chunk(s) in {RunState.path_for(args.directory)}")
    return 0 if recorded else 1


def cmd_certify(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary) if args.glossary else None
    problems = certify(args.directory, glossary=glossary, target_language=args.target_language)
    for problem in problems:
        safe_print("warn  " + problem)
    safe_print(f"certified outputs in {args.directory}" if not problems else "")
    return 1 if problems else 0


def cmd_gate(args: argparse.Namespace) -> int:
    glossary = Glossary.load(args.glossary) if args.glossary else None
    source = _read(args.source)
    target = _read(args.target)
    checks = [name for name in DEFAULT_CHECKS if name not in (args.skip or [])]
    report = run_gate(
        source,
        target,
        source_language=args.source_language,
        target_language=args.target_language,
        glossary=glossary,
        numerals=args.numerals,
        checks=checks,
        max_errors=args.max_errors,
        max_warnings=args.max_warnings,
    )
    if args.json:
        payload = dict(report)
        payload["findings"] = [finding.__dict__ for finding in report["findings"]]
        _json_print(payload)
    else:
        safe_print(render_report(report))
    return 0 if report["ok"] else 1


def cmd_preview(args: argparse.Namespace) -> int:
    path = write_preview(
        args.markdown,
        args.out,
        title=args.title or os.path.splitext(os.path.basename(args.markdown))[0],
        target_language=args.target_language,
        source_language=args.source_language,
        body_font_px=args.font_size,
        line_height=args.line_height,
        align=args.align,
    )
    safe_print(f"wrote {path}")
    return 0


def cmd_lang(args: argparse.Namespace) -> int:
    text = _read(args.file)[: args.chars]
    info = detect_language(text)
    metrics = quality_metrics(text, text)
    info["words"] = metrics["source_words"]
    info["sentences"] = metrics["source_sentences"]
    info["rtl"] = language_is_rtl(str(info["guess"]))
    info["label"] = language_label(str(info["guess"]))
    _json_print(info)
    return 0


def cmd_tm(args: argparse.Namespace) -> int:
    memory = TranslationMemory.load(args.memory) if args.memory else TranslationMemory()
    if args.action == "learn":
        added = memory.learn_from_pair(
            args.source, args.target, args.source_language, args.target_language
        )
        if args.memory:
            memory.save(args.memory)
        safe_print(f"learned {added} pair(s); memory now holds {memory.stats()['entries']}")
        return 0
    if args.action == "lookup":
        text = _read(args.source)
        prefilled, leftovers, hits = memory.reuse(text, args.target_language)
        safe_print(f"reused {hits} sentence(s); {len(leftovers)} left to translate")
        if args.out:
            _write(args.out, prefilled)
            safe_print(f"wrote {args.out}")
        else:
            safe_print("")
            safe_print(prefilled)
        return 0
    safe_print("unknown action")
    return 2


def cmd_info(args: argparse.Namespace) -> int:
    skills = sorted(path.parent.name for path in _skills_root().glob("*/SKILL.md"))
    safe_print(f"qalam {__version__}")
    safe_print(f"skills root: {_skills_root()}")
    safe_print(f"skills ({len(skills)}): {', '.join(skills)}")
    safe_print("tools: " + ", ".join(
        f"{tool} ({TOOL_PATHS[tool]['user']})" for tool in TOOL_PATHS
    ))
    safe_print("")
    low, high = length_ratio_band("en", "ar")
    safe_print(f"en→ar expected length ratio: {low}–{high} words")
    return 0


# ---------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qalam",
        description="Arabic-first skill pack and translation toolkit for coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"qalam {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="install the skills into agent tools")
    install.add_argument("--tools", nargs="+", choices=sorted(TOOL_PATHS), default=None)
    install.add_argument("--scope", choices=["user", "project"], default="user")
    install.add_argument("--mode", choices=["link", "copy"], default="link")
    install.add_argument("--force", action="store_true", help="replace existing skills")
    install.add_argument("--dry-run", action="store_true")
    install.add_argument("--cursor-rule", action="store_true", help="also write .cursor/rules/qalam.mdc")
    install.set_defaults(func=cmd_install)

    uninstall = subparsers.add_parser("uninstall", help="remove installed skills")
    uninstall.add_argument("--tools", nargs="+", choices=sorted(TOOL_PATHS), default=None)
    uninstall.add_argument("--scope", choices=["user", "project"], default="user")
    uninstall.add_argument("--skill", nargs="+", default=None)
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.set_defaults(func=cmd_uninstall)

    doctor_parser = subparsers.add_parser("doctor", help="show where skills are installed")
    doctor_parser.add_argument("--details", action="store_true")
    doctor_parser.set_defaults(func=cmd_doctor)

    rule = subparsers.add_parser("rule", help="write the optional Cursor pointer rule")
    rule.add_argument("--project", default=".")
    rule.add_argument("--dry-run", action="store_true")
    rule.set_defaults(func=cmd_rule)

    skill = subparsers.add_parser("skill", help="validate or scaffold skills")
    skill_sub = skill.add_subparsers(dest="action", required=True)
    check = skill_sub.add_parser("check", help="validate SKILL.md files")
    check.add_argument("paths", nargs="*")
    check.add_argument("--strict", action="store_true")
    check.set_defaults(func=cmd_skill_check)
    new = skill_sub.add_parser("new", help="scaffold a new skill")
    new.add_argument("name")
    new.add_argument("description")
    new.add_argument("--root", default="skills")
    new.add_argument("--no-test", action="store_true")
    new.add_argument("--force", action="store_true")
    new.set_defaults(func=cmd_skill_scaffold)

    glossary = subparsers.add_parser("glossary", help="build and query a term base")
    glossary_sub = glossary.add_subparsers(dest="action", required=True)
    build = glossary_sub.add_parser("build", help="propose terms from documents")
    build.add_argument("paths", nargs="+")
    build.add_argument("--min-frequency", type=int, default=2)
    build.add_argument("--limit", type=int, default=200)
    build.add_argument("--out")
    build.add_argument("--from-glossary", help="merge new terms into an existing glossary")
    build.add_argument("--code", action="store_true", help="also keep code identifiers verbatim")
    build.add_argument("--code-min-frequency", type=int, default=3)
    build.add_argument("--print", action="store_true")
    build.set_defaults(func=cmd_glossary_build)
    terms = glossary_sub.add_parser("terms", help="terms relevant to one chunk")
    terms.add_argument("glossary")
    terms.add_argument("chunk")
    terms.add_argument("--top-n", type=int, default=20)
    terms.set_defaults(func=cmd_glossary_terms)
    show = glossary_sub.add_parser("show", help="print the glossary")
    show.add_argument("glossary")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_glossary_show)
    audit = glossary_sub.add_parser("audit", help="find contradictions")
    audit.add_argument("glossary")
    audit.set_defaults(func=cmd_glossary_audit)
    apply_parser = glossary_sub.add_parser("apply", help="report or rewrite stale term forms")
    apply_parser.add_argument("glossary")
    apply_parser.add_argument("text")
    apply_parser.add_argument("--out")
    apply_parser.add_argument("--strict", action="store_true")
    apply_parser.set_defaults(func=cmd_glossary_apply)

    chunk = subparsers.add_parser("chunk", help="split a Markdown file into chunks")
    chunk.add_argument("file")
    chunk.add_argument("--out-dir", required=True)
    chunk.add_argument("--target-chars", type=int, default=6000)
    chunk.add_argument("--max-chars", type=int, default=12000)
    chunk.set_defaults(func=cmd_chunk)

    merge = subparsers.add_parser("merge", help="join translated chunks")
    merge.add_argument("--source-dir", required=True)
    merge.add_argument("--translated-dir", required=True)
    merge.add_argument("--out", required=True)
    merge.add_argument("--strict", action="store_true")
    merge.set_defaults(func=cmd_merge)

    plan_parser = subparsers.add_parser("plan", help="which chunks need translating again")
    plan_parser.add_argument("directory")
    plan_parser.add_argument("--glossary")
    plan_parser.add_argument("--target-language", default="")
    plan_parser.add_argument("--retranslate-untracked", action="store_true")
    plan_parser.add_argument("--json", action="store_true")
    plan_parser.set_defaults(func=cmd_plan)

    record = subparsers.add_parser("record", help="record finished chunks as done")
    record.add_argument("directory")
    record.add_argument("chunks", nargs="+")
    record.add_argument("--glossary")
    record.add_argument("--target-language", default="")
    record.add_argument("--status", default="translated",
                        choices=["translated", "review", "failed"])
    record.set_defaults(func=cmd_record)

    certify_parser = subparsers.add_parser("certify", help="record every valid existing output")
    certify_parser.add_argument("directory")
    certify_parser.add_argument("--glossary")
    certify_parser.add_argument("--target-language", default="")
    certify_parser.set_defaults(func=cmd_certify)

    gate = subparsers.add_parser("gate", help="quality gate for one translated file")
    gate.add_argument("--source", required=True)
    gate.add_argument("--target", required=True)
    gate.add_argument("--source-language", default="en")
    gate.add_argument("--target-language", default="ar")
    gate.add_argument("--glossary")
    gate.add_argument("--numerals", choices=["preserve", "western", "arabic-indic"], default="preserve")
    gate.add_argument("--skip", nargs="*", default=[])
    gate.add_argument("--max-errors", type=int, default=0)
    gate.add_argument("--max-warnings", type=int, default=40)
    gate.add_argument("--json", action="store_true")
    gate.set_defaults(func=cmd_gate)

    preview = subparsers.add_parser("preview", help="build a self-contained RTL HTML preview")
    preview.add_argument("markdown")
    preview.add_argument("--out", required=True)
    preview.add_argument("--title")
    preview.add_argument("--source-language", default="en")
    preview.add_argument("--target-language", default="ar")
    preview.add_argument("--font-size", type=int, default=19)
    preview.add_argument("--line-height", type=float, default=1.95)
    preview.add_argument("--align", choices=["justify", "start", "right", "left"], default=None)
    preview.set_defaults(func=cmd_preview)

    lang = subparsers.add_parser("lang", help="detect the language and direction of a file")
    lang.add_argument("file")
    lang.add_argument("--chars", type=int, default=4000)
    lang.set_defaults(func=cmd_lang)

    tm = subparsers.add_parser("tm", help="translation memory")
    tm.add_argument("action", choices=["learn", "lookup"])
    tm.add_argument("--memory")
    tm.add_argument("--source")
    tm.add_argument("--target")
    tm.add_argument("--source-language", default="en")
    tm.add_argument("--target-language", default="ar")
    tm.add_argument("--out")
    tm.set_defaults(func=cmd_tm)

    info = subparsers.add_parser("info", help="paths, skills, and defaults")
    info.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    prepare_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (InstallError, SkillError, ChunkingError, FileNotFoundError, ValueError) as error:
        safe_print(f"error: {error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
