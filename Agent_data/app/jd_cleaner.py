"""
JD text cleaning helpers used by Python API and offline scripts.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from typing import Dict

from bs4 import BeautifulSoup


TRANSLATION_TABLE = str.maketrans(
    {
        "\u00A0": " ",
        "\u200B": "",
        "\u200C": "",
        "\u200D": "",
        "\uFEFF": "",
        "\u2018": "'",
        "\u2019": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\t": " ",
    }
)

_BULLET_PATTERN = re.compile(r"^\s*[•●◦▪▫■□◆◇▶▷►▸▹‣∙·・‧◉○*]\s*")
_DASH_BULLET_PATTERN = re.compile(r"^\s*[-–—]\s+")
_MULTI_SPACES = re.compile(r"[ \u00A0]{2,}")


def clean_jd_text(raw_text: str) -> str:
    """Normalize and clean JD text while preserving line breaks."""
    text = raw_text or ""
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(TRANSLATION_TABLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove HTML tags while preserving logical line breaks.
    text = BeautifulSoup(text, "html.parser").get_text(separator="\n")

    cleaned_lines = []
    for line in text.split("\n"):
        line = line.strip()
        line = _BULLET_PATTERN.sub("- ", line)
        line = _DASH_BULLET_PATTERN.sub("- ", line)
        line = _MULTI_SPACES.sub(" ", line)
        cleaned_lines.append(line)

    # Collapse consecutive blank lines but keep paragraph structure.
    compact_lines = []
    previous_blank = False
    for line in cleaned_lines:
        if line == "":
            if not previous_blank:
                compact_lines.append("")
            previous_blank = True
        else:
            compact_lines.append(line)
            previous_blank = False

    return "\n".join(compact_lines).strip()


def clean_document(job_id: str, raw_text: str, min_length: int) -> Dict[str, object]:
    """Return cleaned payload for one document with deletion decision."""
    cleaned = clean_jd_text(raw_text)
    cleaned_length = len(cleaned)
    delete_row = cleaned_length < min_length
    clean_hash = "" if delete_row else hashlib.md5(cleaned.encode("utf-8")).hexdigest()

    return {
        "job_id": job_id,
        "jd_clean_text": "" if delete_row else cleaned,
        "jd_clean_hash": clean_hash,
        "delete_row": delete_row,
        "cleaned_length": cleaned_length,
    }
