#!/usr/bin/env python3
# modules/config/settings.py
# Configuration settings for YT Media Backup

import os

# App settings
# Prefer an externally provided key; fall back to a per-run random key.
# The app is localhost-only, but a hardcoded secret is still poor practice.
SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()

# Get the system's Downloads folder path
def get_downloads_folder():
    """Get the path to the user's Downloads folder"""
    # Try to use the XDG_DOWNLOAD_DIR environment variable first
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    xdg_user_dirs = os.path.join(xdg_config_home, 'user-dirs.dirs')
    
    if os.path.exists(xdg_user_dirs):
        with open(xdg_user_dirs, 'r') as f:
            for line in f:
                if line.startswith('XDG_DOWNLOAD_DIR'):
                    path = line.split('=')[1].strip().strip('"').replace('$HOME', os.path.expanduser('~'))
                    if os.path.exists(path):
                        return path
    
    # Fall back to ~/Downloads if it exists
    home_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
    if os.path.exists(home_downloads):
        return home_downloads
    
    # Last resort, use the current directory's downloads folder
    return os.path.join(os.getcwd(), 'downloads')

# Default download path
default_download_path = get_downloads_folder()

# Create necessary directories
os.makedirs('downloads', exist_ok=True)
os.makedirs('backups', exist_ok=True)

# Global state variables
download_history = []
current_download = {
    'output_path': '',
    'status': None, 
    'progress': 0,  # Individual file progress
    'total_progress': 0,  # Overall playlist progress
    'message': '',
    'current_file': '',
    'total_files': 0,
    'completed_files': 0,
    'is_playlist': False,
    'playlist_title': '',
    'selected_mode': 'single'
}

# Global control variables
download_thread = None
cancel_requested = False
window = None


# Cancellation helpers.
# `cancel_requested` is a module-level bool. Because other modules imported it
# by value (`from settings import cancel_requested`), reassigning it in one
# module never reached the others and cancellation silently did nothing.
# Routing all access through these functions keeps a single source of truth.
def request_cancel():
    """Signal the active download to stop."""
    global cancel_requested
    cancel_requested = True


def reset_cancel():
    """Clear the cancel flag before starting a new download."""
    global cancel_requested
    cancel_requested = False


def is_cancel_requested():
    """Return True if the user has requested cancellation."""
    return cancel_requested

# Import JSON module for history persistence
import json

# Path to store download history
HISTORY_FILE = os.path.join(os.getcwd(), 'data', 'download_history.json')

# Ensure data directory exists
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

# Function to save history (limited to 100 entries)
def save_download_history():
    """Save download history to JSON file, keeping only the 100 most recent entries"""
    global download_history
    # Limit to 100 most recent downloads
    if len(download_history) > 100:
        download_history = download_history[-100:]
    
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(download_history, f, indent=2)
    except Exception as e:
        print(f"Error saving download history: {e}")

# Function to load history
def load_download_history():
    """Load download history from JSON file"""
    global download_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                download_history = json.load(f)
        except Exception as e:
            print(f"Error loading download history: {e}")
            download_history = []
    else:
        download_history = []

# Load history when this module is imported
load_download_history()
