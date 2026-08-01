# Concept: File Manager

> **Status:** Concept / proposed — not yet implemented. This document specifies the feature
> so it can be built later. See [DOCUMENTATION.md](../DOCUMENTATION.md) for the shipped app.

## 1. Purpose

A **File Manager** tab that gives a dense, spreadsheet-like overview of *every music file
this app has downloaded*, with statistics, global bulk text operations, an inline per-file
mini-player with keyboard control, and quick per-file deletion. It complements:

- **Player** — one-at-a-time listening + curation into new folders.
- **Playlists** — per-folder management of a single playlist.

The File Manager is the "power user" bulk view across **all app files at once**.

## 2. Sidebar

Add a **File Manager** entry to the sidebar (after **Player**):
`Home · History · Playlists · Player · File Manager · Links · About`.
Route: `GET /file-manager` → `file-manager.html`.

## 3. Scope — app-recorded files only

The list must show only files **this app downloaded/recorded**, *not* every music file on
the system. Proposed source of truth (union, de-duplicated by real path):

1. Media files inside app playlist folders (the `*_playlist` roots already discovered by
   `list_playlists` / `_scan_dirs`).
2. Media files recorded in `download_history` (their `output_dir`).
3. Files added via the Player's "Add to folder" curation (they live under the download root).

This is intentionally narrower than the Player's `/api/all-media` (which walks the whole
download root). A new endpoint **`GET /api/app-media`** should return only app-recorded
files. *(Open question: do we persist a manifest of downloaded files at download time for a
precise set, or keep deriving it from history + folders? A manifest is more accurate.)*

Each entry: `{name, path, folder, size}` (duration optional/lazy — ffprobe is slow at scale).

## 4. Layout — dense filename grid

- A **tight grid**, **3 or more columns** wide, **cell padding/margin of ~1px**, each cell
  showing **only the file name** (ellipsis on overflow). Goal: see hundreds of names at a
  glance. Responsive: 3 columns on narrow, more on wide.
- Each cell contains, left→right:
  1. a small **play icon** (inline mini-player trigger),
  2. the **file name** (muted/greyed once deleted),
  3. a **trash icon** on the right of the name.
- A search/filter box filters the grid.

```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│ ▶ 01_Theme.mp3       🗑 │ ▶ 02_Arrival.mp3     🗑 │ ▶ 03_Tunnel.mp3      🗑 │
│ ▶ 04_Love.mp3        🗑 │ ▶ 05_Future.mp3      🗑 │ ▶ 06_Factory.mp3     🗑 │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

## 5. Statistics header (above the table)

A stat strip computed server-side (`GET /api/file-stats`, scoped to app-recorded files):

| Stat | Definition |
|------|------------|
| **Total files** | Count of app-recorded media files. |
| **Duplicate files** | Files sharing the **same file name** (basename) in ≥2 locations — count of files involved in a name collision. |
| **Similar files** | Files with an **exact matching file size** (a cheap "likely identical" heuristic) — count involved in a size collision. |

Notes: duplicates are grouped by `name`; similar by `size`. A future refinement could pair
"same name AND same size" as strong-duplicate, or hash contents for certainty (expensive).
The stat tiles should be clickable to filter the grid to just those files.

## 6. Global text controls

The **same operations as the Playlists page**, but applied **across all app-recorded files
everywhere** rather than one folder:

`clean · remove_special · replace_spaces · remove_filler · truncate · standard_font ·
abbreviate_dupes · number_prefix · lower_case · upper_case · title_case · camel_case`

Implementation notes / differences from per-folder ops:
- Operates on the full app-file set (or the current filtered/selected subset — selection is
  a nice enhancement). A new endpoint **`POST /api/global-operation {operation}`** (and an
  optional `paths[]` to limit to a selection).
- Reuse `modules/playlists.py` helpers (`_rename_within` logic, filler/case functions,
  `_unique_name` salt) but iterate per containing folder so collisions are resolved within
  each folder. `abbreviate_dupes` and `number_prefix` are inherently per-folder — decide
  whether "everywhere" means per-folder application or one global numbering (recommend
  per-folder to stay meaningful).
- Wire into the same **Undo/Redo** stack (moves are recorded), so a global rename is
  reversible like folder ops. Confirm destructive ops.
- Guard every path with `is_safe_path`.

## 7. Inline mini-player + keyboard controls

Clicking a file's play icon streams it via the existing `GET /api/media?path=…` (range
requests already supported) into a shared hidden `<audio>` element. The **currently-playing**
cell is highlighted and captures keyboard input:

| Key | Action |
|-----|--------|
| **→ (ArrowRight)** | Seek **forward 5 seconds** |
| **← (ArrowLeft)** | Seek **back 2 seconds** |
| **↑ (ArrowUp)** | **Volume up** (e.g. +10%) |
| **↓ (ArrowDown)** | **Volume down** (e.g. −10%) |
| **Delete** | **Stop playback immediately and delete the file** |

- Arrow keys must `preventDefault()` while a track is active so the page doesn't scroll.
- Only one file plays at a time; starting another stops the previous.

## 8. Deletion UX

Two ways to delete, both via `POST /api/delete-media` (moves the file to its folder's
`.trash`, consistent with the rest of the app — recoverable):

1. The per-file **trash icon** to the right of the name.
2. The **Delete key** while that file is playing (also stops playback instantly).

After deletion:
- Playback stops and the shared player is cleared.
- The deleted cell's **file name and play icon turn a muted/greyed colour** and become
  non-interactive, so the user can see the file is gone and nothing else can play from it.
- Stats refresh (total/duplicate/similar counts update).

## 9. Reused vs. new building blocks

| Need | Reuse | New |
|------|-------|-----|
| Stream + seek | `GET /api/media` (range) | — |
| Delete → trash | `POST /api/delete-media` | — |
| Path safety | `is_safe_path` | — |
| Text ops | `playlists.py` helpers | `POST /api/global-operation` |
| File list | — | `GET /api/app-media` (scoped) |
| Stats | — | `GET /api/file-stats` |
| Page/route | base sidebar pattern | `/file-manager`, `file-manager.html` |

## 10. Open questions / risks

- **Precise scoping:** derive app files from history+folders, or persist a download manifest?
  A manifest is the accurate answer and would also power better stats.
- **Scale:** hundreds/thousands of files → keep the grid virtualized or paginated if needed;
  compute stats server-side; avoid ffprobe in the list.
- **"Everywhere" ops** on huge sets could be slow and hard to undo in one step — consider a
  progress indicator and chunked undo grouping.
- **Duplicate/similar accuracy:** name-match and size-match are heuristics; content hashing
  is the only certain test but is expensive.

## 11. Non-goals

- Not a general system file browser — strictly app-recorded media.
- No move/cut-paste file management beyond delete + the existing "add to folder" curation.
