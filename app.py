#!/usr/bin/env python3
# app.py
# Main application file for YT Media Backup

import os
import threading
import atexit
import logging

# WebKit2GTK's DMABUF renderer crashes on many Linux setups (VMs, some GPU
# drivers, sandboxes), which makes the PyWebView window open and then immediately
# close. Disabling it before WebKit initialises is the standard fix. Set this
# only if the user hasn't already chosen a value.
os.environ.setdefault('WEBKIT_DISABLE_DMABUF_RENDERER', '1')

# Configure logging before anything else so import-time messages are captured.
from modules.config.logging_config import setup_logging
setup_logging()
logger = logging.getLogger('lmd.app')

# The desktop environment matches a window's WM_CLASS against the launcher's
# StartupWMClass to attach the right icon and group windows in the taskbar.
# Left alone, GTK derives WM_CLASS from the script name ("app.py" / "App.py"),
# which matches nothing in linux-media-downloader.desktop, so the running window
# shows a generic icon and cannot be pinned. Setting the program name fixes it,
# and must happen before the GTK/WebKit backend initialises. GDK derives both
# WM_CLASS fields from it, giving a stable
# ("linux-media-downloader", "Linux-media-downloader") that the launcher's
# StartupWMClass=linux-media-downloader matches on the first field.
try:
    from gi.repository import GLib
    GLib.set_prgname('linux-media-downloader')
except Exception:
    # Non-GTK backend or gi unavailable — window identity is cosmetic, so this
    # must never stop the app from starting.
    logger.debug('Could not set the GTK program name', exc_info=True)

import webview
from flask import Flask
from werkzeug.serving import make_server

# Import modules
from modules.routes.ui import ui_routes
from modules.routes.api import api_routes
from modules.config.settings import SECRET_KEY, window

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = SECRET_KEY

# Register blueprints
app.register_blueprint(ui_routes)
app.register_blueprint(api_routes)

# Main function to start the application
# Function to clean up when application exits
def cleanup():
    # Save any pending download history
    from modules.config.settings import save_download_history
    save_download_history()

# Register the cleanup function
atexit.register(cleanup)

def main():
    logger.info('Starting Linux Media Downloader (desktop mode)')
    # make_server() binds and starts listening synchronously, so the port is open
    # the instant it returns — no need to sleep before opening the window.
    server = make_server('127.0.0.1', 0, app)
    port = server.server_port
    app.config['SERVER_PORT'] = port
    logger.info('Flask server listening on http://127.0.0.1:%s', port)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Start the PyWebView window
    global window
    window = webview.create_window(
        'SilverMax',
        f'http://127.0.0.1:{port}',
        width=1000, 
        height=700,
        min_size=(800, 600)
    )
    webview.start()

if __name__ == '__main__':
    main()
