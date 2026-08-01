#!/usr/bin/env python3
# tests/test_app.py
# Offline unit + route tests for Linux Media Downloader.
# These require no network and must never trigger a real download.

import os

import pytest
import yt_dlp

import modules.config.settings as settings
from modules.utils.file_utils import sanitize_filename
from modules.download.media import DownloadProgress
from modules import playlists as pl
import browser_app  # provides a Flask app with both blueprints registered


def _make_playlist(tmp_path, folder, names):
    """Create a folder with media files; return its path."""
    d = tmp_path / folder
    d.mkdir()
    for n in names:
        (d / n).write_bytes(b"x")
    return str(d)


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


def test_cancel_download_sets_flag_through_http(tmp_path, monkeypatch, client):
    """End-to-end proof of the fix: an HTTP cancel must be visible in settings."""
    # Redirect history writes to a temp file so the test never touches repo data.
    monkeypatch.setattr(settings, "HISTORY_FILE", str(tmp_path / "history.json"))
    settings.reset_cancel()
    r = client.post("/api/cancel-download", json={})
    assert r.get_json()["status"] == "cancelled"
    assert settings.is_cancel_requested() is True
    settings.reset_cancel()


# ── progress fallback ────────────────────────────────────────────────────────

def test_progress_hook_fragment_fallback():
    """When byte totals are absent, progress falls back to fragment counts."""
    settings.reset_cancel()
    dp = DownloadProgress(total_files=1)
    dp.progress_hook({
        "status": "downloading",
        "filename": "x.m4a",
        "downloaded_bytes": 0,
        "fragment_index": 3,
        "fragment_count": 12,
    })
    assert round(settings.current_download["progress"]) == 25
    settings.reset_cancel()


# ── links history ────────────────────────────────────────────────────────────

def test_add_and_update_link_history(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LINKS_HISTORY_FILE", str(tmp_path / "links.json"))
    settings.links_history.clear()
    entry = settings.add_link_history("https://youtu.be/abc", "audio", "single")
    assert entry["url"] == "https://youtu.be/abc"
    assert entry["status"] == "started"
    settings.update_last_link_history(title="My Song", status="completed")
    assert settings.links_history[-1]["title"] == "My Song"
    assert settings.links_history[-1]["status"] == "completed"
    settings.links_history.clear()


def test_links_history_api_newest_first(tmp_path, monkeypatch, client):
    monkeypatch.setattr(settings, "LINKS_HISTORY_FILE", str(tmp_path / "links.json"))
    settings.links_history.clear()
    settings.add_link_history("https://youtu.be/one", "audio", "single")
    settings.add_link_history("https://youtu.be/two", "video", "playlist")
    data = client.get("/api/links-history").get_json()
    assert [d["url"] for d in data] == ["https://youtu.be/two", "https://youtu.be/one"]
    assert client.post("/api/clear-links-history").get_json()["status"] == "cleared"
    assert client.get("/api/links-history").get_json() == []


def test_links_page_renders(client):
    r = client.get("/links")
    assert r.status_code == 200
    assert b"Links History" in r.data


# ── playlists manager ────────────────────────────────────────────────────────

@pytest.fixture
def pl_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "default_download_path", str(tmp_path))
    monkeypatch.setattr(settings, "download_history", [])
    return tmp_path


def test_list_playlists_only_multi_file(pl_root):
    _make_playlist(pl_root, "My Mix_playlist", ["a.mp3", "b.mp3"])
    _make_playlist(pl_root, "solo", ["only.mp3"])  # single file -> not a playlist
    names = [p["name"] for p in pl.list_playlists()]
    assert "My Mix_playlist" in names
    assert "solo" not in names


def test_rename_playlist(pl_root):
    p = _make_playlist(pl_root, "Old Name", ["a.mp3", "b.mp3"])
    res = pl.rename_playlist(p, "New Name")
    assert res["status"] == "success"
    assert os.path.isdir(str(pl_root / "New Name"))


def test_rename_rejects_outside_path(pl_root):
    # Path traversal guard: a path outside the download roots must be refused.
    assert pl.rename_playlist("/etc", "hacked")["status"] == "error"


def test_operation_replace_spaces(pl_root):
    p = _make_playlist(pl_root, "mix_playlist", ["a b c.mp3", "d e.mp3"])
    res = pl.apply_operation(p, "replace_spaces")
    assert res["status"] == "success" and res["renamed"] == 2
    assert sorted(os.listdir(p)) == ["a_b_c.mp3", "d_e.mp3"]


def test_operation_remove_special(pl_root):
    p = _make_playlist(pl_root, "mix_playlist", ["a*b?.mp3", "c!.mp3"])
    assert pl.apply_operation(p, "remove_special")["status"] == "success"
    assert sorted(os.listdir(p)) == ["ab.mp3", "c.mp3"]


def test_operation_number_prefix(pl_root):
    p = _make_playlist(pl_root, "mix_playlist", ["alpha.mp3", "beta.mp3"])
    assert pl.apply_operation(p, "number_prefix")["status"] == "success"
    assert sorted(os.listdir(p)) == ["01_alpha.mp3", "02_beta.mp3"]


def test_operation_delete_long(pl_root, monkeypatch):
    p = _make_playlist(pl_root, "mix_playlist", ["short.mp3", "long.mp3"])
    monkeypatch.setattr(pl, "_duration", lambda path: 500 if os.path.basename(path) == "long.mp3" else 100)
    res = pl.apply_operation(p, "delete_long")
    assert res["status"] == "success" and res["deleted"] == 1
    assert sorted(os.listdir(p)) == ["short.mp3"]


def test_playlists_api(pl_root, client):
    _make_playlist(pl_root, "api_mix_playlist", ["a.mp3", "b.mp3"])
    data = client.get("/api/playlists").get_json()
    assert any(p["name"] == "api_mix_playlist" for p in data)


def test_playlists_page_renders(client):
    r = client.get("/playlists")
    assert r.status_code == 200
    assert b"Playlists" in r.data


def test_scan_does_not_walk_into_parent(tmp_path, monkeypatch):
    # A single (non-playlist) history entry must NOT cause the parent dir to be
    # scanned, or the download root itself / sibling folders leak in as playlists.
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(settings, "default_download_path", str(root))
    # A playlist URL grabbed in single mode: is_playlist True, but output_dir is
    # the plain download root (not a *_playlist folder). Must not scan the parent.
    monkeypatch.setattr(settings, "download_history",
                        [{"output_dir": str(root), "is_playlist": True}])
    _make_playlist(root, "mix_playlist", ["a.mp3", "b.mp3"])
    _make_playlist(tmp_path, "other", ["c.mp3", "d.mp3"])  # sibling of root -> ignored
    names = [p["name"] for p in pl.list_playlists()]
    assert "mix_playlist" in names
    assert "other" not in names
