#!/usr/bin/env python3
"""End-to-end demo of the Qalam pipeline on a small real document.

Runs, in order:

1. language detection on the source,
2. chunking with the real chunker,
3. glossary proposal and term injection per chunk,
4. a plan/record/plan cycle showing selective re-translation,
5. the quality gate on a good and a deliberately defective translation,
6. the RTL HTML preview.

Everything runs offline and writes only inside ``demo/work/``.

    python3 demo/run_demo.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qalam.chunk import merge_outputs, write_chunks
from qalam.glossary import Glossary
from qalam.qa import render_report, run_gate
from qalam.render import write_preview
from qalam.runstate import RunState, plan
from qalam.termbase import prepare_console, safe_print
from qalam.textutil import detect_language, length_ratio_band

DEMO = ROOT / "demo"
WORK = DEMO / "work"


def rule(title: str) -> None:
    safe_print("")
    safe_print("=" * 68)
    safe_print(title)
    safe_print("=" * 68)


def main() -> int:
    prepare_console()
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "ar").mkdir(parents=True)

    source_text = (DEMO / "source.en.md").read_text(encoding="utf-8")

    rule("1. Detect the source language")
    info = detect_language(source_text)
    safe_print(
        f"guess={info['guess']} confidence={info['confidence']} "
        f"direction={info['direction']}"
    )
    safe_print(f"script shares: {info['script']}")

    rule("2. Chunk the document")
    chunks = write_chunks(source_text, str(WORK / "ar"), target_chars=1200, max_chars=3000)
    for chunk in chunks:
        safe_print(chunk.summary())
    safe_print(f"manifest: {WORK / 'ar' / 'manifest.json'}")

    rule("3. Glossary: propose, then inject per chunk")
    glossary_path = DEMO / "glossary.json"
    glossary = Glossary.load(str(glossary_path))
    glossary.count_frequencies([source_text])
    safe_print(glossary.to_markdown_table())
    for chunk in chunks:
        terms = glossary.matching(chunk.text)
        names = ", ".join(term.source for term in terms) or "(none)"
        safe_print(f"  {chunk.id}: {names}")

    rule("4. Plan, record, and change one term to see selective re-translation")
    for chunk in chunks:
        (WORK / "ar" / f"output_{chunk.id}.md").write_text(
            f"نص تجريبي للفقرة {chunk.index}.\n", encoding="utf-8"
        )
    first = plan(str(WORK / "ar"), glossary=glossary, target_language="ar")
    safe_print(f"first plan: translate={len(first.translate)} record_only={len(first.record_only)} while={len(first.unchanged)}")
    state = RunState.load(str(WORK / "ar"))
    for chunk in chunks:
        # Record what is actually on disk, not the in-memory text: write_chunks
        # adds a trailing newline, and a hash of the pre-write string would never
        # match the file, leaving every chunk permanently "source_changed".
        state.record(
            chunk.id,
            (WORK / "ar" / f"{chunk.id}.md").read_text(encoding="utf-8"),
            (WORK / "ar" / f"output_{chunk.id}.md").read_text(encoding="utf-8"),
            glossary,
            "ar",
        )
    state.save(str(WORK / "ar"))
    second = plan(str(WORK / "ar"), glossary=glossary, target_language="ar")
    safe_print(f"after recording: translate={second.translate} unchanged={len(second.unchanged)}")

    # Change the target of one term and re-plan.
    for term in glossary.terms:
        if term.source == "parsed tree":
            term.target = "شجرة التحليل"
            break
    third = plan(str(WORK / "ar"), glossary=glossary, target_language="ar")
    safe_print(
        f"after editing one term: translate={third.translate} "
        f"reasons={third.reasons} unchanged={len(third.unchanged)}"
    )
    safe_print("Only chunks that contain the edited term were invalidated.")

    rule("5. Quality gate: a good translation and a defective one")
    # Reload: step 4 deliberately mutated one term to show invalidation, and that
    # change must not leak into the quality checks below.
    glossary = Glossary.load(str(glossary_path))
    glossary.count_frequencies([source_text])
    good = (DEMO / "good.ar.md").read_text(encoding="utf-8")
    bad = (DEMO / "bad.ar.md").read_text(encoding="utf-8")
    low, high = length_ratio_band("en", "ar")
    safe_print(f"expected en→ar word ratio: {low}–{high}")
    safe_print("")
    safe_print("--- good.ar.md ---")
    report = run_gate(source_text, good, glossary=glossary)
    safe_print(render_report(report))
    safe_print("")
    safe_print("--- bad.ar.md (deliberate defects) ---")
    report = run_gate(source_text, bad, glossary=glossary)
    safe_print(render_report(report))

    rule("6. Merge and render an RTL preview")
    merge_dir = WORK / "merge"
    merge_dir.mkdir()
    (merge_dir / "chunk0001.md").write_text(source_text, encoding="utf-8")
    (merge_dir / "output_chunk0001.md").write_text(good, encoding="utf-8")
    count, warnings = merge_outputs(str(merge_dir), str(merge_dir), str(WORK / "final.ar.md"))
    safe_print(f"merged {count} chunk(s), warnings={warnings or 'none'}")
    preview = write_preview(
        str(WORK / "final.ar.md"),
        str(WORK / "preview.ar.html"),
        title="استراتيجية التخزين المؤقت",
        source_language="en",
        target_language="ar",
    )
    safe_print(f"preview: {preview}")

    rule("Done")
    safe_print(f"All artefacts are under {WORK}")
    for path in sorted(WORK.rglob("*")):
        if path.is_file():
            safe_print(f"  {path.relative_to(WORK)}  ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
