"""Tests for text_format.strip_inline_markdown — the shared markdown normalizer
that keeps bullets/paragraphs clean across generation, publishing and preview."""
import time
import pytest

from text_format import strip_inline_markdown as s


@pytest.mark.parametrize("raw,expected", [
    ("**bold** text", "bold text"),
    ("__also bold__", "also bold"),
    ("some *italic* word", "some italic word"),
    ("a `code` token", "a code token"),
    ("### Key Highlights", "Key Highlights"),
    ("## Heading", "Heading"),
    ("A [link text](https://x.com) inline.", "A link text inline."),
    ("* **Feature**: value with *stars*", "* Feature: value with stars"),
])
def test_emphasis_and_headings_stripped(raw, expected):
    assert s(raw) == expected


@pytest.mark.parametrize("preserved", [
    "- Range is now 500 km",              # dash bullet marker survives
    "* plain bullet",                     # star bullet marker survives
    "![alt](https://img.com/a.jpg)",      # inline image survives
    "| a | b |",                          # table pipes survive
    "snake_case_variable stays",          # underscores in words survive
    "3*4 = 12 math stays",                # bare asterisks survive
    "1. first numbered item",             # numbered list survives
])
def test_structure_preserved(preserved):
    assert preserved in s(preserved)


@pytest.mark.parametrize("empty", ["", None, "   "])
def test_empty_and_none_are_safe(empty):
    # Must never raise and must return a string.
    out = s(empty)
    assert isinstance(out, str)


def test_idempotent():
    """Running twice equals running once — required because the normalizer is
    applied at multiple layers (generation + publisher + frontend)."""
    samples = [
        "**a** *b* `c` ### d [e](http://f) * **g**",
        "- bullet\n\nParagraph **with** bold.",
        "nested **outer *inner* outer**",
        "unbalanced **open only",
    ]
    for x in samples:
        once = s(x)
        assert s(once) == once


def test_no_catastrophic_backtracking():
    big = "*" * 5000 + "x"
    t0 = time.time()
    s(big)
    assert time.time() - t0 < 1.0
