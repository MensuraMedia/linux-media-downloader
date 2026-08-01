#!/usr/bin/env python3
# modules/download/chapters.py
# Split a single downloaded file into per-track files using chapters or a
# description tracklist (see docs/concept-chapter-split.md).

import os
import re
import subprocess

from modules.utils.file_utils import sanitize_filename

MEDIA_EXTS = {'.mp3', '.m4a', '.mp4', '.webm', '.opus', '.wav', '.flac', '.ogg', '.aac', '.mkv'}

# A timestamped tracklist line, tolerant of common formats:
#   "0:00 Title", "1) 3:14 - Title", "12:03 – Artist - Title", "1:02:03 | Title"
_TS_LINE = re.compile(r'^\s*\d{0,3}[\.\)]?\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—|:]?\s*(.*)$')


def parse_timestamp(ts):
    """'m:ss' or 'h:mm:ss' -> seconds (int), or None."""
    try:
        parts = [int(p) for p in ts.split(':')]
    except ValueError:
        return None
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


def parse_description(description, duration=None):
    """Parse timestamped description lines into [{start, end, title}] segments."""
    segs = []
    last = -1
    for line in (description or '').splitlines():
        m = _TS_LINE.match(line)
        if not m:
            continue
        start = parse_timestamp(m.group(1))
        if start is None or start <= last:   # require strictly increasing
            continue
        title = m.group(2).strip(' \t-–—|:').strip()
        segs.append({'start': start, 'title': title})
        last = start
    if len(segs) < 2:
        return []
    return _fill_ends(segs, duration)


def _fill_ends(segs, duration):
    for i, s in enumerate(segs):
        s['end'] = segs[i + 1]['start'] if i + 1 < len(segs) else duration
    return segs


def chapter_segments(info_dict, duration=None):
    """Prefer embedded chapters; fall back to the description tracklist."""
    info_dict = info_dict or {}
    duration = duration or info_dict.get('duration')
    chapters = info_dict.get('chapters')
    if chapters:
        return [{
            'start': c.get('start_time') or 0,
            'end': c.get('end_time'),
            'title': (c.get('title') or '').strip(),
        } for c in chapters]
    return parse_description(info_dict.get('description', ''), duration)


def segment_filename(seg, index, count, video_title):
    """Track title if present, else 'NN_<video-title-summary>' (the unlabeled fallback)."""
    width = max(2, len(str(count)))
    title = (seg.get('title') or '').strip()
    if title:
        return sanitize_filename(title) or f"{str(index + 1).zfill(width)}"
    summary = sanitize_filename((video_title or 'video')[:40]).strip('_') or 'video'
    return f"{str(index + 1).zfill(width)}_{summary}"


def _unique(out_dir, name, ext):
    dst = os.path.join(out_dir, f"{name}.{ext}")
    n = 1
    while os.path.exists(dst):
        dst = os.path.join(out_dir, f"{name}_{n}.{ext}")
        n += 1
    return dst


def split_file(src_path, segments, out_dir, video_title, reencode=False, on_progress=None):
    """Cut src_path into one file per segment with ffmpeg. Returns {status, tracks}.

    on_progress(i, count, title) is called before each segment (for UI updates).
    """
    if not segments:
        return {'status': 'error', 'message': 'No chapters/tracklist found', 'tracks': 0}
    if not os.path.isfile(src_path):
        return {'status': 'error', 'message': 'Source file missing', 'tracks': 0}
    ext = os.path.splitext(src_path)[1].lstrip('.').lower() or 'mp3'
    os.makedirs(out_dir, exist_ok=True)
    count = len(segments)
    made = 0
    for i, seg in enumerate(segments):
        if on_progress:
            try:
                on_progress(i, count, segment_filename(seg, i, count, video_title))
            except Exception:
                pass
        dst = _unique(out_dir, segment_filename(seg, i, count, video_title), ext)
        cmd = ['ffmpeg', '-y', '-ss', str(seg['start']), '-i', src_path]
        if seg.get('end') is not None:
            dur = float(seg['end']) - float(seg['start'])
            if dur > 0:
                cmd += ['-t', str(dur)]
        cmd += (['-c:a', 'libmp3lame', '-q:a', '2'] if (reencode and ext == 'mp3') else ['-c', 'copy'])
        cmd += [dst]
        try:
            subprocess.run(cmd, capture_output=True, timeout=600)
            if os.path.isfile(dst) and os.path.getsize(dst) > 0:
                made += 1
        except Exception:
            pass
    return {'status': 'success', 'tracks': made}
