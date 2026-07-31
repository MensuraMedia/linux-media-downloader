# Project: Linux Media Downloader — CLAUDE.md (v2026.03)

## Overview
A localhost desktop application for downloading YouTube media (audio/video, single or
playlist) for personal, non-commercial use. A Flask backend serves a small web UI that is
rendered either in a native PyWebView window (`app.py`) or an ordinary browser
(`browser_app.py`). All downloading is delegated to `yt-dlp`.

## Architecture
- Language/Framework: Python 3.8+ / Flask (blueprints) + PyWebView (native shell)
- Build system: none (interpreted); optional AppImage packaging via `AppDir/`
- Key dependencies: `Flask`, `yt-dlp`, `pywebview` (see `requirements.txt`)
- Entry points:
  - `app.py` — native window (Flask on an ephemeral port + `webview`)
  - `browser_app.py` — browser fallback (Flask on `127.0.0.1:5000`)
- Modules:
  - `modules/config/settings.py` — config, shared mutable state, history persistence,
    cancellation helpers (`request_cancel` / `reset_cancel` / `is_cancel_requested`)
  - `modules/download/media.py` — `yt-dlp` orchestration, progress hook, worker thread
  - `modules/routes/api.py` — JSON API blueprint (`/api/*`)
  - `modules/routes/ui.py` — page-rendering blueprint (`/`, `/backups`, ...)
  - `modules/utils/file_utils.py` — filename sanitization, folder opening
- State model: download state lives in module-level singletons in `settings.py`
  (`current_download` dict, `download_history` list). Because these are **mutable and
  imported by reference**, cross-module mutation works. Scalar flags (e.g. the cancel
  flag) must be accessed through the helper functions, never imported by value.
- Persistence: `data/download_history.json` (last 100 entries).

## Build & Test Commands
```
# Install deps (into a venv)
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

# Run (native window)
python3 app.py

# Run (browser fallback -> http://127.0.0.1:5000)
python3 browser_app.py

# Syntax check (no test suite exists yet)
python3 -m py_compile app.py browser_app.py modules/**/*.py

# Lint (suggested; not yet configured)
python3 -m pyflakes .
```

## Project Conventions
- Modules are Flask blueprints registered in the entry-point files.
- Shared runtime state is centralized in `modules/config/settings.py`.
- **Never** import a scalar global (like `cancel_requested`) by value across modules —
  reassigning it in one module will not be seen by the others. Use accessor functions.
- User-facing status flows through the `current_download` dict consumed by
  `/api/download-status`.
- Keep the `AppDir/usr/bin/` staging copy in sync with the top-level sources when
  changing runtime code (it is what an AppImage build ships).

## Memory System
This project uses the universal memory management system.
- Session logs: `.claude/memory/sessions/`
- Change manifests: `.claude/memory/changes/`
- Decision log: `.claude/memory/decisions.md`
- Pending items: `.claude/memory/pending.md`
- Memory index: `.claude/memory/MEMORY.md`
- Local change log: `changelog.md` (git-independent, append-only)

## References
- @.claude/rules/ for memory, token-hygiene, and security rules
- @.claude/memory/decisions.md for architectural decisions
- README.md for user-facing feature documentation
