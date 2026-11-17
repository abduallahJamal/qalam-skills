"""Arabic-aware text primitives.

Everything here is deterministic and offline.  These helpers are what the skills
call when they need to *know* something about Arabic text (is it Arabic? is it
numerals? where does an RTL run start?) instead of guessing from the model.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Character classes
# ---------------------------------------------------------------------------

ARABIC_LETTER_RE = re.compile(r"[\u0620-\u064A\u066E-\u06D3\u06FA-\u06FF]")
ARABIC_PRESENTATION_RE = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")
ARABIC_TATWEEL = "\u0640"
ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

#: Arabic-Indic digits and Extended Arabic-Indic (Persian) digits.
ARABIC_INDIC_DIGITS = re.compile(r"[\u0660-\u0669]")
EXTENDED_ARABIC_INDIC_DIGITS = re.compile(r"[\u06F0-\u06F9]")

LTR = "L"
RTL = "R"
NEUTRAL = "N"


def to_digits(value: int, script: str = "western") -> str:
    """Render an integer using Western, Arabic-Indic, or Persian digits."""
    text = str(value)
    if script == "western":
        return text
    if script == "arabic-indic":
        return "".join(chr(0x0660 + int(d)) for d in text)
    if script == "extended-arabic-indic":
        return "".join(chr(0x06F0 + int(d)) for d in text)
    raise ValueError(f"unknown numeral script: {script}")


def normalise_digits(text: str) -> str:
    """Fold Arabic-Indic and Persian digits to ASCII so comparisons work."""
    out = []
    for char in text:
        if ARABIC_INDIC_DIGITS.match(char):
            out.append(chr(ord(char) - 0x0660 + ord("0")))
        elif EXTENDED_ARABIC_INDIC_DIGITS.match(char):
            out.append(chr(ord(char) - 0x06F0 + ord("0")))
        else:
            out.append(char)
    return "".join(out)


def strip_diacritics(text: str) -> str:
    """Remove harakat (tashkeel) and Quranic annotation signs."""
    return ARABIC_DIACRITICS.sub("", text)


def strip_tatweel(text: str) -> str:
    return text.replace(ARABIC_TATWEEL, "")


def strip_presentation_forms(text: str) -> str:
    """Convert Arabic presentation forms (U+FB50–U+FEFF) to their base letters."""
    return unicodedata.normalize("NFKC", text)


def normalise_arabic(text: str, keep_diacritics: bool = True) -> str:
    """Unicode-normalise Arabic for matching: NFKC, tatweel removed, alef folded.

    Diacritics are kept by default because they are meaningful for display, but
    matching (glossary lookups, QA diffing) should pass ``keep_diacritics=False``
    so that ``كتاب`` matches ``كِتَاب``.
    """
    text = strip_presentation_forms(text)
    text = strip_tatweel(text)
    if not keep_diacritics:
        text = strip_diacritics(text)
    text = re.sub(r"[\u0622\u0623\u0625\u0671]", "\u0627", text)  # alef forms
    text = text.replace("\u0649", "\u064A")  # alef maqsura -> yeh
    text = text.replace("\u0629", "\u0647") if not keep_diacritics else text
    text = normalise_digits(text)
    text = re.sub(r"[ \t\u00A0\u200B-\u200F]+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Direction detection
# ---------------------------------------------------------------------------

RTL_LANGUAGES = {
    "ar", "arc", "azb", "bal", "ckb", "dv", "fa", "glk", "he", "khw", "ks",
    "ku", "mzn", "nqo", "pnb", "prs", "ps", "sd", "skr", "syr", "ug", "ur",
    "yi",
}

#: Languages whose punctuation and quoting conventions differ from English.
LANGUAGE_NAMES = {
    "ar": ("Arabic", "العربية"),
    "en": ("English", "الإنجليزية"),
    "fr": ("French", "الفرنسية"),
    "de": ("German", "الألمانية"),
    "es": ("Spanish", "الإسبانية"),
    "it": ("Italian", "الإيطالية"),
    "pt": ("Portuguese", "البرتغالية"),
    "ru": ("Russian", "الروسية"),
    "tr": ("Turkish", "التركية"),
    "fa": ("Persian", "الفارسية"),
    "ur": ("Urdu", "الأردية"),
    "he": ("Hebrew", "العبرية"),
    "hi": ("Hindi", "الهندية"),
    "zh": ("Chinese", "الصينية"),
    "ja": ("Japanese", "اليابانية"),
    "ko": ("Korean", "الكورية"),
}


def language_is_rtl(language: str) -> bool:
    return (language or "").split("-")[0].lower() in RTL_LANGUAGES


def char_direction(char: str) -> str:
    """Return ``L``, ``R``, or ``N`` using the Unicode bidi category."""
    code = ord(char)
    # Arabic/Hebrew blocks are strong RTL regardless of the general category,
    # because the bidi algorithm assigns them R or AL.
    if (
        0x0590 <= code <= 0x05FF        # Hebrew
        or 0x0600 <= code <= 0x06FF     # Arabic
        or 0x0700 <= code <= 0x074F     # Syriac
        or 0x0750 <= code <= 0x077F     # Arabic Supplement
        or 0x0780 <= code <= 0x07BF     # Thaana
        or 0x08A0 <= code <= 0x08FF     # Arabic Extended-A
        or 0xFB50 <= code <= 0xFDFF     # Arabic Presentation Forms-A
        or 0xFE70 <= code <= 0xFEFF     # Arabic Presentation Forms-B
        or 0x10800 <= code <= 0x10FFF   # Ancient RTL scripts
    ):
        return RTL
    category = unicodedata.bidirectional(char)
    # Only strong types decide direction. ANSI/EN (digits) are weak types in
    # UAX#9, so a leading number must not flip an Arabic paragraph to LTR.
    if category in ("R", "AL"):
        return RTL
    if category == "L":
        return LTR
    return NEUTRAL


def estimate_direction(text: str) -> str:
    """Guess paragraph direction from the first strong character."""
    for char in text:
        direction = char_direction(char)
        if direction != NEUTRAL:
            return direction
    return NEUTRAL


def script_distribution(text: str) -> Dict[str, float]:
    """Return the share of Arabic, Latin, and digit characters in *text*."""
    counts = {"arabic": 0, "latin": 0, "digits": 0, "other": 0}
    for char in text:
        if ARABIC_LETTER_RE.match(char) or ARABIC_PRESENTATION_RE.match(char):
            counts["arabic"] += 1
        elif "a" <= char.lower() <= "z":
            counts["latin"] += 1
        elif char.isdigit() or ARABIC_INDIC_DIGITS.match(char):
            counts["digits"] += 1
        elif char.isspace():
            continue
        else:
            counts["other"] += 1
    total = sum(counts.values()) or 1
    return {key: value / total for key, value in counts.items()}


# ---------------------------------------------------------------------------
# Punctuation mirroring and bidi isolation
# ---------------------------------------------------------------------------

MIRROR_PAIRS = {
    "(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{",
    "<": ">", ">": "<", "\u00AB": "\u00BB", "\u00BB": "\u00AB",
    "\u2039": "\u203A", "\u203A": "\u2039",
}

#: Punctuation that should change shape, not just position, in Arabic prose.
ARABIC_PUNCTUATION = {
    ",": "\u060C",   # Arabic comma
    ";": "\u061B",   # Arabic semicolon
    "?": "\u061F",   # Arabic question mark
}

LRM = "\u200E"
RLM = "\u200F"
ALM = "\u061C"          # Arabic letter mark
LRI, RLI, FSI, PDI = "\u2066", "\u2067", "\u2068", "\u2069"


def isolate_rtl(text: str) -> str:
    """Wrap text in RTL isolates so it survives an LTR host sentence."""
    return f"{RLI}{text}{PDI}"


def isolate_ltr(text: str) -> str:
    return f"{LRI}{text}{PDI}"


def balance_brackets(text: str) -> List[str]:
    """Report unbalanced brackets, treating mirrored Arabic punctuation."""
    openers = {"(": ")", "[": "]", "{": "}", "\u00AB": "\u00BB", "\u2039": "\u203A"}
    closers = {value: key for key, value in openers.items()}
    stack: List[Tuple[str, int]] = []
    problems: List[str] = []
    for index, char in enumerate(text):
        if char in openers:
            stack.append((char, index))
        elif char in closers:
            if not stack:
                problems.append(f"unexpected closing {char!r} at offset {index}")
            else:
                opener, _pos = stack.pop()
                if openers[opener] != char:
                    problems.append(
                        f"closing {char!r} at offset {index} does not match {opener!r}"
                    )
    for char, index in stack:
        problems.append(f"unclosed {char!r} opened at offset {index}")
    return problems


def bracket_depth_series(text: str) -> List[int]:
    """Running bracket depth, used to check that a chunk ends where it starts."""
    openers = set("([{\u00AB\u2039")
    closers = set(")]}\u00BB\u203A")
    depth, series = 0, []
    for char in text:
        if char in openers:
            depth += 1
        elif char in closers:
            depth -= 1
        series.append(depth)
    return series


# ---------------------------------------------------------------------------
# Arabic-specific quality signals
# ---------------------------------------------------------------------------

#: Machine-translation tells that Qalam flags in Arabic output.
ARABIC_MT_SMELLS = {
    "من المهم أن نلاحظ": "تعبير ترجمة حرفية؛ يُفضَّل صياغة مباشرة",
    "لا شك أن": "حشو؛ يُحذف عادةً بلا خسارة",
    "في عالم اليوم": "كليشيه ترجمة؛ استبدله بزمن محدد أو احذفه",
    "يُعتبر ... من": "بنية إنجليزية (is considered); أعد الصياغة",
    "من المثير للاهتمام": "ترجمة حرفية لـ it is interesting",
    "تجدر الإشارة إلى أن": "حشو إنجليزي (it is worth noting)",
    "على مدار": "تحقق: قد تكون ترجمة حرفية لـ across",
    "بشكل كبير": "قد تكون ترجمة حرفية لـ significantly",
    "بشكل عام": "مقبولة بحدود؛ لا تكرّرها كل فقرة",
}

#: Latin words that are acceptable to keep untranslated in Arabic technical text
#: when they are code identifiers or established acronyms.
CODE_SPAN_RE = re.compile(r"`[^`]*`")

INLINE_CODE = re.compile(r"`[^`\n]+`")
FENCED_CODE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
LINK_TARGET = re.compile(r"\]\(([^)]+)\)")
HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
PROTECTED_SPANS = (FENCED_CODE, INLINE_CODE, LINK_TARGET, HTML_TAG)


def protected_spans(text: str) -> List[Tuple[int, int]]:
    """Offsets that a translator must copy verbatim: code, links, HTML tags."""
    spans: List[Tuple[int, int]] = []
    for pattern in PROTECTED_SPANS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))
    return sorted(spans)


def mask_protected(text: str, placeholder: str = "\uE000") -> Tuple[str, List[str]]:
    """Replace protected spans with placeholders and return them in order."""
    saved: List[str] = []
    output = []
    cursor = 0
    for start, end in protected_spans(text):
        if start < cursor:
            continue
        output.append(text[cursor:start])
        token = f"{placeholder}{len(saved)}{placeholder}"
        output.append(token)
        saved.append(text[start:end])
        cursor = end
    output.append(text[cursor:])
    return "".join(output), saved
