#!/usr/bin/env python3
# modules/playlists.py
# Discover and manage previously-downloaded playlists (folders with >1 track).

import os
import re
import subprocess

from modules.config import settings
from modules.utils.file_utils import sanitize_filename

# Media file types we recognize as "tracks"
MEDIA_EXTS = {
    '.mp3', '.m4a', '.mp4', '.webm', '.opus', '.wav',
    '.flac', '.ogg', '.oga', '.mkv', '.aac', '.mov', '.avi',
}

# A "long" file is over 6 minutes
LONG_SECONDS = 360


def _scan_dirs():
    """Directories that may contain playlist folders (download roots + history)."""
    dirs = set()
    if settings.default_download_path:
        dirs.add(os.path.abspath(settings.default_download_path))
    for entry in settings.download_history:
        out = entry.get('output_dir')
        if not out:
            continue
        out = os.path.abspath(out)
        # Only treat the parent as a scan root when output_dir is an actual
        # "<name>_playlist" folder. Otherwise output_dir IS the download root —
        # using its parent would scan the whole home directory. (A playlist URL
        # grabbed in single mode records is_playlist=True but a non-playlist
        # output_dir, so is_playlist alone is not a reliable signal.)
        if os.path.basename(out).endswith('_playlist'):
            dirs.add(os.path.dirname(out))
        else:
            dirs.add(out)
    dirs.add(os.path.abspath('downloads'))
    return {d for d in dirs if os.path.isdir(d)}


def _is_media(name):
    return os.path.splitext(name)[1].lower() in MEDIA_EXTS


def _is_safe_path(path):
    """True only if `path` resolves inside one of the known download directories.

    Guards the destructive rename/delete operations against path traversal.
    """
    if not path:
        return False
    rp = os.path.realpath(path)
    for base in _scan_dirs():
        b = os.path.realpath(base)
        if rp == b or rp.startswith(b + os.sep):
            return True
    return False


def _safe_folder_name(name):
    """Sanitize a user-supplied folder name (allow spaces/brackets, block traversal)."""
    name = (name or '').strip().strip('.')
    name = re.sub(r'[/\\\x00]', '', name)
    return name[:200] or 'playlist'


def _duration(path):
    """Return media duration in seconds via ffprobe, or None if unavailable."""
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', path],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except Exception:
        return None


def _media_files(path):
    return sorted(
        f for f in os.listdir(path)
        if _is_media(f) and os.path.isfile(os.path.join(path, f))
    )


def list_playlists():
    """Return folders holding more than one media file, newest-name first."""
    seen = {}
    for base in _scan_dirs():
        try:
            entries = os.listdir(base)
        except OSError:
            continue
        for name in entries:
            folder = os.path.join(base, name)
            if not os.path.isdir(folder):
                continue
            try:
                files = _media_files(folder)
            except OSError:
                continue
            if len(files) > 1:  # a playlist = more than one song
                rp = os.path.realpath(folder)
                if rp in seen:
                    continue
                size = 0
                for f in files:
                    try:
                        size += os.path.getsize(os.path.join(folder, f))
                    except OSError:
                        pass
                seen[rp] = {
                    'name': name,
                    'path': folder,
                    'file_count': len(files),
                    'total_size': size,
                }
    return sorted(seen.values(), key=lambda x: x['name'].lower())


def list_playlist_files(path):
    """List a playlist's media files with duration and size, or None if invalid."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return None
    files = []
    for name in _media_files(path):
        fp = os.path.join(path, name)
        try:
            size = os.path.getsize(fp)
        except OSError:
            size = 0
        files.append({
            'filename': name,
            'size': size,
            'duration': _duration(fp),
        })
    return files


def rename_playlist(path, new_name):
    """Rename the playlist folder on disk."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}
    new_name = _safe_folder_name(new_name)
    parent = os.path.dirname(os.path.abspath(path))
    new_path = os.path.join(parent, new_name)
    if os.path.realpath(new_path) == os.path.realpath(path):
        return {'status': 'success', 'path': path, 'name': new_name}
    if os.path.exists(new_path):
        return {'status': 'error', 'message': 'A folder with that name already exists'}
    try:
        os.rename(path, new_path)
        return {'status': 'success', 'path': new_path, 'name': new_name}
    except OSError as e:
        return {'status': 'error', 'message': str(e)}


def delete_long_files(path, max_seconds=LONG_SECONDS):
    """Delete media files whose duration exceeds max_seconds."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}
    deleted = 0
    for name in _media_files(path):
        fp = os.path.join(path, name)
        dur = _duration(fp)
        if dur is not None and dur > max_seconds:
            try:
                os.remove(fp)
                deleted += 1
            except OSError:
                pass
    return {'status': 'success', 'deleted': deleted}


def _rename_within(path, mapper):
    """Apply mapper(base_name, index) -> new_base to each media file. Skips collisions."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}
    renamed = 0
    for idx, name in enumerate(_media_files(path)):
        base, ext = os.path.splitext(name)
        new_name = mapper(base, idx) + ext
        if new_name == name:
            continue
        dst = os.path.join(path, new_name)
        if os.path.exists(dst):
            continue
        try:
            os.rename(os.path.join(path, name), dst)
            renamed += 1
        except OSError:
            pass
    return {'status': 'success', 'renamed': renamed}


def apply_operation(path, operation):
    """Dispatch a bulk file operation over a playlist folder."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}

    if operation == 'delete_long':
        return delete_long_files(path)
    if operation == 'remove_special':
        return _rename_within(path, lambda b, i: re.sub(r'[^\w\s.-]', '', b).strip())
    if operation == 'replace_spaces':
        return _rename_within(path, lambda b, i: re.sub(r'\s+', '_', b.strip()))
    if operation == 'clean':
        # Full clean: strip specials, collapse spaces/dashes to underscores.
        return _rename_within(path, lambda b, i: os.path.splitext(sanitize_filename(b + '.x'))[0])
    if operation == 'number_prefix':
        files = _media_files(path)
        width = max(2, len(str(len(files))))
        return _rename_within(
            path,
            lambda b, i: f"{str(i + 1).zfill(width)}_{re.sub(r'^[0-9]+[_-]', '', b)}",
        )
    return {'status': 'error', 'message': f'Unknown operation: {operation}'}
