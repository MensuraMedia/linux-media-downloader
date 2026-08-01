# Concept: Chapter / Tracklist Split

> **Status:** Concept / technical design — not yet implemented. Same spirit as the File
> Manager and Ignore-Duplicates specs. Fits the existing stack (yt-dlp + ffmpeg, both
> already present). See [DOCUMENTATION.md](../DOCUMENTATION.md) for the shipped app.

## 1. Purpose

Split a single long video (a compilation / "full album" / mix with a tracklist) into one
file per track. Boundaries come from the video's **chapters** or its **description
tracklist**; each output is named after its track. Output lands in a folder named after the
video, so it immediately reuses the **Playlists** and **File Manager** tooling.

## 2. The two approaches

**A. yt-dlp native split at download time** — `--split-chapters` (API: the `SplitChapters`
postprocessor) writes one file per chapter using `%(section_title)s` / `%(section_number)s`
output templates. Only fires when the video has **real embedded chapters**
(`info_dict['chapters']`). YouTube auto-promotes a description to real chapters when it has a
`0:00` start plus ≥3 timestamps; otherwise the description tracklist is *not* seen as
chapters and A produces nothing.

**B. Full download, then ffmpeg post-hoc split** — download once, then cut segments:
```
ffmpeg -ss 0:00 -to 4:11 -i full.mp3 -c copy "01 - Everybody Wants To Rule The World.mp3"
```
`-c copy` = stream copy, no re-encode → fast. Start/end come from consecutive timestamps
(last track runs to end-of-file). Works even with **no embedded chapters** — you only need
the timestamp list, which is already in `info_dict['description']`.

## 3. Analysis — which is best?

| Dimension | A (yt-dlp `--split-chapters`) | B (download + ffmpeg `-c copy`) |
|-----------|-------------------------------|----------------------------------|
| **Network** | 1 download | 1 download (identical) |
| **Split speed** | In-process, `-c copy` per chapter | N `ffmpeg -c copy` spawns; also near-instant (I/O bound) |
| **CPU** | Minimal (copy) | Minimal (copy); tiny per-process overhead |
| **Robustness** | ❌ Only when real chapters exist | ✅ Works for embedded **and** description-only tracklists |
| **Naming control** | Template only (`%(section_number)02d`, `%(title)s`) | ✅ Full: real title, or fallback, or `NN_` prefix |
| **Unlabeled fallback** | Possible via template defaults, but clumsy | ✅ Trivial in code |
| **Precision** | keyframe (`-c copy`) | keyframe (`-c copy`) or exact (`-c:a libmp3lame`) |
| **Code complexity** | Low | Moderate (parser + orchestration) |
| **Reuses app helpers** | Limited | ✅ `sanitize_filename`, `number_prefix`, folder→playlist |

### Recommendation

**Adopt Approach B (single download + `ffmpeg -c copy` post-hoc) as the engine, fed by the
best available chapter source**, i.e. a *hybrid* on the *source* but a single *splitter*:

1. If `info_dict['chapters']` is present → use those `(start, end, title)` triples.
2. Else parse the **description tracklist** into `(start, title)` and derive ends.
3. Split all segments with one uniform ffmpeg path.

**Why B over A:**
- **Robustness is decisive.** The common real-world case is a description tracklist that
  YouTube did *not* promote to chapters — A silently produces nothing there; B handles it.
- **Speed is effectively equal.** Both download once and both cut with `-c copy` (I/O-bound,
  near-instant). The extra process spawns in B are negligible next to download time.
- **Naming control is required** by this app: real titles when present, and the specified
  fallback (§5) when not — plus reuse of `sanitize_filename` / `number_prefix` and automatic
  Playlists/File-Manager integration via a video-named folder.

Approach A remains a valid *fast path* when real chapters exist and default naming is
acceptable; but standardizing on B keeps **one** code path that covers every case and
satisfies the naming rules, so B is the recommendation.

## 4. Chapter source detection & parsing

```
chapters = info_dict.get('chapters')          # [{start_time, end_time, title}, ...]
if not chapters:
    chapters = parse_description(info_dict.get('description', ''), duration)
```

Description parser — tolerant of common formats (`-`, `–`, `|`, `Artist – Title`, leading
track numbers, optional hours):
```
^\s*\d*[\.\)]?\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–|:]?\s*(.*)$
```
- Convert `h:mm:ss` / `m:ss` → seconds.
- Require ≥2 timestamps and a monotonic increasing sequence (guards against false matches).
- Each segment's **end** = next segment's start; the **last** segment's end = media duration
  (`ffprobe`/`info_dict['duration']`).
