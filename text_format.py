"""
Shared content-formatting normalizer for Zapway Newsroom.

The AI sometimes emits markdown emphasis (**bold**, *italic*, `code`), markdown
headings (## / ###) and inline links inside the article body. If these are left
in place they leak as literal asterisks / hashes into the ZAPWAY website and the
dashboard preview, and they confuse the bullet-extraction step (a real paragraph
can get pushed into a tiny bullet field, or a real bullet shows a stray '*').

`strip_inline_markdown` removes that inline syntax while deliberately PRESERVING:
  - bullet markers at the start of a line ("* item", "- item", "1. item")
  - inline images ![alt](url)
  - markdown table pipes ("| a | b |")

Applying this in ONE place (generation) plus defensively in the publisher and
the frontend keeps every surface consistent.
"""
import re

# **bold** and __bold__
_BOLD_STAR = re.compile(r"\*\*(.+?)\*\*")
_BOLD_UND = re.compile(r"__(.+?)__")
# `inline code`
_CODE = re.compile(r"`([^`]+)`")
# *italic* — a single '*' hugging text on both sides. The negative look-arounds
# ensure we never touch a bullet marker "* " (which has whitespace after the '*')
# nor a leftover '**'.
_ITAL_STAR = re.compile(r"(?<![\*\w])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\*\w])")
# _italic_ — same idea for underscores, without eating snake_case words.
_ITAL_UND = re.compile(r"(?<![_\w])_(?!\s)([^_\n]+?)(?<!\s)_(?![_\w])")
# [text](url) markdown link that is NOT an image (no leading '!'). Keep BOTH the
# text and the URL as "text (url)" so the link target is never silently lost.
# The URL group allows one level of balanced parens so Wikipedia-style targets
# like ".../Kanban_(development)" are captured whole, not truncated at the first ')'.
_LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\(((?:[^()]|\([^()]*\))+)\)")
# Leading heading hashes on a line: "### Title" -> "Title"
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")


def strip_inline_markdown(text: str) -> str:
    """Remove markdown emphasis/heading/link syntax, preserving bullets,
    inline images and table pipes. Safe to call repeatedly (idempotent)."""
    if not text:
        return text or ""
    text = _BOLD_STAR.sub(r"\1", text)
    text = _BOLD_UND.sub(r"\1", text)
    text = _CODE.sub(r"\1", text)
    text = _ITAL_STAR.sub(r"\1", text)
    text = _ITAL_UND.sub(r"\1", text)
    text = _LINK.sub(r"\1 (\2)", text)
    # Strip heading hashes line-by-line so the heading text survives as a plain line.
    lines = [_HEADING.sub("", ln) for ln in text.split("\n")]
    return "\n".join(lines)
