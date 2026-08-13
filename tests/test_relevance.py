"""Tests for the deterministic India-EV relevance gates in backend.llm.
Only the OFFLINE paths are exercised (no Groq call)."""
import pytest

from backend.llm import is_ev_focused, is_two_wheeler_story, filter_article


class TestIsEvFocused:
    def test_ev_in_headline_is_true(self):
        assert is_ev_focused("Tata launches new electric SUV", "petrol prices rise") is True

    def test_single_passing_mention_is_false(self):
        # One stray "EV" mention in a non-EV body must not qualify.
        assert is_ev_focused("Auto news roundup", "The market grew. One EV was shown.") is False

    def test_multiple_body_signals_is_true(self):
        assert is_ev_focused(
            "Auto news",
            "electric vehicle battery charging ev ev electric",
        ) is True

    def test_empty_inputs_are_false(self):
        assert is_ev_focused("", "") is False


class TestIsTwoWheelerStory:
    def test_scooter_dominant_is_true(self):
        assert is_two_wheeler_story(
            "Ola launches new electric scooter",
            "The e-scooter and scooter and motorcycle segment expands",
        ) is True

    def test_car_and_infra_context_is_false(self):
        # A scooter mentioned alongside cars/charging/policy stays relevant.
        assert is_two_wheeler_story(
            "Tata Nexon EV charging network",
            "car charging policy sales market nexon scooter",
        ) is False

    def test_empty_is_false(self):
        assert is_two_wheeler_story("", "") is False


class TestFilterArticleOffline:
    def test_blacklisted_smartphone_rejected(self):
        res = filter_article("Best smartphone under 30000", "phone review")
        assert res["relevant"] is False
        assert "reason" in res

    def test_blacklisted_ipl_rejected(self):
        res = filter_article("Cricket match today", "IPL points table update")
        assert res["relevant"] is False

    def test_no_ev_terminology_rejected(self):
        # Passes the blacklist but has no EV term -> rejected before any LLM call.
        res = filter_article("City council approves new park", "Green spaces added downtown")
        assert res["relevant"] is False
        assert "No EV" in res["reason"] or "terminology" in res["reason"].lower()
