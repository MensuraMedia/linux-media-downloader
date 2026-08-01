# Concept: Ignore Duplicates

> **Status:** Concept / proposed — not yet implemented. Companion to the shipped
> "Skip long files (over 6 min)" option on the Home page. See
> [DOCUMENTATION.md](../DOCUMENTATION.md) for the current app.

## 1. Purpose

Add an **Ignore Duplicates** checkbox on the Home page (directly under **Skip long files
(over 6 min)**) so that, when downloading a playlist, the app **skips any track the user
already has** — both exact re-downloads and *near-duplicates* whose names differ only in
wording/order/formatting.

Because this app **rewrites filenames** (sanitize, remove-filler, case, truncate, …), the
names *on disk* are unreliable for comparison. The feature therefore depends on a **hidden
internal record of each file's ORIGINAL name (before any text modification)**, captured at
download time, against which incoming candidates are compared.

## 2. Home UI

- A checkbox **"Ignore Duplicates"** in the **Playlist** column, right under
  "Skip long files (over 6 min)". Same lifecycle as the other playlist-only options:
  visible always, **grayed/disabled until a playlist is detected**.
- Sends `ignore_dupes: true` on `POST /api/download` (alongside `skip_long`, `limit`).
- After a run, report how many were skipped as duplicates (e.g. in `current_download`:
  `skipped_duplicates`, surfaced in the status message / History).

## 3. The download manifest (source of truth)

A new persisted, git-ignored file: **`data/download_manifest.json`** — one entry per file
the app has downloaded, recorded **at download time** (before rename post-processing):

| Field | Why |
|-------|-----|
| `video_id` | yt-dlp `info_dict['id']` — the **strongest** dedup key (exact source identity) |
| `original_title` | yt-dlp `info_dict['title']` — the untouched title (pre-sanitize) |
| `norm_tokens` | normalized token signature (see §4) — precomputed for fast fuzzy matching |
| `duration`, `filesize` | secondary corroboration |
| `path`, `date` | bookkeeping / traceability |

Recording point: in `modules/download/media.py`, when a file finishes (the progress hook's
`finished` branch already sees `info_dict`) — capture `id`/`title` **there**, before the
`SanitizeFilenamePP` post-processor renames it.

**Backfill:** existing downloads predate the manifest and only have modified on-disk names.
Seed the manifest best-effort from current files (using the modified name as a weak key) so
the feature is useful immediately, and record true originals going forward. Flag seeded
entries as low-confidence (id/original unknown).

## 4. Matching strategy (layered)

For each candidate about to be downloaded, test against the manifest in order; skip on the
first hit:

1. **Exact source match** — `video_id` equals a manifest `video_id`. Certain; no false
   positives. (Requires the id to be available for the candidate, which yt-dlp provides.)
2. **Exact normalized-title match** — normalized candidate title equals a manifest entry's.
3. **Fuzzy / relevancy match ≥ threshold (default 80%)** — for parallel naming conventions.

### Normalization (shared with the app's text tools)

Lowercase → strip punctuation → split into tokens → **remove filler words**
(reuse `FILLER_WORDS`) and a small stopword set (`the, a, of, my, this, your, …`). Order is
discarded (compare as **sets/multisets**), so separators and word order don't matter.

### Relevancy score

Compute a similarity on the normalized token sets and treat **≥ 0.80** as a duplicate:

- Primary: **token-set similarity** — Sørensen–Dice `2·|A∩B| / (|A|+|B|)` (order-independent).
- Fallback/tie-break: `difflib.SequenceMatcher` ratio on the normalized strings (stdlib, no
  new dependency), for near-spellings.
- Take `max(dice, seq_ratio)` (or require both over a lower floor) — tunable.

Worked examples (after filler/stopword removal):

| Candidate | Existing | Tokens (norm) | Score | Skip? |
|-----------|----------|---------------|-------|-------|
| `Beach_Original_music` | `Original Beach Music` | {beach, music} vs {beach, music} (`original` = filler) | 1.00 | ✅ |
| `My_Cool_video` | `This Cool Video` | {cool} vs {cool} (`my/this` stop, `video` filler) | 1.00 | ✅ |
| `Predator Theme` | `Predator Suite` | {predator} vs {predator} | 1.00 | ⚠️ likely false-positive → see §6 |

The last row shows why a **token count / length guard** matters (very short signatures are
prone to false positives) — see risks.

## 5. Where the check runs

- On download start (`ignore_dupes` true), before fetching each playlist entry, run the
  match against the manifest. Reuse the existing **`match_filter`** hook in
  `download_media`: return a skip message for entries that match, so yt-dlp never downloads
  them (same mechanism as Skip-long). yt-dlp exposes `id`/`title`/`duration` to the filter.
- Combine with `skip_long` (both filters applied).
- Track `skipped_duplicates` in `current_download` for reporting.

New//reused building blocks:

| Need | Reuse | New |
|------|-------|-----|
| Normalization | `FILLER_WORDS`, sanitize helpers | stopword list, token signature |
| Skip mechanism | yt-dlp `match_filter` | dedup predicate |
| Record originals | progress hook `info_dict` | `data/download_manifest.json` + writer |
| Similarity | `difflib` (stdlib) | Dice on token sets, threshold |
| UI flag | Home options + `getScope()` pattern | `ignore_dupes` checkbox + param |

## 6. Risks / open questions

- **False positives** from short/generic signatures (`Predator Theme` vs `Predator Suite`).
  Mitigations: require a minimum token count (e.g. ≥3) for fuzzy matches, corroborate with
  duration/filesize, or only fuzzy-match above 0.85 when signatures are short.
- **Default threshold**: 80% as requested, but expose it (and an exact-only mode) — some
  users want strict de-dup.
- **In-batch duplicates**: also skip repeats within the same playlist, not just vs. history.
- **Backfill confidence**: seeded entries lack the true original/id; matches against them are
  weaker. Consider re-recording originals opportunistically.
- **Manifest growth/perf**: linear scan is fine for thousands; if it grows large, index by a
  sorted token signature or first-token bucket.
- **Cross-source dupes**: same song from two channels has different `video_id` but similar
  titles — the fuzzy layer catches these (intended).

## 7. Non-goals

- Not content-based (audio fingerprinting) de-duplication — names + ids + size only.
- Does not retroactively delete existing duplicates (that's the File Manager's job); this
  feature only **prevents new duplicate downloads**.
