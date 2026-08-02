#!/bin/bash
#
# install-menu.sh — add Linux Media Downloader to the application menu
# (Linux Mint / Cinnamon, GNOME, XFCE — any XDG-compliant desktop).
#
# Per-user install (no root). Points the launcher at THIS checkout and uses a
# local venv's python if one exists, otherwise system python3.
#
# Usage:   ./packaging/install-menu.sh
# Remove:  ./packaging/install-menu.sh --uninstall

set -euo pipefail

APP_ID="linux-media-downloader"
APP_NAME="Linux Media Downloader"

# Repo root = parent of this script's directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
DESKTOP_FILE="$DESKTOP_DIR/$APP_ID.desktop"
ICON_FILE="$ICON_DIR/$APP_ID.svg"

if [ "${1:-}" = "--uninstall" ]; then
    rm -fv "$DESKTOP_FILE" "$ICON_FILE"
    command -v update-desktop-database >/dev/null && update-desktop-database "$DESKTOP_DIR" || true
    echo "Removed $APP_NAME from the application menu."
    exit 0
fi

# Choose the interpreter: prefer a project venv, else system python3
if [ -x "$REPO_DIR/venv/bin/python" ]; then
    PYTHON="$REPO_DIR/venv/bin/python"
else
    PYTHON="$(command -v python3 || true)"
fi
[ -n "$PYTHON" ] || { echo "Error: python3 not found."; exit 1; }

mkdir -p "$DESKTOP_DIR" "$ICON_DIR"
cp "$SCRIPT_DIR/$APP_ID.svg" "$ICON_FILE"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Download and back up YouTube media (audio/video, playlists)
Exec=$PYTHON $REPO_DIR/app.py
Path=$REPO_DIR
Icon=$APP_ID
Terminal=false
Categories=AudioVideo;Recorder;
Keywords=youtube;download;media;music;video;backup;
StartupWMClass=$APP_NAME
EOF

chmod +x "$DESKTOP_FILE"
command -v update-desktop-database >/dev/null && update-desktop-database "$DESKTOP_DIR" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed '$APP_NAME' to the application menu."
echo "  launcher : $DESKTOP_FILE"
echo "  runs     : $PYTHON $REPO_DIR/app.py"
echo
echo "Search for '$APP_NAME' in the Mint menu (you may need to log out/in once,"
echo "or run 'cinnamon --replace' briefly, for it to appear)."
echo "Note: app.py needs a PyWebView GUI backend — see README Requirements."
