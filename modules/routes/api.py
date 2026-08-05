#!/usr/bin/env python3
# modules/routes/api.py
# API routes for YT Media Backup

import os
from flask import Blueprint, request, jsonify, send_file
from modules.config.settings import (
    current_download,
    default_download_path,
    download_queue,
    request_cancel,
    add_link_history,
)
from modules.download.media import get_video_info, enqueue_download
from modules.utils.file_utils import open_folder

# Create blueprint
api_routes = Blueprint('api_routes', __name__)

@api_routes.route('/api/check-url', methods=['POST'])
def check_url():
    """Check if URL is a single video or playlist"""
    data = request.get_json()
    url = data.get('url', '')
    
    if not url:
        return jsonify({'error': 'No URL provided'})
    
    info = get_video_info(url)
    return jsonify(info)

@api_routes.route('/api/get-default-path')
def get_default_path():
    """Get the default download path"""
    return jsonify({"path": default_download_path})

@api_routes.route('/api/download', methods=['POST'])
def start_download():
    """Start the download process"""
    data = request.get_json()
    url = data.get('url', '')
    output_dir = data.get('output_dir', default_download_path)
    download_type = data.get('download_type', 'audio')
    playlist_mode = data.get('playlist_mode', 'single')
    # Video resolution cap; ignored for audio (always highest quality).
    # Whitelist to the two supported values, defaulting to 1080p.
    video_quality = str(data.get('video_quality', '1080'))
    if video_quality not in ('720', '1080'):
        video_quality = '1080'
    skip_long = bool(data.get('skip_long', False))
    split_chapters = bool(data.get('split_chapters', False))
    ignore_dupes = bool(data.get('ignore_dupes', False))
    try:
        limit = int(data.get('limit', 0) or 0)
    except (TypeError, ValueError):
        limit = 0

    if not url:
        return jsonify({'error': 'No URL provided'})

    # Record the submitted link in the links history (title filled in later
    # once the download worker resolves it).
    add_link_history(url, download_type, playlist_mode)

    # Add to the queue. It starts immediately if idle, else runs after the
    # current/earlier jobs finish (one at a time).
    job = enqueue_download(url, output_dir, download_type, playlist_mode, skip_long, limit,
                           split_chapters, ignore_dupes, video_quality=video_quality)

    if job.get('status') == 'active':
        return jsonify({'status': 'started', 'job_id': job['id']})
    # Position among still-queued jobs
    position = sum(1 for j in download_queue if j.get('status') == 'queued'
                   and j['id'] <= job['id'])
    return jsonify({'status': 'queued', 'job_id': job['id'], 'position': position})

@api_routes.route('/api/cancel-download', methods=['POST'])
def cancel_download():
    """Cancel the current download process"""
    # Signal the running download thread to stop (single source of truth).
    request_cancel()

    # Update the current download status
    current_download["status"] = "cancelled"
    current_download["message"] = "Download cancelled by user"

    # Record the partial download in history before returning.
    # (Previously this block was dead code placed after the return statement.)
    from modules.config.settings import download_history, save_download_history

    # Only add to history if we have current download info
    if current_download.get('playlist_title') or current_download.get('current_file'):
        # Create a title from playlist or current file
        title = current_download.get('playlist_title') or current_download.get('current_file', 'Unknown')
        from datetime import datetime
        download_history.append({
            'url': '',  # URL might not be accessible here
            'output_dir': current_download.get('output_path', ''),
            'download_type': current_download.get('selected_mode', 'unknown'),
            'is_playlist': current_download.get('is_playlist', False),
            'title': title,
            'status': 'completed_with_errors',  # This will show as 'Partial'
            'timestamp': datetime.now().isoformat(timespec='seconds')
        })
        save_download_history()

    return jsonify({"status": "cancelled"})


@api_routes.route('/api/download-status')
def download_status():
    """Get the current download status (+ how many jobs are still queued)."""
    data = dict(current_download)
    data['queue_pending'] = sum(1 for j in download_queue if j.get('status') == 'queued')
    return jsonify(data)


@api_routes.route('/api/queue')
def queue_route():
    """Return the download queue (queued, active, and finished jobs) for Pending."""
    return jsonify([
        {k: j.get(k) for k in ('id', 'url', 'title', 'status', 'download_type',
                               'playlist_mode', 'queued_at')}
        for j in download_queue
    ])


@api_routes.route('/api/clear-queue-finished', methods=['POST'])
def clear_queue_finished_route():
    """Remove finished/errored/cancelled jobs from the queue list."""
    download_queue[:] = [j for j in download_queue
                         if j.get('status') in ('queued', 'active')]
    return jsonify({'status': 'ok', 'remaining': len(download_queue)})

@api_routes.route('/api/links-history')
def links_history_route():
    """Return the links history, newest first."""
    from modules.config.settings import links_history
    return jsonify(list(reversed(links_history)))


