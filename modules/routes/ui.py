#!/usr/bin/env python3
# modules/routes/ui.py
# UI routes for YT Media Backup

from flask import Blueprint, render_template
from modules.config.settings import download_history

# Create blueprint
ui_routes = Blueprint('ui_routes', __name__)

@ui_routes.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@ui_routes.route('/backups')
def backups():
    """Render the backups page"""
    return render_template('backups.html', download_history=download_history)

@ui_routes.route('/links')
def links():
    """Render the links history page"""
    return render_template('links.html')

@ui_routes.route('/information')
def information():
    """Render the information page"""
    return render_template('information.html')

@ui_routes.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')
