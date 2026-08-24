#!/usr/bin/env bash
#
# build-deb.sh — build a .deb package for Linux Media Downloader.
#
#   ./packaging/build-deb.sh
#
# Produces dist/linux-media-downloader_<version>_all.deb
#
# The package installs the app under /opt/linux-media-downloader, adds a launcher
# (/usr/bin/linux-media-downloader), a menu entry and icon. yt-dlp/Flask/pywebview
# are installed into a venv by the postinst (they're not reliably in apt / change
# often), reusing the system PyGObject/WebKit backend via --system-site-packages.
#
set -euo pipefail

PKG="linux-media-downloader"
VERSION="1.0.0"
ARCH="all"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$REPO_DIR/build/deb"
ROOT="$BUILD_DIR/$PKG"
APP_DIR="$ROOT/opt/$PKG"
DIST="$REPO_DIR/dist"

echo "==> Cleaning build tree"
rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR" "$ROOT/DEBIAN" "$ROOT/usr/bin" \
         "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/icons/hicolor/scalable/apps" "$DIST"

echo "==> Copying application files"
for item in app.py browser_app.py requirements.txt requirements-dev.txt LICENSE \
            README.md DOCUMENTATION.md INSTALL.md ROADMAP.md modules templates static; do
    [ -e "$REPO_DIR/$item" ] && cp -r "$REPO_DIR/$item" "$APP_DIR/"
done
# Strip caches
find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$APP_DIR" -name '*.pyc' -delete

echo "==> Installed size"
INSTALLED_KB=$(du -sk "$APP_DIR" | cut -f1)

echo "==> Writing DEBIAN/control"
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: sound
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.8), python3-venv, python3-pip, ffmpeg, python3-gi, python3-gi-cairo, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0
Installed-Size: $INSTALLED_KB
Maintainer: MensuraMedia <mensuramedia@gmail.com>
Homepage: https://github.com/MensuraMedia/linux-media-downloader
Description: Desktop YouTube media downloader (audio/video, playlists)
 A localhost desktop app to download and back up YouTube media for personal use.
 Audio (MP3) or video (MP4), single tracks or whole playlists, with a download
 queue, playlist/file managers, a built-in player, chapter splitting, and
 duplicate skipping. Runs in its own native window (PyWebView).
EOF

echo "==> Writing launcher"
cat > "$ROOT/usr/bin/$PKG" <<'EOF'
#!/bin/bash
# Launch Linux Media Downloader in its own window. Runs the code from /opt but
# keeps user data (downloads, history) under the user's data directory.
APP="/opt/linux-media-downloader"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/linux-media-downloader"
mkdir -p "$DATA"
cd "$DATA"
exec "$APP/venv/bin/python" "$APP/app.py" "$@"
EOF
chmod 755 "$ROOT/usr/bin/$PKG"

echo "==> Menu entry + icon"
cp "$SCRIPT_DIR/$PKG.svg" "$ROOT/usr/share/icons/hicolor/scalable/apps/$PKG.svg"
cat > "$ROOT/usr/share/applications/$PKG.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Linux Media Downloader
Comment=Download and back up YouTube media (audio/video, playlists)
Exec=$PKG
Icon=$PKG
Terminal=false
Categories=AudioVideo;Recorder;
Keywords=youtube;download;media;music;video;backup;
StartupWMClass=$PKG
EOF

echo "==> postinst (build venv, install Python deps)"
cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
APP="/opt/linux-media-downloader"
echo "Setting up Python environment for Linux Media Downloader…"
python3 -m venv --system-site-packages "$APP/venv"
"$APP/venv/bin/pip" install --quiet --upgrade pip || true
"$APP/venv/bin/pip" install --quiet -r "$APP/requirements.txt"
# Refresh desktop database / icon cache (best effort)
command -v update-desktop-database >/dev/null && update-desktop-database -q || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
echo "Linux Media Downloader installed. Launch it from your application menu."
exit 0
EOF
chmod 755 "$ROOT/DEBIAN/postinst"

echo "==> prerm (remove the venv created at install time)"
cat > "$ROOT/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e
rm -rf /opt/linux-media-downloader/venv || true
exit 0
EOF
chmod 755 "$ROOT/DEBIAN/prerm"

echo "==> Building package"
OUT="$DIST/${PKG}_${VERSION}_${ARCH}.deb"
if command -v fakeroot >/dev/null; then
    fakeroot dpkg-deb --build "$ROOT" "$OUT"
else
    dpkg-deb --build "$ROOT" "$OUT"
fi

echo
echo "✅ Built: $OUT"
echo "   Install with:  sudo apt install $OUT"
echo "   (or: sudo dpkg -i $OUT && sudo apt-get -f install)"
