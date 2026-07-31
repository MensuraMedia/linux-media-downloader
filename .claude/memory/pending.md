# Pending / Unresolved Items

Opportunities identified during the 2026-07-31 review but intentionally **not** changed
(to keep the optimization pass low-risk). Revisit when scope allows:

- [ ] **cwd-relative paths** — `settings.py` builds `HISTORY_FILE`, `downloads/`, and
  `backups/` from `os.getcwd()`. Launching the app from a different directory splits state.
  Anchor these to a fixed app-data dir (e.g. `~/.local/share/linux-media-downloader`).
- [ ] **AppDir duplication** — the packaging staging tree is a committed copy of the whole
  app. Prefer copying from source at build time so it cannot drift. Currently synced by hand.
- [x] **Automated tests (tier 1)** — `tests/test_app.py` now covers `sanitize_filename`,
  the cancel wiring (incl. an end-to-end HTTP cancel), the progress hook, and the `/api/*`
  routes. 15 tests, offline. Still TODO: an integration smoke test that does one real
  yt-dlp download, and wiring `pytest` into the `test-agent` skill + CI.
- [ ] **Playlist-in-single URL parsing** in `media.py` (`get_video_info`) uses fragile
  string splitting on `list=`. Consider `urllib.parse` for robustness.
- [ ] **Blocking `time.sleep(1)`** in `app.py` before opening the window — could poll the
  server's readiness instead.
