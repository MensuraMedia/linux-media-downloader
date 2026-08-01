#!/usr/bin/env python3
# modules/download/media.py
# Download functionality for YT Media Backup

import os
import threading
import yt_dlp
from modules.utils.file_utils import sanitize_filename
from modules.config.settings import (
    current_download,
    download_history,
    reset_cancel,
    is_cancel_requested,
)

def get_video_info(url):
    """Get information about the video or playlist"""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Check if it's a playlist
            if '_type' in info and info['_type'] == 'playlist':
                # Get info for the first video to determine if this is a video within a playlist
                if len(info.get('entries', [])) > 0 and 'url' in info['entries'][0]:
                    first_video_url = info['entries'][0]['url']
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                            video_info = ydl2.extract_info(first_video_url, download=False)
                            
                            return {
                                'is_playlist': True,
                                'is_video_in_playlist': True,
                                'title': info.get('title', 'Playlist'),
                                'video_title': video_info.get('title', 'Video'),
                                'entries': len(info.get('entries', [])),
                                'url': url,
                                'video_url': first_video_url
                            }
                    except Exception:
                        # If fetching individual video info fails, continue with playlist info
                        pass
                
                return {
                    'is_playlist': True,
                    'is_video_in_playlist': False,
                    'title': info.get('title', 'Playlist'),
                    'entries': len(info.get('entries', [])),
                    'url': url
                }
            else:
                # Check if this URL is part of a playlist by looking for the playlist parameter
                if 'list=' in url and 'youtube.com' in url:
                    # Try to get playlist info
                    playlist_url = url
                    if '&list=' in url:
                        playlist_url = 'https://www.youtube.com/playlist?list=' + url.split('&list=')[1].split('&')[0]
                    elif '?list=' in url:
                        playlist_url = 'https://www.youtube.com/playlist?list=' + url.split('?list=')[1].split('&')[0]
                    
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                            playlist_info = ydl2.extract_info(playlist_url, download=False)
                            
                            if '_type' in playlist_info and playlist_info['_type'] == 'playlist':
                                return {
                                    'is_playlist': True,
                                    'is_video_in_playlist': True,
                                    'title': playlist_info.get('title', 'Playlist'),
                                    'video_title': info.get('title', 'Video'),
                                    'entries': len(playlist_info.get('entries', [])),
                                    'url': url,
                                    'playlist_url': playlist_url
                                }
                    except Exception:
                        # If fetching playlist info fails, continue with single video info
                        pass
                
                # Not a playlist
                return {
                    'is_playlist': False,
                    'title': info.get('title', 'Video'),
                    'url': url
                }
    except Exception as e:
        return {
            'is_playlist': False,
            'title': 'Unknown',
            'error': str(e),
            'url': url
        }

class DownloadProgress:
    """Progress callback for YT-DLP"""
    def __init__(self, total_files=1):
        self.current_file = ""
        self.total_files = total_files
        self.completed_files = 0
        self.info = None   # richest info_dict seen (chapters/description) for splitting

    def progress_hook(self, d):
        """Handle download progress updates"""
        if d["status"] == "downloading":
            # Update current file info
            if "filename" in d and d["filename"] != self.current_file:
                self.current_file = d["filename"]
                filename = os.path.basename(d["filename"])
                current_download["current_file"] = filename
                current_download["message"] = f"Downloading: {filename}"
                # Track duration (seconds) for the Length column, when available
                info_dict = d.get("info_dict") or {}
                current_download["duration"] = info_dict.get("duration")
            
            # Calculate download progress with graceful fallbacks:
            #   1. exact/estimated byte totals (most common)
            #   2. fragment counts (DASH/HLS streams that report no byte total)
            downloaded_bytes = d.get("downloaded_bytes", 0)
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            frag_index = d.get("fragment_index") or 0
            frag_count = d.get("fragment_count") or 0
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)

            if total_bytes:
                progress = downloaded_bytes / total_bytes * 100
            elif frag_count:
                progress = frag_index / frag_count * 100
            else:
                progress = 0

            # Always provide consistent progress data
            current_download.update({
                'status': 'downloading',
                'downloaded_bytes': downloaded_bytes,
                'total_bytes': total_bytes,
                'fragment_index': frag_index,
                'fragment_count': frag_count,
                'speed': speed,
                'eta': eta,
                'progress': progress
            })
            
            if is_cancel_requested():
                current_download["status"] = "cancelled"
                current_download["message"] = "Download cancelled by user"
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user")
        
        elif d['status'] == 'finished':
            self.completed_files += 1
            info_dict = d.get("info_dict") or {}
            self.info = info_dict or self.info
            current_download.update({
                'status': 'processing',
                'completed_files': self.completed_files,
                'progress': 100,
                'duration': info_dict.get("duration"),
                'message': f"Processing {os.path.basename(d['filename'])}..."
            })
            
            # Update total progress for playlist
            if self.total_files > 1:
                current_download['total_progress'] = min((self.completed_files * 100) / self.total_files, 100)
            
            # Check if this was the last file
            if self.completed_files >= self.total_files:
                current_download.update({
                    'status': 'completed',
                    'total_progress': 100,
                    'message': 'Download completed successfully!'
                })
        
        elif d['status'] == 'error':
            current_download.update({
                'status': 'error',
                'message': f"Error: {d.get('error', 'Unknown error')}"
            })


