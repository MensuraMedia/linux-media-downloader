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
    # Isolate the per-playlist metadata stores so tests never touch repo data.
    monkeypatch.setattr(pl, "COLORS_FILE", str(tmp_path / "colors.json"))
    monkeypatch.setattr(pl, "SEQ_FILE", str(tmp_path / "seq.json"))
    pl._undo_stack.clear()
    pl._redo_stack.clear()
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


def test_operation_truncate(pl_root):
    long_name = "This Is A Really Long Track Title That Exceeds The Limit.mp3"
    p = _make_playlist(pl_root, "mix_playlist", [long_name, "short.mp3"])
    assert pl.apply_operation(p, "truncate")["status"] == "success"
    for f in os.listdir(p):
        assert len(os.path.splitext(f)[0]) <= 35


def test_operation_remove_filler(pl_root):
    p = _make_playlist(pl_root, "mix_playlist",
                       ["Artist - Song (Official Music Video) [4K HD].mp3", "keep.mp3"])
    pl.apply_operation(p, "remove_filler")
    assert "Artist Song.mp3" in os.listdir(p)


def test_rename_collision_gets_salt(pl_root):
    # Two names that truncate to the same value must both survive (one salted).
    p = _make_playlist(pl_root, "mix_playlist", ["A" * 40 + "1.mp3", "A" * 40 + "2.mp3"])
    assert pl.apply_operation(p, "truncate")["status"] == "success"
    assert len(os.listdir(p)) == 2


def test_operation_standard_font(pl_root):
    p = _make_playlist(pl_root, "mix_playlist", ["Café Münster.mp3", "b.mp3"])
    pl.apply_operation(p, "standard_font")
    assert "Cafe Munster.mp3" in os.listdir(p)


def test_operation_camel_case(pl_root):
    p = _make_playlist(pl_root, "mix_playlist", ["hello world.mp3", "keep me.mp3"])
    pl.apply_operation(p, "camel_case")
    assert "HelloWorld.mp3" in os.listdir(p)


def test_operation_delete_long(pl_root, monkeypatch):
    p = _make_playlist(pl_root, "mix_playlist", ["short.mp3", "long.mp3"])
    monkeypatch.setattr(pl, "_duration", lambda path: 500 if os.path.basename(path) == "long.mp3" else 100)
    res = pl.apply_operation(p, "delete_long")
    assert res["status"] == "success" and res["deleted"] == 1
    remaining = [f for f in os.listdir(p) if f != ".trash"]
    assert remaining == ["short.mp3"]
    # Undo restores the "deleted" file
    assert pl.undo_last()["status"] == "success"
    assert "long.mp3" in os.listdir(p)


def test_empty_trash(pl_root, monkeypatch):
    p = _make_playlist(pl_root, "mix_playlist", ["short.mp3", "long.mp3"])
    monkeypatch.setattr(pl, "_duration", lambda path: 500 if os.path.basename(path) == "long.mp3" else 100)
    pl.apply_operation(p, "delete_long")
    assert pl.trash_count(p) == 1
    res = pl.empty_trash(p)
    assert res["status"] == "success" and res["purged"] == 1
    assert pl.trash_count(p) == 0
    assert not os.path.isdir(os.path.join(p, ".trash"))


def test_remove_filler_camelcase(pl_root):
    p = _make_playlist(pl_root, "mix_playlist",
                       ["SongTitleOfficialVideo.mp3", "keep.mp3"])
    pl.apply_operation(p, "remove_filler")
    assert "SongTitle.mp3" in os.listdir(p)


def test_remove_filler_media_terms(pl_root):
    p = _make_playlist(pl_root, "mix_playlist",
                       ["MyShow_OST_Track01.mp3", "AnimeAMVScore.mp3"])
    pl.apply_operation(p, "remove_filler")
    got = os.listdir(p)
    assert "MyShow Track01.mp3" in got   # OST removed, unique part kept
    assert "Anime.mp3" in got            # AMV + Score removed from camelCase


def test_undo_redo_rename(pl_root):
    p = _make_playlist(pl_root, "mix_playlist", ["a b.mp3", "c d.mp3"])
    pl.apply_operation(p, "replace_spaces")
    assert sorted(f for f in os.listdir(p) if f.endswith(".mp3")) == ["a_b.mp3", "c_d.mp3"]
    assert pl.undo_last()["status"] == "success"
    assert sorted(f for f in os.listdir(p) if f.endswith(".mp3")) == ["a b.mp3", "c d.mp3"]
    assert pl.redo_last()["status"] == "success"
    assert sorted(f for f in os.listdir(p) if f.endswith(".mp3")) == ["a_b.mp3", "c_d.mp3"]


def test_playlists_api(pl_root, client):
    _make_playlist(pl_root, "api_mix_playlist", ["a.mp3", "b.mp3"])
    data = client.get("/api/playlists").get_json()
    assert any(p["name"] == "api_mix_playlist" for p in data)


def test_playlists_page_renders(client):
    r = client.get("/playlists")
    assert r.status_code == 200
    assert b"Playlists" in r.data


