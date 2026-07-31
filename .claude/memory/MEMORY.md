# MEMORY.md — Project Memory Index
# Keep under 200 lines. One entry per line. Link to detail files.

## Session Logs
<!-- Add newest first -->
- [2026-07-31 onboarding + optimization](sessions/2026-07-31_onboarding-and-optimization.md) — Applied universal standards; fixed cancel bug, dead code, cleanup

## Changes
<!-- Add newest first -->
- [2026-07-31 cancel + cleanup](changes/2026-07-31_cancel-fix-and-cleanup.md) — Cross-module cancel fix, dead-code repair, unused imports, secret key, AppDir sync

## Decisions
- [Decision Log](decisions.md) — Architectural and design decisions

## Project Context
<!-- User info, project goals, references -->
- Onboarded from https://github.com/mikesdatawork/linux-media-downloader on 2026-07-31.
- Tech stack: Python / Flask (blueprints) + PyWebView + yt-dlp. Localhost-only desktop app.
- Two entry points: app.py (native window), browser_app.py (browser fallback).

## Feedback & Preferences
<!-- User corrections, confirmed approaches -->
- Alterations must follow the `-universal-*` instruction set (copy-and-adapt into `.claude/`).