def download_media(url, output_dir, download_type='audio', playlist_mode='single',
                   skip_long=False, limit=0, split_chapters=False):
    """Download media from YouTube"""
    reset_cancel()

    current_download['status'] = 'starting'
    # Keep progress property for compatibility but we don't update it anymore
    current_download['progress'] = 0
    current_download['total_progress'] = 0
    current_download['completed_files'] = 0
    current_download['message'] = 'Preparing download...'
    current_download['current_file'] = ''
    
    # Get video info to check if it's a playlist
    info = get_video_info(url)
    current_download['is_playlist'] = info['is_playlist']
    current_download['output_path'] = output_dir

    # Enrich the most recent links-history entry with the resolved title
    from modules.config.settings import update_last_link_history
    update_last_link_history(title=info.get('title'))
    
    if info['is_playlist']:
        current_download['playlist_title'] = info['title']
        current_download['total_files'] = info.get('entries', 1)
    else:
        current_download['playlist_title'] = ''
        current_download['total_files'] = 1

    # Limit a playlist download to the top N items if requested
    if info['is_playlist'] and playlist_mode == 'playlist' and limit and limit > 0:
        current_download['total_files'] = min(current_download['total_files'], limit)
    
    # If it's a playlist but user selected single video, modify URL
    if info['is_playlist'] and playlist_mode == 'single':
        # If we have a specific video URL, use it
        if 'video_url' in info:
            url = info['video_url']
        else:
            # Extract the first video from the playlist
            url = url.split('&list=')[0] if '&list=' in url else url
        
        current_download['is_playlist'] = False
        current_download['total_files'] = 1
    
    # Create a directory for playlist if needed
    if info['is_playlist'] and playlist_mode == 'playlist':
        playlist_name = sanitize_filename(info['title'])
        output_dir = os.path.join(output_dir, f"{playlist_name}_playlist")
        os.makedirs(output_dir, exist_ok=True)
    
    progress_tracker = DownloadProgress(current_download['total_files'])
    
    # Create a sanitize filename post-processor
    class SanitizeFilenamePP(yt_dlp.postprocessor.PostProcessor):
        def run(self, info):
            if 'filepath' in info:
                path_dir, path_file = os.path.split(info['filepath'])
                sanitized_file = sanitize_filename(path_file)
                new_path = os.path.join(path_dir, sanitized_file)
                
                if info['filepath'] != new_path:
                    try:
                        os.rename(info['filepath'], new_path)
                        info['filepath'] = new_path
                        
                        # Update the filename in the info dictionary
                        if 'filename' in info:
                            info['filename'] = new_path
                    except Exception as e:
                        print(f"Error renaming file: {e}")
            
            return [info], None
    
    # Setup common yt-dlp options
    ydl_opts = {
        'restrictfilenames': False,  # Don't restrict filenames - we'll sanitize them ourselves
        'progress_hooks': [progress_tracker.progress_hook],
        'ignoreerrors': True,
        'no_warnings': True,
        'geo_bypass': True,
        'extractor_retries': 5,
    }

    # Optional filter: skip any track longer than 7 minutes (playlists)
    if skip_long:
        def _skip_long_filter(info_dict, *, incomplete=False):
            dur = info_dict.get('duration')
            if dur is not None and dur > 420:
                return f"Skipping long file (>7 min): {info_dict.get('title', '')}"
            return None
        ydl_opts['match_filter'] = _skip_long_filter

    # Limit a playlist to the top N items (yt-dlp downloads items 1..N)
    if info['is_playlist'] and playlist_mode == 'playlist' and limit and limit > 0:
        ydl_opts['playlistend'] = limit


    if download_type == 'audio':
        # For audio, set specific options to only download and process audio
        audio_output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
        ydl_opts.update({
            'outtmpl': audio_output_template,
            'format': 'bestaudio',  # Only select audio streams
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'keepvideo': False,  # Important: Don't keep the video file after extraction
        })
    else:  # video
        # For video, set specific options to download video
        video_output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
        ydl_opts.update({
            'outtmpl': video_output_template,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        })
    
    # IMPORTANT FIX: For playlists, we need to ensure we're using the correct URL format
    if info['is_playlist'] and playlist_mode == 'playlist':
        # Remove noplaylist option which may cause issues
        if 'noplaylist' in ydl_opts:
            del ydl_opts['noplaylist']
        
        # Add the yes-playlist option to ensure all videos are downloaded
        ydl_opts['noplaylist'] = False
        
        # If we have a playlist URL but it's not in the correct format, fix it
        if 'playlist_url' in info:
            url = info['playlist_url']
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Add sanitize filename post-processor
            ydl.add_post_processor(SanitizeFilenamePP())
            
            # Start the download
            ydl.download([url])
        
        # Final pass to sanitize all filenames in the output directory
        for filename in os.listdir(output_dir):
            filepath = os.path.join(output_dir, filename)
            if os.path.isfile(filepath):
                sanitized = sanitize_filename(filename)
                if filename != sanitized:
                    try:
                        sanitized_path = os.path.join(output_dir, sanitized)
                        if not os.path.exists(sanitized_path):  # Avoid overwriting existing files
                            os.rename(filepath, sanitized_path)
                    except Exception as e:
                        print(f"Error renaming {filename}: {e}")
        
        # If status is still not completed (due to errors), try alternative method
        if current_download['status'] != 'completed':
            # If we're missing files or there was an error code, try alternative method
            current_download['message'] = 'Trying alternative download method...'
            
            # Modify options for alternative method
            if download_type == 'audio':
                ydl_opts.update({
                    'extractor_args': {'youtube': {'player_client': ['android']}},
                })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Add sanitize filename post-processor
                ydl.add_post_processor(SanitizeFilenamePP())
                
                # Try the download again
                ydl.download([url])
            
            # If status is not already set to completed by the progress hook, handle any errors
            if current_download['status'] != 'completed':
                # Check if we had partial success (some files downloaded)
                actual_count = current_download['completed_files']
                expected_count = current_download['total_files']
                
                if actual_count < expected_count and info['is_playlist']:
                    current_download['status'] = 'completed_with_errors'
                    current_download['message'] = f'Download incomplete. Only {actual_count} of {expected_count} files were downloaded.'
                else:
                    current_download['status'] = 'completed_with_errors'
                    current_download['message'] = 'Download completed with some errors or skipped files.'
            
            # Final filename sanitization for alternative method
            for filename in os.listdir(output_dir):
                filepath = os.path.join(output_dir, filename)
                if os.path.isfile(filepath):
                    sanitized = sanitize_filename(filename)
                    if filename != sanitized:
                        try:
                            sanitized_path = os.path.join(output_dir, sanitized)
                            if not os.path.exists(sanitized_path):  # Avoid overwriting existing files
                                os.rename(filepath, sanitized_path)
                        except Exception as e:
                            print(f"Error renaming {filename}: {e}")
        
        # Add to download history
        download_history.append({
            'url': url,
            'output_dir': output_dir,
            'download_type': download_type,
            'is_playlist': info['is_playlist'],
            'title': info.get('title', 'Unknown'),
            'status': current_download['status']
        })
        # Save history to persistent storage
        from modules.config.settings import save_download_history
        save_download_history()

        # Optional: split a single downloaded video into per-track files
        if split_chapters and playlist_mode != 'playlist':
            try:
                _split_into_tracks(output_dir, progress_tracker.info, info.get('title'))
            except Exception as e:
                print(f"Chapter split error: {e}")

    except yt_dlp.utils.DownloadCancelled:
        # User cancelled mid-download: report it as cancelled, not an error,
        # and skip the alternative-method retry.
        current_download['status'] = 'cancelled'
        current_download['message'] = 'Download cancelled by user'
    except Exception as e:
        current_download['status'] = 'error'
        current_download['message'] = f'Error: {str(e)}'

    # Record the final outcome against the links-history entry (all exit paths).
    update_last_link_history(status=current_download['status'])


