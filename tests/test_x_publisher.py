"""Tests for x_publisher — caption building and the credential-guarded paths.
No network is touched: with no X creds the functions must no-op gracefully."""
import pytest

from x_publisher import build_caption, post_to_x, verify_x_connection


class TestBuildCaption:
    def test_within_tweet_limit(self):
        c = build_caption("Tata launches Nexon EV facelift with 500 km range", "New pack")
        assert len(c) <= 280

    def test_contains_hashtags(self):
        c = build_caption("EV news", "")
        assert "#" in c

    def test_long_title_truncated(self):
        c = build_caption("word " * 100, "")
        assert len(c) <= 280
        assert "…" in c


class TestGuardedPaths:
    def test_post_to_x_no_creds_skips(self, monkeypatch):
        for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"):
            monkeypatch.delenv(k, raising=False)
        res = post_to_x("hello", url="https://zapway.app/x")
        assert res["success"] is False
        assert res.get("skipped") is True

    def test_verify_no_creds_reports_disconnected(self, monkeypatch):
        for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"):
            monkeypatch.delenv(k, raising=False)
        res = verify_x_connection()
        assert res["connected"] is False
        assert "error" in res
