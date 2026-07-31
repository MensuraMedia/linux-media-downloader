#!/usr/bin/env python3
# modules/routes/api.py
# API routes for YT Media Backup

from flask import Blueprint, request, jsonify
from modules.config.settings import current_download, default_download_path, request_cancel
from modules.download.media import get_video_info, start_download_thread
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
    
    if not url:
        return jsonify({'error': 'No URL provided'})
    
    # Start download in a separate thread
    start_download_thread(url, output_dir, download_type, playlist_mode)
    
    return jsonify({'status': 'started'})

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
        download_history.append({
            'url': '',  # URL might not be accessible here
            'output_dir': current_download.get('output_path', ''),
            'download_type': current_download.get('selected_mode', 'unknown'),
            'is_playlist': current_download.get('is_playlist', False),
            'title': title,
            'status': 'completed_with_errors'  # This will show as 'Partial'
        })
        save_download_history()

    return jsonify({"status": "cancelled"})


@api_routes.route('/api/download-status')
def download_status():
    """Get the current download status"""
    return jsonify(current_download)

@api_routes.route('/api/open-folder', methods=['POST'])
def api_open_folder():
    """Open a folder in the file explorer"""
    data = request.get_json()
    folder_path = data.get('path', '')
    
    result = open_folder(folder_path)
    return jsonify(result)
