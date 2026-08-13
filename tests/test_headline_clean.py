"""Tests for backend.llm.clean_headline_garbage — strips publisher/domain
suffixes and dates from scraped headlines without harming real words."""
import pytest

from backend.llm import clean_headline_garbage as ch


@pytest.mark.parametrize("raw,expected", [
    ("Tata Nexon EV review - Autocar India", "Tata Nexon EV review"),
    ("EV sales up 20% | CleanTechnica", "EV sales up 20%"),
    ("Mahindra XUV400 first drive - carandbike.com", "Mahindra XUV400 first drive"),
    # Regression: source domain with NO space before the dash must still be stripped.
    ("After Mahindra, Lightrock in talks for investment in electric bus company- Moneycontrol.com",
     "After Mahindra, Lightrock in talks for investment in electric bus company"),
])
def test_suffixes_stripped(raw, expected):
    assert ch(raw) == expected


@pytest.mark.parametrize("keep", [
    "Ola e-scooter range test",          # hyphenated word must survive
    "BYD opens well-known gigafactory",  # hyphenated word must survive
    "Tata Nexon EV launched in India",   # nothing to strip
])
def test_real_words_preserved(keep):
    assert ch(keep) == keep


@pytest.mark.parametrize("empty", ["", None])
def test_empty_is_safe(empty):
    assert ch(empty) == empty
