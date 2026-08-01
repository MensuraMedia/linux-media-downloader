#!/usr/bin/env python3
# modules/routes/ui.py
# UI routes for YT Media Backup

from flask import Blueprint, render_template
from modules.config import settings

# Create blueprint
ui_routes = Blueprint('ui_routes', __name__)

@ui_routes.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@ui_routes.route('/backups')
def backups():
    """Render the backups page, newest download first (descending by time)."""
    hist = settings.download_history
    # Sort descending by timestamp; append-index as tiebreaker so entries without
    # a timestamp (legacy) keep newest-appended-first order.
    order = sorted(range(len(hist)),
                   key=lambda i: (hist[i].get('timestamp', ''), i),
                   reverse=True)
    ordered = [hist[i] for i in order]
    return render_template('backups.html', download_history=ordered)

@ui_routes.route('/links')
def links():
    """Render the links history page"""
    return render_template('links.html')

@ui_routes.route('/playlists')
def playlists():
    """Render the playlists management page"""
    return render_template('playlists.html')

@ui_routes.route('/player')
def player():
    """Render the media player / curation page"""
    return render_template('player.html')

@ui_routes.route('/file-manager')
def file_manager():
    """Render the file manager page"""
    return render_template('file-manager.html')

@ui_routes.route('/information')
def information():
    """Render the information page"""
    return render_template('information.html')

@ui_routes.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')
