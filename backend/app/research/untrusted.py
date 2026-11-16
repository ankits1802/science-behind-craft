from __future__ import annotations

import re

__all__ = ["UNTRUSTED_TAG", "clean_untrusted_text", "untrusted_block"]

UNTRUSTED_TAG = "untrusted_source"
INVISIBLE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f"
    r"\u200b\u200e\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\ufff9-\ufffb"
    r"\U000e0000-\U000e007f]"
)
SPACES = re.compile(r"[ \t\u00a0]+")
BLANK_LINES = re.compile(r"\n{3,}")
TAG_MENTION = re.compile(rf"<\s*/?\s*{UNTRUSTED_TAG}", re.IGNORECASE)
LABEL_UNSAFE = re.compile(r"[\"<>\n]")


def clean_untrusted_text(text: str) -> str:
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    visible = INVISIBLE.sub("", unified)
    lines = [SPACES.sub(" ", line).strip() for line in visible.split("\n")]
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def untrusted_block(ref: str, label: str, text: str) -> str:
    safe_ref = LABEL_UNSAFE.sub(" ", ref)
    safe_label = LABEL_UNSAFE.sub(" ", label)
    body = TAG_MENTION.sub(lambda match: match.group(0).replace("<", "("), clean_untrusted_text(text))
    return f'<{UNTRUSTED_TAG} ref="{safe_ref}" label="{safe_label}">\n{body}\n</{UNTRUSTED_TAG}>'
