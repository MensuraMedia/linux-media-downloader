#!/usr/bin/env python3
# tests/test_app.py
# Offline unit + route tests for Linux Media Downloader.
# These require no network and must never trigger a real download.

import pytest
import yt_dlp

import modules.config.settings as settings
from modules.utils.file_utils import sanitize_filename
from modules.download.media import DownloadProgress
import browser_app  # provides a Flask app with both blueprints registered


# ── filename sanitization ────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("My Video.mp3", "My_Video.mp3"),
    ("a  b---c.mp4", "a_b_c.mp4"),
    ("  spaced  .m4a", "spaced.m4a"),
    ("weird:*?name<>.webm", "weirdname.webm"),
    ("__leading_trailing__.mp3", "leading_trailing.mp3"),
])
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_sanitize_preserves_extension():
    assert sanitize_filename("song.final.mp3").endswith(".mp3")


# ── cancellation wiring (the cross-module bug that was fixed) ─────────────────

def test_cancel_flag_single_source_of_truth():
    settings.reset_cancel()
    assert settings.is_cancel_requested() is False
    settings.request_cancel()
    # media.py imported the accessor, so it must observe the same state
    from modules.download import media
    assert media.is_cancel_requested() is True
    settings.reset_cancel()


def test_progress_hook_raises_when_cancelled():
    settings.reset_cancel()
    dp = DownloadProgress(total_files=1)
    settings.request_cancel()
    with pytest.raises(yt_dlp.utils.DownloadCancelled):
        dp.progress_hook({
            "status": "downloading",
            "filename": "file.part",
            "downloaded_bytes": 1,
            "total_bytes": 2,
        })
    settings.reset_cancel()


def test_progress_hook_finished_marks_completed():
    settings.reset_cancel()
    dp = DownloadProgress(total_files=1)
    dp.progress_hook({"status": "finished", "filename": "/tmp/song.mp3"})
    assert settings.current_download["status"] == "completed"
    assert settings.current_download["total_progress"] == 100


# ── secret key hygiene ───────────────────────────────────────────────────────

def test_secret_key_not_hardcoded_default():
    assert settings.SECRET_KEY != "ytmediabackup"
    assert len(settings.SECRET_KEY) >= 24


# ── API routes (Flask test client, offline) ──────────────────────────────────

@pytest.fixture
def client():
    browser_app.app.config["TESTING"] = True
    return browser_app.app.test_client()


def test_get_default_path(client):
    r = client.get("/api/get-default-path")
    assert r.status_code == 200
    assert "path" in r.get_json()


def test_check_url_requires_url(client):
    assert client.post("/api/check-url", json={}).get_json().get("error")


def test_download_requires_url(client):
    assert client.post("/api/download", json={}).get_json().get("error")


def test_download_status_ok(client):
    assert client.get("/api/download-status").status_code == 200


def test_cancel_download_sets_flag_through_http(client):
    """End-to-end proof of the fix: an HTTP cancel must be visible in settings."""
    settings.reset_cancel()
    r = client.post("/api/cancel-download", json={})
    assert r.get_json()["status"] == "cancelled"
    assert settings.is_cancel_requested() is True
    settings.reset_cancel()
