# Change Manifest — 2026-08-04 — Home page video resolution picker

## Feature
On the Home page, selecting **Video** now reveals a resolution choice — **720p** or
**1080p** (default 1080p). **Audio** is unchanged and always downloads the highest
available quality. The picker is hidden unless Video is selected.

## Design
- `video_quality` ('720' | '1080') flows: `templates/index.html` (radio + JS) →
  `POST /api/download` → `start_download_thread` → `download_media`.
- Validation is defense-in-depth: whitelisted to {720, 1080} in `api.py` (bad/missing
  → 1080) and re-validated in `media.py`.
- yt-dlp format is capped by height with graceful fallbacks so a source lacking a
  stream at the cap still downloads:
  `bestvideo[ext=mp4][height<=N]+bestaudio[ext=m4a]/best[ext=mp4][height<=N]/best[height<=N]/best`
- Audio path untouched (`bestaudio` + MP3 postprocessor).

## Files Affected
- `templates/index.html` — added `#video-quality-options` radios (720/1080, default 1080);
  change handler to slide-toggle on Audio/Video; read `videoQuality`; added `video_quality`
  to the `/api/download` payload; added `input[name="video-quality"]` to the
  disable/enable-during-download selectors.
- `modules/routes/api.py` — read + whitelist `video_quality`; log it; pass to
  `start_download_thread`.
- `modules/download/media.py` — `download_media` and `start_download_thread` take
  `video_quality='1080'`; video branch builds a height-capped format string; logs the cap.

## Verification
- Import OK; signatures updated on both functions.
- `GET /` renders `#video-quality-options`, `#quality-720`, `#quality-1080`, `>720p<`, `>1080p<`.
- `POST /api/download {download_type:video, video_quality:720}` → HTTP 200, log shows
  `quality=720`. Format-string logic table-tested for 720/1080/invalid/None.
- Full network download not run (YouTube bot-gating in this environment) — format path
  exercised up to the yt-dlp call.

## Notes / Not Done
- **Repo only.** The menu-launched install (MensuraMedia tree) has a divergent download
  API (`enqueue_download`) and different templates; this feature was NOT ported there.
  See [[two-divergent-repos]].
- Playlist mode inherits the same cap (applies per entry) — no extra work needed.
