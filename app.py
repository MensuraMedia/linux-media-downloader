#!/usr/bin/env python3
# app.py
# Main application file for YT Media Backup

import time
import threading
import atexit
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

# Function to start the Flask server
def start_server():
    server = make_server('127.0.0.1', 0, app)
    port = server.server_port
    app.config['SERVER_PORT'] = port
    server.serve_forever()

# Main function to start the application
# Function to clean up when application exits
def cleanup():
    # Save any pending download history
    from modules.config.settings import save_download_history
    save_download_history()

# Register the cleanup function
atexit.register(cleanup)

def main():
    # Start Flask server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1)
    
    # Get the port Flask is running on
    port = app.config.get('SERVER_PORT', 5000)
    
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