# ── player / media curation ──────────────────────────────────────────────────

def test_list_all_media(pl_root):
    _make_playlist(pl_root, "a_playlist", ["x.mp3", "y.mp3"])
    (pl_root / "single.mp3").write_bytes(b"z")
    names = [m["name"] for m in pl.list_all_media()]
    assert "x.mp3" in names and "single.mp3" in names


def test_delete_media_file(pl_root):
    p = _make_playlist(pl_root, "a_playlist", ["x.mp3", "y.mp3"])
    f = os.path.join(p, "x.mp3")
    assert pl.delete_media_file(f)["status"] == "success"
    assert not os.path.exists(f)
    assert os.path.isfile(os.path.join(p, ".trash", "x.mp3"))


def test_delete_media_rejects_outside(pl_root):
    assert pl.delete_media_file("/etc/hosts")["status"] == "error"


def test_add_to_folder_copies(pl_root):
    p = _make_playlist(pl_root, "a_playlist", ["x.mp3", "y.mp3"])
    f = os.path.join(p, "x.mp3")
    res = pl.add_to_folder(f, "My Curated")
    assert res["status"] == "success"
    assert os.path.isfile(os.path.join(str(pl_root), "My Curated", "x.mp3"))
    assert os.path.isfile(f)  # original kept (it's a copy)


def test_player_page_renders(client):
    r = client.get("/player")
    assert r.status_code == 200
    assert b"Player" in r.data


def test_serve_media_rejects_outside(client):
    assert client.get("/api/media?path=/etc/hosts").status_code == 404


def test_abbreviate_duplicates(pl_root):
    p = _make_playlist(pl_root, "mix_playlist",
                       ["Predator_Soundtrack_Track01.mp3",
                        "Predator_Soundtrack_Track02.mp3"])
    pl.apply_operation(p, "abbreviate_dupes")
    assert sorted(os.listdir(p)) == ["Pred_Soun_Track01.mp3", "Pred_Soun_Track02.mp3"]


def test_playlist_color_set_and_listed(pl_root, monkeypatch):
    monkeypatch.setattr(pl, "COLORS_FILE", str(pl_root / "colors.json"))
    p = _make_playlist(pl_root, "mix_playlist", ["a.mp3", "b.mp3"])
    assert pl.set_playlist_color(p, "#ff0000")["status"] == "success"
    entry = next(x for x in pl.list_playlists() if x["name"] == "mix_playlist")
    assert entry["color"] == "#ff0000"


def test_playlist_color_invalid_defaults(pl_root, monkeypatch):
    monkeypatch.setattr(pl, "COLORS_FILE", str(pl_root / "colors.json"))
    p = _make_playlist(pl_root, "mix_playlist", ["a.mp3", "b.mp3"])
    assert pl.set_playlist_color(p, "not-a-color")["color"] == "#0d6efd"


def test_list_playlists_sorted_newest_first(pl_root):
    import time
    old = _make_playlist(pl_root, "old_playlist", ["a.mp3", "b.mp3"])
    _make_playlist(pl_root, "new_playlist", ["a.mp3", "b.mp3"])
    os.utime(old, (time.time() - 10000, time.time() - 10000))
    names = [x["name"] for x in pl.list_playlists()]
    assert names.index("new_playlist") < names.index("old_playlist")


def test_sequence_fixed_and_descending(pl_root):
    import time
    a = _make_playlist(pl_root, "a_playlist", ["x.mp3", "y.mp3"])
    _make_playlist(pl_root, "b_playlist", ["x.mp3", "y.mp3"])
    os.utime(a, (time.time() - 100, time.time() - 100))  # a older, b newer
    lst = pl.list_playlists()
    seq = {p["name"]: p["seq"] for p in lst}
    assert lst[0]["name"] == "b_playlist"          # newest on top
    assert seq["b_playlist"] > seq["a_playlist"]   # newest has the higher number

    # Adding another playlist must NOT change existing (fixed) numbers.
    _make_playlist(pl_root, "c_playlist", ["x.mp3", "y.mp3"])
    lst2 = pl.list_playlists()
    seq2 = {p["name"]: p["seq"] for p in lst2}
    assert seq2["a_playlist"] == seq["a_playlist"]
    assert seq2["b_playlist"] == seq["b_playlist"]
    assert lst2[0]["name"] == "c_playlist"


def test_sequence_wraps_at_1000(pl_root):
    import time
    (pl_root / "seq.json").write_text('{"next": 999, "orders": {}}')
    a = _make_playlist(pl_root, "a_playlist", ["x.mp3", "y.mp3"])
    _make_playlist(pl_root, "b_playlist", ["x.mp3", "y.mp3"])
    os.utime(a, (time.time() - 100, time.time() - 100))  # a -> 999, b -> 1000
    seq = {p["name"]: p["seq"] for p in pl.list_playlists()}
    assert seq["a_playlist"] == 999
    assert seq["b_playlist"] == 0  # 1000 % 1000 wraps to 000


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
