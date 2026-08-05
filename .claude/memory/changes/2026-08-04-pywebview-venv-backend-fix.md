# Change Manifest — 2026-08-04 — PyWebView venv backend fix + install hardening

## Summary
The app installed via `install.sh` showed a menu icon but no window on click. Root
cause: the installer's venv was created without `--system-site-packages`, so
PyWebView could not import the system GTK/WebKit2 backend (`gi`), and
`webview.start()` raised `WebViewException` and exited in <1s. Fixed the live
install, hardened the installer, added a DMABUF guard, and ported install infra
into this repo.

## Root Cause
- `venv/pyvenv.cfg` had `include-system-site-packages = false`.
- `PyGObject` (`python3-gi`) + WebKit2GTK are apt-only, not pip-installable into an
  isolated venv; the walled-off venv therefore had **no** GUI backend (GTK missing,
  Qt absent).
- Secondary: installed `app.py` lacked the `WEBKIT_DISABLE_DMABUF_RENDERER` guard.
- Enabler: `.desktop` uses `Terminal=false`, so the traceback was invisible.

## Files Affected
- `/home/user/.local/share/linux-media-downloader/venv/pyvenv.cfg` — flipped
  `include-system-site-packages` to `true` (live install repair).
- `/home/user/.local/share/linux-media-downloader/app.py` — added DMABUF guard.
- `/home/user/.local/share/linux-media-downloader/install.sh` — `--system-site-packages`
  + install-time backend import check.
- `install.sh` (repo, new) — ported hardened installer.
- `packaging/{build-deb.sh,install-menu.sh,linux-media-downloader.svg}` (repo, new).
- `INSTALL.md`, `docs/packaging.md`, `requirements-dev.txt` (repo, new).
- `docs/troubleshooting/2026-08-04-pywebview-blank-launch.md` (repo, new) — postmortem.
- `changelog.md`, `.claude/memory/decisions.md` — updated.

## Verification
- `venv/bin/python -c "import gi; gi.require_version('WebKit2','4.1'); from gi.repository import WebKit2"` → OK (was ModuleNotFoundError).
- `venv/bin/python app.py` with no env overrides → stays running in the event loop
  (killed by 10s timeout, exit 124) instead of crashing.
- Flask + yt-dlp still import inside the venv (system site-packages did not shadow them).

## Not Done (flagged for user decision)
- **Feature-module divergence not merged.** The MensuraMedia install tree carries
  `playlists.py`, `download/chapters.py`, `download/dedupe.py`,
  `config/user_settings.py` that this repo lacks; this repo carries
  `logging_config.py` + the DMABUF fix that the install lacks. Only install infra was
  ported — app logic was NOT merged (would need route/settings reconciliation).
- **Remote divergence.** Working repo origin = `mikesdatawork/...`; install origin =
  `MensuraMedia/...`. `install.sh` REPO_URL points at MensuraMedia. The canonical
  remote must be decided before publishing.
- **`tests/test_app.py` not ported** — it imports the un-merged feature modules.

## Related
- Builds on the 2026-06-03 DMABUF fix (`app.py`) — see decisions.md.