def _split_into_tracks(output_dir, meta, fallback_title):
    """Split the just-downloaded single file into per-track files via chapters/tracklist."""
    from modules.download.chapters import chapter_segments, split_file, MEDIA_EXTS
    meta = meta or {}
    segments = chapter_segments(meta, meta.get('duration'))
    if not segments:
        current_download['message'] = 'No chapters/tracklist found to split'
        return
    # Find the file we just downloaded (newest top-level media file)
    cands = [os.path.join(output_dir, f) for f in os.listdir(output_dir)
             if os.path.isfile(os.path.join(output_dir, f))
             and os.path.splitext(f)[1].lower() in MEDIA_EXTS]
    if not cands:
        return
    src = max(cands, key=os.path.getmtime)
    title = meta.get('title') or fallback_title or 'video'
    tracks_dir = os.path.join(output_dir, (sanitize_filename(title) or 'tracks') + '_playlist')
    current_download['message'] = 'Splitting into tracks…'
    res = split_file(src, segments, tracks_dir, title)
    if res.get('tracks'):
        current_download['message'] = f"Split into {res['tracks']} tracks"
        try:
            os.remove(src)  # keep only the split tracks
        except OSError:
            pass


def start_download_thread(url, output_dir, download_type='audio', playlist_mode='single',
                          skip_long=False, limit=0, split_chapters=False):
    """Start the download process in a separate thread"""
    download_thread = threading.Thread(
        target=download_media,
        args=(url, output_dir, download_type, playlist_mode, skip_long, limit, split_chapters)
    )
    download_thread.daemon = True
    download_thread.start()
    return download_thread
