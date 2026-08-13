"""Tests for content_scoring — the deterministic quality gate that decides
APPROVE / IMPROVE / REJECT for a generated article."""
import pytest

from content_scoring import (
    compute_content_score,
    compute_headline_score,
    compute_readability,
)

RICH_HEADLINE = "Tata Nexon EV facelift launched in India with 500 km range at Rs 15 lakh"
RICH_BODY = (
    "Tata Motors has launched the 2026 Nexon EV facelift in India. The new model "
    "packs a 45 kWh battery delivering an ARAI-certified range of 500 km on a single "
    "charge. Prices start at Rs 15 lakh ex-showroom. Fast charging takes the pack from "
    "10 to 80 percent in 30 minutes using a 60 kW DC charger. Tata expects monthly "
    "sales of 5,000 units and has expanded its charging network to 4,500 points across "
    "120 cities. The company also confirmed a new LFP battery plant with 20 GWh capacity."
)
RICH_SECTIONS = [
    {"heading": "Battery and range", "content": "45 kWh pack, 500 km ARAI range, LFP chemistry."},
    {"heading": "Pricing", "content": "Starts at Rs 15 lakh, three trims up to Rs 19 lakh."},
    {"heading": "Charging", "content": "10-80% in 30 minutes on a 60 kW DC fast charger."},
]

VAGUE_HEADLINE = "Some news"
VAGUE_BODY = "A thing happened. It was reported. People talked about it. The end."


def test_return_shape():
    res = compute_content_score(RICH_HEADLINE, RICH_BODY, topic="EV", sections=RICH_SECTIONS)
    assert set(["content_score", "decision", "sub_scores"]).issubset(res.keys())
    assert 0 <= res["content_score"] <= 100
    assert res["decision"] in {"APPROVE", "IMPROVE", "REJECT"}


def test_rich_scores_higher_than_vague():
    rich = compute_content_score(RICH_HEADLINE, RICH_BODY, topic="EV", sections=RICH_SECTIONS)
    vague = compute_content_score(VAGUE_HEADLINE, VAGUE_BODY, topic="EV")
    assert rich["content_score"] > vague["content_score"]


def test_rich_article_not_rejected():
    rich = compute_content_score(RICH_HEADLINE, RICH_BODY, topic="EV", sections=RICH_SECTIONS)
    assert rich["decision"] != "REJECT"


def test_vague_article_rejected():
    vague = compute_content_score(VAGUE_HEADLINE, VAGUE_BODY, topic="EV")
    assert vague["decision"] == "REJECT"


def test_headline_score_clamped():
    for h in ["", "x", RICH_HEADLINE, "word " * 200]:
        s = compute_headline_score(h)["score"]
        assert 0 <= s <= 100


def test_readability_clamped():
    for c in ["", VAGUE_BODY, RICH_BODY]:
        s = compute_readability(c)["score"]
        assert 0 <= s <= 100
