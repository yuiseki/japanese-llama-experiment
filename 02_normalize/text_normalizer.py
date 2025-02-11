# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#
# Added some modification for Japanese text normalization.

import re
import unicodedata

#
# NOTE: 実際のところ, 01_normalize では PUNCT 変換は行わない.
# dedup 時には行う(PUNCT 除去)
# TODO: dedup 時, 日本語の場合は句読点を含んだままのほうが良いような気もするがどうか.
#

UNICODE_PUNCT = {
    # 日本語の場合は句読点は、。のままがよいでしょう
    "。": "。",
    "、": "、",
    "，": "、",

    "„": '"',
    "”": '"',
    "“": '"',
    "«": '"',
    "»": '"',
    "１": '"',
    "」": '"',
    "「": '"',
    "《": '"',
    "》": '"',
    "´": "'",
    "∶": ":",
    "：": ":",
    "？": "?",
    "！": "!",
    "（": "(",
    "）": ")",
    "；": ";",
    "–": "-",
    "—": " - ",
    "．": ". ",
    "～": "~",
    "’": "'",
    "…": "...",
    "━": "-",
    "〈": "<",
    "〉": ">",
    "【": "[",
    "】": "]",
    "％": "%",
    "►": "-",
}

UNICODE_PUNCT_RE = re.compile(f"[{''.join(UNICODE_PUNCT.keys())}]")


def replace_unicode_punct(text: str) -> str:
    return "".join((UNICODE_PUNCT.get(c, c) for c in text))


def remove_unicode_punct(text: str) -> str:
    """More aggressive version of replace_unicode_punct but also faster."""
    return UNICODE_PUNCT_RE.sub("", text)


# Reuse `strip_accents` for CJK text. Use NFKC
def strip_accents(line: str) -> str:
    """Strips accents from a piece of text."""
    #nfd = unicodedata.normalize("NFD", line)
    nkfc = unicodedata.normalize("NFKC", line)
    output = [c for c in nkfc if unicodedata.category(c) != "Mn"]
    if len(output) == line:
        return line
    return "".join(output)


# Build a regex matching all control characters.
# newline(LF, 10) has meaningful infor in CJK text, so do not remove it.
NON_PRINTING_CHARS_RE = re.compile(
    f"[{''.join(map(chr, list(range(0,10)) + list(range(11, 32)) + list(range(127,160))))}]"
)
DIGIT_RE = re.compile(r"\d")
PUNCT_OR_NON_PRINTING_CHARS_RE = re.compile(
    (UNICODE_PUNCT_RE.pattern + NON_PRINTING_CHARS_RE.pattern).replace("][", "")
)


def remove_non_printing_char(text: str) -> str:
    return NON_PRINTING_CHARS_RE.sub("", text)


def normalize_spacing_for_tok(text: str, language: str = "en") -> str:
    res = (
        text.replace("\r", "")
        # remove extra spaces
        .replace("(", " (")
        .replace(")", ") ")
        .replace(" +", " ")
    )
    res = re.sub(r"\) ([\.\!\:\?\;\,])", r"\)\1", res)
    res = res.replace("( ", "(").replace(" )", ")")
    res = re.sub(r"(\d) \%", r"\1\%", res)
    res = res.replace(" :", ":").replace(" ;", ";")
    res = res.replace("`", "'").replace("''", ' " ')

    res = (
        res.replace("„", '"')
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", " - ")
        .replace(" +", " ")
        .replace("´", "'")
        .replace("([a-z])‘([a-z])", r"\1'\2/")
        .replace("([a-z])’([a-z])", r"\1'\2/")
        .replace("‘", '"')
        .replace("‚", '"')
        .replace("’", '"')
        .replace("''", '"')
        .replace("´´", '"')
        .replace("…", "...")
        # French quotes
        .replace(" « ", ' "')
        .replace("« ", '"')
        .replace("«", '"')
        .replace(" » ", '" ')
        .replace(" »", '"')
        .replace("»", '"')
        # handle pseudo-spaces
        .replace(" %", "%")
        .replace("nº ", "nº ")
        .replace(" :", ":")
        .replace(" ºC", " ºC")
        .replace(" cm", " cm")
        .replace(" ?", "?")
        .replace(" !", "!")
        .replace(" ;", ";")
        .replace(", ", ", ")
        .replace(" +", " ")
        .replace("．", ". ")
    )
    # English "quotation," followed by comma, style
    if language == "en":
        res = re.sub(r"\"([,\.]+)", r"\1\"", res)
    # Czech is confused
    elif language == "cs" or language == "cz":
        pass
    # German/Spanish/French "quotation", followed by comma, style
    else:
        res = res.replace(',"', '",')
        res = re.sub(
            r"(\.+)\"(\s*[^<])", r"\"\1\2", res
        )  # don't fix period at end of sentence

    if (
        language == "de"
        or language == "es"
        or language == "cz"
        or language == "cs"
        or language == "fr"
    ):
        res = re.sub(r"(\d) (\d)", r"\1,\2", res)
    else:
        res = re.sub(r"(\d) (\d)", r"\1.\2", res)
    return res


# NOTE accent=True will do NFKC normalization
# NOTE: set punct=0(no zenkaku->hankaku conversion) hby default for Japanese dataset
def normalize(line: str, accent=True, case=False, numbers=False, punct=0) -> str:
    line = line.strip()
    if not line:
        return line
    if case:
        line = line.lower()

    # FIXME: Always apply NKFC normalization for CJK text.
    if accent:
        line = strip_accents(line)
    if numbers:
        line = DIGIT_RE.sub("0", line)
    if punct == 1:
        line = replace_unicode_punct(line)
    elif punct == 2:
        line = remove_unicode_punct(line)
    line = remove_non_printing_char(line)
    return line


def slow_normalize_for_dedup(line: str) -> str:
    return normalize(line, accent=False, case=True, numbers=True, punct=2)


def normalize_for_dedup(line: str) -> str:
    line = line.strip()
    if not line:
        return line
    # case
    line = line.lower()
    # numbers
    line = DIGIT_RE.sub("0", line)
    line = PUNCT_OR_NON_PRINTING_CHARS_RE.sub("", line)
    return line
