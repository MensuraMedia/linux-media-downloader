---
date: 2026-08-02
type: feature
files_changed:
  - modules/config/settings.py (download_queue)
  - modules/download/media.py (queue manager)
  - modules/routes/api.py
  - modules/routes/ui.py
  - templates/base.html, pending.html (new), index.html
  - tests/test_app.py
---
## Change: Download queue + Pending page

- **Queue backend** (`media.py`): `enqueue_download()` appends a job to
  `settings.download_queue` and `_start_next_if_idle()` runs the next job in a worker
  thread when nothing is active (`_download_active()` checks live status + active jobs).
  `_run_job()` runs `download_media` to completion, sets the job status/title, then starts
  the next — so jobs run strictly one at a time. `current_download['job_id']` tags the active job.
- **API**: `/api/download` now ENQUEUES (returns `started` if it began immediately, else
  `queued` + `position`) instead of rejecting a concurrent request. `/api/download-status`
  adds `queue_pending`. New `/api/queue` and `/api/clear-queue-finished`.
- **Pending page** (`/pending` + sidebar button under Home): lists jobs (active/queued first,
  then finished) with status badges, live auto-refresh, and Clear-finished.
- **Home**: adding a link while a download runs queues it (shows "added to queue, see
  Pending") without disturbing the active progress; the poller rebuilds the table when
  `job_id` changes (follows each job) and keeps polling while `queue_pending>0`; on final
  completion shows "See your download here →" linking to History Downloads. Input clears on
  submit so the next link can be added immediately.

### Verification
- 74/74 pytest (queued-when-active, /api/queue list, queue_pending, /pending renders).
- **Live:** 3 jobs submitted — job1 started, 2 & 3 queued; they completed one-after-another;
  Pending page showed ACTIVE + COMPLETED with resolved titles. pyflakes/compile clean.
