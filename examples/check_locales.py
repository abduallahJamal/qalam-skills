#!/usr/bin/env python3
"""Compare a source locale file with a translation and report real defects.

This is the script the `localize-app` skill points at. It checks the things that
break applications, not the things that are merely different:

* key sets (missing and extra),
* placeholder sets per key (types and names, not positions),
* plural categories for Arabic (six, not two),
* empty values,
* leftover source text in values that should have been translated.

    python3 examples/check_locales.py examples/arabic-app/en.json examples/arabic-app/ar.json
"""

from __future__ import annotations

import json
import re
import sys
from typing import Dict, List

PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}|\{[A-Za-z_][A-Za-z0-9_]*\}|%\d*\$?[sd@]|%\([^)]+\)s")
ICU_PLURAL = re.compile(r"\{(\w+),\s*plural,\s*([^{}]*(?:\{[^}]*\}[^{}]*)*)\}")
CATEGORY = re.compile(r"\b(zero|one|two|few|many|other)\s*\{")
ARABIC = re.compile(r"[\u0620-\u064A]")
ARABIC_CATEGORIES = {"zero", "one", "two", "few", "many", "other"}


def placeholders(value: str) -> List[str]:
    return sorted(PLACEHOLDER.findall(value))


def plural_categories(value: str) -> List[str]:
    match = ICU_PLURAL.search(value)
    if not match:
        return []
    return sorted(set(CATEGORY.findall(match.group(2))))


def check(
    source: Dict[str, str],
    target: Dict[str, str],
    expect_arabic: bool = True,
    untouched: tuple = (),
) -> List[str]:
    problems: List[str] = []
    for key in source:
        if key not in target:
            problems.append(f"missing key: {key}")
    for key in target:
        if key not in source:
            problems.append(f"extra key: {key}")

    for key, source_value in source.items():
        if key not in target:
            continue
        target_value = target[key]
        if not str(target_value).strip():
            problems.append(f"empty value: {key}")
            continue

        source_slots = placeholders(str(source_value))
        target_slots = placeholders(str(target_value))
        if source_slots != target_slots:
            problems.append(
                f"placeholder mismatch: {key}: source {source_slots} target {target_slots}"
            )

        source_categories = plural_categories(str(source_value))
        target_categories = plural_categories(str(target_value))
        if source_categories and expect_arabic:
            missing = ARABIC_CATEGORIES - set(target_categories)
            if missing:
                problems.append(
                    f"incomplete Arabic plural: {key}: missing {sorted(missing)}"
                )

        # A value identical to the source is only a defect when the key was not
        # explicitly excluded. Product names ("Ledger") are legitimately
        # untouched and must not be reported as untranslated.
        if (
            expect_arabic
            and key not in untouched
            and str(source_value) == str(target_value)
            and not ARABIC.search(str(target_value))
        ):
            problems.append(f"not translated (identical to source): {key}: {target_value!r}")

    return problems


def main(argv: List[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        source = json.load(handle)
    with open(argv[2], encoding="utf-8") as handle:
        target = json.load(handle)
    # Usage: check_locales.py en.json ar.json [key.untouched ...]
    problems = check(source, target, untouched=tuple(argv[3:]))
    print(f"{len(source)} source keys, {len(target)} target keys")
    if not problems:
        print("no problems found")
        return 0
    for problem in problems:
        print("  " + problem)
    print(f"\n{len(problems)} problem(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
