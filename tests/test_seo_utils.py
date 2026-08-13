"""Tests for seo_engine deterministic text helpers."""
import pytest

from seo_engine import truncate_word_safe, clean_incomplete_ending


class TestTruncateWordSafe:
    def test_short_text_unchanged(self):
        assert truncate_word_safe("Short text.", 100) == "Short text."

    def test_truncates_at_sentence_boundary(self):
        text = "First sentence is here. Second sentence continues well beyond the limit."
        out = truncate_word_safe(text, 30)
        assert out == "First sentence is here."
        assert len(out) <= 30

    def test_empty_is_safe(self):
        assert truncate_word_safe("", 10) == ""


class TestCleanIncompleteEnding:
    @pytest.mark.parametrize("text,expected", [
        ("The EV market is growing to", "The EV market is growing"),
        # ALL trailing stopwords are stripped in a loop ("and" then "by").
        ("Range increased by and", "Range increased"),
        ("A complete sentence.", "A complete sentence."),
    ])
    def test_trailing_stopwords_removed(self, text, expected):
        assert clean_incomplete_ending(text) == expected

    def test_empty_is_safe(self):
        assert clean_incomplete_ending("") == ""
