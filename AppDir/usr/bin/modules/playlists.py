#!/usr/bin/env python3
# modules/playlists.py
# Discover and manage previously-downloaded playlists (folders with >1 track).

import os
import re
import hashlib
import subprocess
import unicodedata

from modules.config import settings
from modules.utils.file_utils import sanitize_filename

# Media file types we recognize as "tracks"
MEDIA_EXTS = {
    '.mp3', '.m4a', '.mp4', '.webm', '.opus', '.wav',
    '.flac', '.ogg', '.oga', '.mkv', '.aac', '.mov', '.avi',
}

# A "long" file is over 6 minutes
LONG_SECONDS = 360

# Max characters kept by the "truncate" operation
TRUNCATE_LEN = 35

# Common clutter words stripped by the "remove filler" operation (case-insensitive)
FILLER_WORDS = {
    'music', 'mix', 'remaster', 'remastered', 'live', '4k', '8k', 'hd', 'uhd',
    'hq', 'original', 'remix', 'cover', 'official', 'video', 'audio', 'visualizer',
    'lyric', 'lyrics', 'full', 'album', 'version', 'feat', 'ft', 'explicit',
    'clean', 'mv', 'hq', 'edit', 'extended', 'radio',
    # months (full + abbreviations)
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec',
}


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
    """Move media files longer than max_seconds into a .trash folder (undoable)."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}
    trash = os.path.join(path, '.trash')
    moves = []
    for name in _media_files(path):
        fp = os.path.join(path, name)
        dur = _duration(fp)
        if dur is not None and dur > max_seconds:
            os.makedirs(trash, exist_ok=True)
            dst = os.path.join(trash, _unique_name(trash, name, name))
            try:
                os.rename(fp, dst)
                moves.append((fp, dst))
            except OSError:
                pass
    _record(moves)
    return {'status': 'success', 'deleted': len(moves), **stack_state()}


# ── Undo / redo ──────────────────────────────────────────────────────────────
# Each recorded op is a list of (src, dst) moves that were performed. Undo
# reverses them; redo replays them. State is in-memory (resets on restart).
_undo_stack = []
_redo_stack = []


def stack_state():
    return {'can_undo': bool(_undo_stack), 'can_redo': bool(_redo_stack)}


def _record(moves):
    if moves:
        _undo_stack.append(moves)
        _redo_stack.clear()


def _safe_move(src, dst):
    if not (_is_safe_path(src) and _is_safe_path(os.path.dirname(dst))):
        return False
    if os.path.exists(dst):
        return False
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)
        return True
    except OSError:
        return False


def _apply_moves(moves):
    return sum(1 for src, dst in moves if _safe_move(src, dst))


def undo_last():
    """Reverse the most recent operation."""
    if not _undo_stack:
        return {'status': 'noop', **stack_state()}
    moves = _undo_stack.pop()
    changed = _apply_moves([(dst, src) for (src, dst) in reversed(moves)])
    _redo_stack.append(moves)
    return {'status': 'success', 'changed': changed, **stack_state()}


def redo_last():
    """Replay the most recently undone operation."""
    if not _redo_stack:
        return {'status': 'noop', **stack_state()}
    moves = _redo_stack.pop()
    changed = _apply_moves(moves)
    _undo_stack.append(moves)
    return {'status': 'success', 'changed': changed, **stack_state()}


def _unique_name(path, new_name, original):
    """Return new_name, inserting a 4-char salt before the extension on collision."""
    if not os.path.exists(os.path.join(path, new_name)):
        return new_name
    base, ext = os.path.splitext(new_name)
    salt = hashlib.md5(original.encode('utf-8', 'ignore')).hexdigest()[:4]
    candidate = f"{base}_{salt}{ext}"
    n = 1
    while os.path.exists(os.path.join(path, candidate)):
        candidate = f"{base}_{salt}{n}{ext}"
        n += 1
    return candidate


def _rename_within(path, mapper):
    """Apply mapper(base_name, index) -> new_base to each media file.

    On a name collision a 4-character salt is inserted before the extension so
    uniqueness is always preserved (rather than skipping the file).
    """
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}
    moves = []
    for idx, name in enumerate(_media_files(path)):
        base, ext = os.path.splitext(name)
        new_base = (mapper(base, idx) or '').strip() or base
        new_name = new_base + ext
        if new_name == name:
            continue
        new_name = _unique_name(path, new_name, name)
        src = os.path.join(path, name)
        dst = os.path.join(path, new_name)
        try:
            os.rename(src, dst)
            moves.append((src, dst))
        except OSError:
            pass
    _record(moves)
    return {'status': 'success', 'renamed': len(moves), **stack_state()}


def _split_camel(token):
    """Split a CamelCase / PascalCase token into its words (e.g. OfficialVideo)."""
    parts = re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+', token)
    return parts or [token]


def _is_filler_word(word):
    low = word.lower()
    return low in FILLER_WORDS or bool(re.fullmatch(r'(?:19|20)\d{2}', low))


def _remove_filler(base):
    """Drop clutter words (filler + years) — even when glued together in camelCase.

    e.g. "Artist - Song (Official Music Video) [4K HD]" -> "Artist Song"
         "SongTitleOfficialVideo"                       -> "SongTitle"
    """
    out = []
    for tok in re.split(r'[\s_\-\[\]\(\)\{\}]+', base):
        if not tok:
            continue
        # Whole-token match first so units like "4K"/"HD" and years are caught
        # before camelCase splitting breaks them apart.
        whole = re.sub(r'[^\w]', '', tok)
        if whole and _is_filler_word(whole):
            continue
        kept = [s for s in _split_camel(tok) if not _is_filler_word(s)]
        if kept:
            out.append(''.join(kept))
    return ' '.join(out).strip()


def _to_standard(base):
    """Normalize fancy / accented / full-width characters to standard ASCII."""
    norm = unicodedata.normalize('NFKD', base)
    return norm.encode('ascii', 'ignore').decode('ascii').strip()


def _title_case(base):
    return re.sub(r'\b\w', lambda m: m.group().upper(), base.lower())


def _camel_case(base):
    words = [w for w in re.split(r'[\s_\-]+', base) if w]
    return ''.join(w[:1].upper() + w[1:].lower() for w in words)


def apply_operation(path, operation):
    """Dispatch a bulk file operation over a playlist folder."""
    if not _is_safe_path(path) or not os.path.isdir(path):
        return {'status': 'error', 'message': 'Invalid playlist path'}

    if operation == 'delete_long':
        return delete_long_files(path)

    if operation == 'number_prefix':
        files = _media_files(path)
        width = max(2, len(str(len(files))))
        return _rename_within(
            path,
            lambda b, i: f"{str(i + 1).zfill(width)}_{re.sub(r'^[0-9]+[_-]', '', b)}",
        )

    rename_ops = {
        'remove_special': lambda b, i: re.sub(r'[^\w\s.-]', '', b).strip(),
        'replace_spaces': lambda b, i: re.sub(r'\s+', '_', b.strip()),
        # Full clean: strip specials, collapse spaces/dashes to underscores.
        'clean':          lambda b, i: os.path.splitext(sanitize_filename(b + '.x'))[0],
        'truncate':       lambda b, i: b[:TRUNCATE_LEN].strip(),
        'remove_filler':  lambda b, i: _remove_filler(b),
        'standard_font':  lambda b, i: _to_standard(b),
        'lower_case':     lambda b, i: b.lower(),
        'upper_case':     lambda b, i: b.upper(),
        'title_case':     lambda b, i: _title_case(b),
        'camel_case':     lambda b, i: _camel_case(b),
    }
    if operation in rename_ops:
        return _rename_within(path, rename_ops[operation])

    return {'status': 'error', 'message': f'Unknown operation: {operation}'}
