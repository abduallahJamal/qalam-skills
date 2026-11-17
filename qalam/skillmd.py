"""Parse, validate, and emit portable ``SKILL.md`` files.

The canonical source of a Qalam skill is a single ``SKILL.md`` whose frontmatter
uses only the fields of the open Agent Skills specification.  That is what makes
the same folder load in Claude Code, Codex CLI, Cursor, and OpenCode without a
translation layer.  Tool-specific behaviour (installation path, invocation
syntax) is handled by :mod:`qalam.install`, never by the skill file itself.

Only the Python standard library is used, so the package runs on a bare
interpreter with no virtualenv.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500

#: Frontmatter keys defined by the Agent Skills specification.
SPEC_FIELDS = ("name", "description", "license", "compatibility", "metadata")

#: Keys that some hosts accept and others ignore.  They are allowed, but
#: ``qalam skill check --strict`` warns when a skill depends on them.
HOST_FIELDS = (
    "allowed-tools",
    "disallowed-tools",
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "paths",
    "hooks",
    "shell",
)


class SkillError(ValueError):
    """Raised when a SKILL.md cannot be parsed or fails validation."""


@dataclass
class SkillDoc:
    """A parsed SKILL.md."""

    frontmatter: Dict[str, Any]
    body: str
    path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return str(self.frontmatter.get("name") or "")

    @property
    def description(self) -> str:
        return str(self.frontmatter.get("description") or "")

    # -- validation ---------------------------------------------------------
    def checks(self, strict: bool = False) -> List[Tuple[str, str]]:
        """Return ``(level, message)`` pairs; level is ``error`` or ``warn``."""
        found: List[Tuple[str, str]] = []
        fm = self.frontmatter

        name = self.name
        if not name:
            found.append(("error", "frontmatter is missing a `name`"))
        elif not NAME_RE.match(name):
            found.append(
                (
                    "error",
                    "`name` must be lowercase words joined by single hyphens "
                    f"(got {name!r}); OpenCode rejects other shapes",
                )
            )
        elif len(name) > MAX_NAME:
            found.append(("error", f"`name` is longer than {MAX_NAME} characters"))

        desc = self.description
        if not desc:
            found.append(
                (
                    "error",
                    "frontmatter is missing a `description`; hosts match user "
                    "requests against it, so the skill would never auto-load",
                )
            )
        elif len(desc) > MAX_DESCRIPTION:
            found.append(
                (
                    "error",
                    f"`description` is {len(desc)} characters; the spec caps it "
                    f"at {MAX_DESCRIPTION}. Move detail into the body.",
                )
            )
        elif len(desc) < 40:
            found.append(
                (
                    "warn",
                    "`description` is very short; it is the only text the host "
                    "sees before loading the skill, so add trigger words",
                )
            )
        if "\n" in desc.strip():
            found.append(
                (
                    "warn",
                    "`description` spans lines; most hosts list only the first "
                    "line, so keep it to a single sentence",
                )
            )

        compat = fm.get("compatibility")
        if compat is not None and len(str(compat)) > MAX_COMPATIBILITY:
            found.append(
                ("error", f"`compatibility` exceeds {MAX_COMPATIBILITY} characters")
            )

        meta = fm.get("metadata")
        if meta is not None:
            if not isinstance(meta, dict):
                found.append(("error", "`metadata` must be a mapping"))
            else:
                for key, value in meta.items():
                    if isinstance(value, (dict, list)):
                        found.append(
                            (
                                "error",
                                f"`metadata.{key}` must be a string; the spec "
                                "allows a flat string map only",
                            )
                        )

        for key in fm:
            if key not in SPEC_FIELDS and key not in HOST_FIELDS:
                found.append(("warn", f"unknown frontmatter field `{key}`"))

        if strict:
            for key in fm:
                if key in HOST_FIELDS:
                    found.append(
                        (
                            "warn",
                            f"`{key}` is a host-specific field; Cursor and "
                            "Codex ignore it",
                        )
                    )
            body = self.body
            if len(body.strip()) < 200:
                found.append(
                    (
                        "warn",
                        "body is under 200 characters; a skill that short is "
                        "usually better as a line in AGENTS.md",
                    )
                )

        return found

    def errors(self, strict: bool = False) -> List[str]:
        return [msg for level, msg in self.checks(strict) if level == "error"]

    def warning_messages(self, strict: bool = False) -> List[str]:
        return [msg for level, msg in self.checks(strict) if level == "warn"]

    def raise_if_invalid(self, strict: bool = False) -> None:
        problems = self.errors(strict)
        if problems:
            where = f" ({self.path})" if self.path else ""
            raise SkillError(
                "invalid SKILL.md" + where + ":\n  - " + "\n  - ".join(problems)
            )

    def to_markdown(self) -> str:
        """Serialise back to a portable SKILL.md string."""
        self.raise_if_invalid()
        lines = ["---", f"name: {self.name}", f"description: {_one_line(self.description)}"]
        if self.frontmatter.get("license"):
            lines.append(f"license: {self.frontmatter['license']}")
        if self.frontmatter.get("compatibility"):
            lines.append(f"compatibility: {_one_line(str(self.frontmatter['compatibility']))}")
        meta = self.frontmatter.get("metadata") or {}
        if meta:
            lines.append("metadata:")
            for key in sorted(meta):
                lines.append(f'  {key}: "{meta[key]}"')
        tools = self.frontmatter.get("allowed-tools")
        if tools:
            if isinstance(tools, (list, tuple)):
                tools = ", ".join(str(t) for t in tools)
            lines.append(f"allowed-tools: {tools}")
        lines.append("---")
        body = self.body.strip("\n")
        return "\n".join(lines) + "\n\n" + body + "\n"


# ---------------------------------------------------------------------------
# A deliberately small YAML subset parser
# ---------------------------------------------------------------------------
# Skill frontmatter only needs mappings, lists, scalars, and block scalars.
# Implementing that subset keeps Qalam dependency-free; a full YAML library
# would add an install step for every user of every skill.


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value[0] == '"' and value.endswith('"') and len(value) > 1:
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    if value[0] == "'" and value.endswith("'") and len(value) > 1:
        return value[1:-1].replace("''", "'")
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_inline(inner)]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _split_inline(text: str) -> List[str]:
    parts, buffer, quote = [], "", ""
    for char in text:
        if quote:
            buffer += char
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
            buffer += char
        elif char == ",":
            parts.append(buffer)
            buffer = ""
        else:
            buffer += char
    if buffer.strip():
        parts.append(buffer)
    return [p.strip() for p in parts]


def _read_block_scalar(
    lines: List[str], start: int, indicator: str
) -> Tuple[str, int]:
    """Read a ``|`` or ``>`` block starting at *start*; return (text, next index)."""
    collected: List[str] = []
    index = start
    base_indent: Optional[int] = None
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            collected.append("")
            index += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if base_indent is None:
            base_indent = indent
        if indent < base_indent:
            break
        collected.append(raw[base_indent:])
        index += 1
    while collected and collected[-1] == "":
        collected.pop()
        trailing_blank = True
    folded = indicator.startswith(">")
    if folded:
        paragraphs, current = [], []
        for line in collected:
            if line.strip():
                current.append(line.strip())
            else:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                paragraphs.append("")
        if current:
            paragraphs.append(" ".join(current))
        text = "\n".join(paragraphs)
    else:
        text = "\n".join(collected)
    if indicator.endswith("-"):
        text = text.rstrip("\n")
    return text, index


def _tokenize(lines: List[str]) -> List[Tuple[int, str, int]]:
    tokens: List[Tuple[int, str, int]] = []
    for index, raw in enumerate(lines):
        if not raw.strip():
            continue
        stripped = raw.lstrip(" ")
        if stripped.startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(stripped) + 1]:
            raise SkillError(
                f"line {index + 1}: indentation must use spaces, not tabs"
            )
        tokens.append((len(raw) - len(stripped), stripped.rstrip(), index))
    return tokens


def _parse_map(
    tokens: List[Tuple[int, str, int]], pos: int, indent: int, lines: List[str]
) -> Tuple[Dict[str, Any], int]:
    result: Dict[str, Any] = {}
    while pos < len(tokens):
        cur_indent, content, line_no = tokens[pos]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise SkillError(f"line {line_no + 1}: unexpected indentation")
        key, sep, rest = content.partition(":")
        if not sep:
            raise SkillError(f"line {line_no + 1}: expected `key: value`")
        key = key.strip()
        if not key:
            raise SkillError(f"line {line_no + 1}: empty key")
        rest = rest.strip()
        if rest[:1] in ("|", ">"):
            text, pos = _read_block_scalar(lines, line_no + 1, rest)
            result[key] = text
            continue
        pos += 1
        if rest == "":
            if pos < len(tokens) and tokens[pos][0] > indent:
                child_indent = tokens[pos][0]
                if tokens[pos][1].startswith("- "):
                    value, pos = _parse_list(tokens, pos, child_indent)
                else:
                    value, pos = _parse_map(tokens, pos, child_indent, lines)
                result[key] = value
            else:
                result[key] = None
            continue
        result[key] = _parse_scalar(rest)
    return result, pos


def _parse_list(
    tokens: List[Tuple[int, str, int]], pos: int, indent: int
) -> Tuple[List[Any], int]:
    items: List[Any] = []
    while pos < len(tokens):
        cur_indent, content, line_no = tokens[pos]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise SkillError(f"line {line_no + 1}: unexpected indentation in list")
        if not content.startswith("- "):
            break
        items.append(_parse_scalar(content[2:]))
        pos += 1
    return items, pos


def parse_yaml(text: str) -> Dict[str, Any]:
    """Parse the YAML subset used by SKILL.md frontmatter."""
    lines = text.splitlines()
    tokens = _tokenize(lines)
    if not tokens:
        return {}
    if tokens[0][0] != 0:
        raise SkillError("frontmatter must start at column 0")
    result, _ = _parse_map(tokens, 0, 0, lines)
    return result


def parse_markdown(text: str, path: Optional[str] = None) -> SkillDoc:
    """Split a SKILL.md string into frontmatter and body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillError(
            "SKILL.md must start with a `---` frontmatter block on its first line "
            "(a byte-order mark or a blank line above it stops every host from "
            "loading the skill)"
        )
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            closing = index
            break
    if closing is None:
        raise SkillError("frontmatter block is never closed with `---`")
    frontmatter = parse_yaml("\n".join(lines[1:closing]))
    body = "\n".join(lines[closing + 1 :])
    return SkillDoc(frontmatter=frontmatter, body=body, path=path)


def load(path: str, strict: bool = False) -> SkillDoc:
    """Read and validate a SKILL.md from disk."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    doc = parse_markdown(text, path=path)
    doc.raise_if_invalid(strict=strict)
    return doc


def emit(doc: SkillDoc) -> str:
    return doc.to_markdown()


def description_for_index(description: str, limit: int = 160) -> str:
    """Shorten a description for listing tables without cutting mid-word."""
    text = _one_line(description)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def iter_skill_files(root: str) -> Iterable[str]:
    import os

    for directory, _dirs, files in os.walk(root):
        if "SKILL.md" in files:
            yield os.path.join(directory, "SKILL.md")