@api_routes.route('/api/clear-links-history', methods=['POST'])
def clear_links_history():
    """Clear the entire links history."""
    from modules.config.settings import links_history, save_links_history
    links_history.clear()
    save_links_history()
    return jsonify({'status': 'cleared'})


@api_routes.route('/api/playlists')
def playlists_route():
    """List previously-downloaded playlists (folders with more than one track)."""
    from modules import playlists
    return jsonify(playlists.list_playlists())


@api_routes.route('/api/playlist-files', methods=['POST'])
def playlist_files_route():
    """List the media files in a playlist folder (length / name / size)."""
    from modules import playlists
    path = (request.get_json() or {}).get('path', '')
    files = playlists.list_playlist_files(path)
    if files is None:
        return jsonify({'error': 'Invalid or unknown playlist path'}), 400
    return jsonify({'path': path, 'files': files,
                    'trash_count': playlists.trash_count(path), **playlists.stack_state()})


@api_routes.route('/api/rename-playlist', methods=['POST'])
def rename_playlist_route():
    """Rename a playlist folder on disk."""
    from modules import playlists
    data = request.get_json() or {}
    return jsonify(playlists.rename_playlist(data.get('path', ''), data.get('new_name', '')))


@api_routes.route('/api/playlist-operation', methods=['POST'])
def playlist_operation_route():
    """Apply a bulk file operation to a playlist folder."""
    from modules import playlists
    data = request.get_json() or {}
    return jsonify(playlists.apply_operation(data.get('path', ''), data.get('operation', '')))


@api_routes.route('/api/playlist-undo', methods=['POST'])
def playlist_undo_route():
    """Undo the most recent playlist file operation."""
    from modules import playlists
    return jsonify(playlists.undo_last())


@api_routes.route('/api/playlist-redo', methods=['POST'])
def playlist_redo_route():
    """Redo the most recently undone playlist file operation."""
    from modules import playlists
    return jsonify(playlists.redo_last())


@api_routes.route('/api/playlist-color', methods=['POST'])
def playlist_color_route():
    """Set the badge color for a playlist."""
    from modules import playlists
    data = request.get_json() or {}
    return jsonify(playlists.set_playlist_color(data.get('path', ''), data.get('color', '')))


@api_routes.route('/api/playlist-empty-trash', methods=['POST'])
def playlist_empty_trash_route():
    """Permanently purge a playlist's .trash folder."""
    from modules import playlists
    path = (request.get_json() or {}).get('path', '')
    return jsonify(playlists.empty_trash(path))


@api_routes.route('/api/all-media')
def all_media_route():
    """List every downloaded media file (for the Player)."""
    from modules import playlists
    return jsonify(playlists.list_all_media())


@api_routes.route('/api/media')
def serve_media_route():
    """Stream a media file (supports range requests for seeking)."""
    from modules import playlists
    path = request.args.get('path', '')
    if not playlists.is_safe_path(path) or not os.path.isfile(path):
        return jsonify({'error': 'Not found'}), 404
    return send_file(path, conditional=True)


@api_routes.route('/api/app-media')
def app_media_route():
    """List media files this app recorded (for the File Manager)."""
    from modules import playlists
    return jsonify(playlists.list_app_media())


@api_routes.route('/api/file-stats')
def file_stats_route():
    """Stats over app-recorded files (total / duplicate names / same size)."""
    from modules import playlists
    return jsonify(playlists.file_stats())


@api_routes.route('/api/global-operation', methods=['POST'])
def global_operation_route():
    """Apply a text operation across every app folder as one undoable action."""
    from modules import playlists
    op = (request.get_json() or {}).get('operation', '')
    return jsonify(playlists.global_operation(op))


@api_routes.route('/api/delete-media', methods=['POST'])
def delete_media_route():
    """Move a single media file to trash."""
    from modules import playlists
    path = (request.get_json() or {}).get('path', '')
    return jsonify(playlists.delete_media_file(path))


@api_routes.route('/api/add-to-folder', methods=['POST'])
def add_to_folder_route():
    """Copy a media file into a (new) curation folder."""
    from modules import playlists
    data = request.get_json() or {}
    return jsonify(playlists.add_to_folder(data.get('path', ''), data.get('folder', '')))


@api_routes.route('/api/settings')
def get_settings_route():
    """Return the user-editable text-control settings."""
    from modules.config import user_settings
    return jsonify(user_settings.get_settings())


@api_routes.route('/api/settings', methods=['POST'])
def save_settings_route():
    """Save filler words + character replacements."""
    from modules.config import user_settings
    data = request.get_json() or {}
    return jsonify(user_settings.save_settings(data))


@api_routes.route('/api/settings/reset', methods=['POST'])
def reset_settings_route():
    """Reset text-control settings to defaults."""
    from modules.config import user_settings
    return jsonify(user_settings.save_settings(user_settings._defaults()))


@api_routes.route('/api/open-folder', methods=['POST'])
def api_open_folder():
    """Open a folder in the file explorer"""
    data = request.get_json()
    folder_path = data.get('path', '')
    
    result = open_folder(folder_path)
    return jsonify(result)
