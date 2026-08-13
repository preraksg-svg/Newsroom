"""Tests for zapway_publisher content formatting — the step that decides what
text/bullets get typed into the zapway.app form."""
import pytest

from zapway_publisher import extract_bullets_from_content, flatten_markdown_tables


class TestFlattenTables:
    def test_table_becomes_bullets(self):
        md = "| Feature | Nexon | Punch |\n| Battery | 45 kWh | 35 kWh |"
        out = flatten_markdown_tables(md)
        assert "|" not in out
        assert "Battery" in out
        assert out.strip().startswith("*")

    def test_non_table_text_untouched(self):
        text = "Just a normal paragraph with no pipes."
        assert flatten_markdown_tables(text) == text


class TestExtractBullets:
    def test_bullets_extracted_and_emphasis_stripped(self):
        content = "Intro paragraph.\n* **Range**: 500 km\n- Fast charging in *30 min*"
        body, bullets = extract_bullets_from_content(content)
        assert "Range: 500 km" in bullets            # ** stripped
        assert "Fast charging in 30 min" in bullets   # * stripped
        assert "Intro paragraph." in body
        # No stray markdown asterisks leak into the body.
        assert "**" not in body

    def test_long_starred_line_stays_a_paragraph(self):
        long_line = "* " + ("word " * 60).strip()   # > 200 chars, prefixed with '*'
        body, bullets = extract_bullets_from_content(long_line)
        assert bullets == []                          # not treated as a bullet
        assert "word word" in body

    def test_plain_paragraph_has_no_bullets(self):
        body, bullets = extract_bullets_from_content("A single ordinary sentence.")
        assert bullets == []
        assert "ordinary" in body

    def test_empty_content(self):
        body, bullets = extract_bullets_from_content("")
        assert body == "" and bullets == []