- A description tracklist without a `0:00` first entry: prepend `0:00` if the first real
  track starts later (intro), or start at the first timestamp — configurable.

## 5. Naming rules

For each segment `i` (1-based), title `t`:
- If `t` is a real, non-empty track title → `sanitize_filename(t)`.
- **If the chapter is unlabeled/blank → `NN_<video-title-summary>`**, i.e. a zero-padded
  sequence number plus a sanitized, length-capped summary of the *general* video title:
  `f"{i:02d}_{sanitize_filename(truncate(video_title))}"` → e.g. `03_80s_Playlist.mp3`.
- Optional leading `NN_` prefix for *all* tracks (reuse the existing `number_prefix` op).
- Zero-pad width = digits of the segment count (`01..12`, `001..120`).
- Collisions resolved with the existing 4-char salt (`_unique_name`).

Output folder: `<download_root>/<sanitize_filename(video_title)>_tracks/` (or `_playlist` so
it is picked up by `list_playlists`). Extension follows the download type (mp3 / mp4).

## 6. ffmpeg invocation

```
ffmpeg -y -ss <start> -to <end> -i <full_file> -c copy <out_dir>/<name>.<ext>
```
- `-c copy` (default): fast, no quality loss; cuts land on the nearest keyframe (sub-second
  drift) — fine for music/compilations.
- **Precise mode** (optional toggle): `-c:a libmp3lame -q:a 2` (audio) / re-encode video —
  exact boundaries, slower. Default off.
- Run segments sequentially (or a small pool); report progress via `current_download`
  (`completed_files/total_files`) so the existing progress UI + reconnect work unchanged.

## 7. Integration & UI entry points

- **Home:** a "Split by chapters/tracklist" checkbox (playlist-only options group; most
  useful for a **single** long video). On download, after the file is produced, run the
  splitter into a `_tracks`/`_playlist` folder.
- **File Manager / per-file:** a "Split into tracks" action on an already-downloaded file.
  Caveat: post-hoc split of a local file needs the boundaries — read **embedded chapters
  from the file via `ffprobe -show_chapters`** if present; otherwise the description isn't on
  disk and would require re-fetching `info_dict` by URL (store the source URL/id to enable
  this — see the Ignore-Duplicates manifest, which would also carry it).
- Reuses: `sanitize_filename`, `number_prefix`, `_unique_name`, the progress/reconnect
  pipeline, and the Playlists/File-Manager views (the output folder is just a playlist).

## 8. Edge cases / caveats

- **Format variance** in description tracklists → tolerant regex + a fallback that bails
  cleanly (no split) rather than producing garbage.
- **Keyframe accuracy** with `-c copy` (fraction-of-second drift); precise mode re-encodes.
- **Prefer embedded chapters** over description text when both exist (titles are cleaner).
- **No chapters and no timestamps** → nothing to split by; surface a clear "no tracklist
  found" message rather than failing.
- **Video vs audio** splits both work; keep the container consistent (`mp3`↔`mp3`,
  `mp4`↔`mp4`) so `-c copy` stays valid.
- **Very long compilations** (hundreds of tracks) → sequential ffmpeg is fine; show progress.

## 9. Data flow (sketch)

```
/api/download (split=true)
  → download_media downloads the full file (existing path)
  → chapters = info_dict['chapters'] or parse_description(description, duration)
  → for i, (start, end, title) in enumerate(chapters):
        name = title ? sanitize(title) : f"{i:02d}_{sanitize(summary(video_title))}"
        ffmpeg -ss start -to end -i full -c copy out_dir/name.ext
        update current_download progress
  → (optional) delete the full file, keep only tracks
```
New helpers (in `modules/download/`): `parse_description()`, `split_file()` (ffmpeg wrapper),
`chapter_segments(info_dict, duration)`. New param `split_chapters` on `/api/download`.

## 10. Open questions / non-goals

- Keep the full file as well, or only the tracks? (Recommend: option; default keep tracks.)
- Default to `-c copy` speed vs precise re-encode — expose a toggle.
- Cross-reference the Ignore-Duplicates **manifest** to store the source URL/id so File
  Manager "Split into tracks" can re-fetch a description when the file has no embedded chapters.
- **Non-goal:** silence-detection / automatic track boundaries without any tracklist — out of
  scope (needs `ffmpeg silencedetect` heuristics; unreliable).
