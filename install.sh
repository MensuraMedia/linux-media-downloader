#!/usr/bin/env bash
#
# Linux Media Downloader — one-command installer for Debian / Ubuntu / Linux Mint.
#
#   curl -fsSL https://raw.githubusercontent.com/MensuraMedia/linux-media-downloader/main/install.sh | bash
#
# Installs system deps (Python, ffmpeg, WebKit GUI backend), clones the repo,
# sets up a virtualenv, and adds the app to your program menu with its icon.
# Re-runnable (updates an existing install). Uninstall: install.sh --uninstall
#
set -euo pipefail

REPO_URL="https://github.com/MensuraMedia/linux-media-downloader.git"
INSTALL_DIR="${LMD_DIR:-$HOME/.local/share/linux-media-downloader}"
APP_NAME="Linux Media Downloader"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

# ── Uninstall ─────────────────────────────────────────────────────────────────
if [ "${1:-}" = "--uninstall" ]; then
    say "Removing menu entry…"
    [ -x "$INSTALL_DIR/packaging/install-menu.sh" ] && \
        "$INSTALL_DIR/packaging/install-menu.sh" --uninstall || true
    say "Deleting $INSTALL_DIR …"
    rm -rf "$INSTALL_DIR"
    say "Uninstalled. (Your downloads were not touched.)"
    exit 0
fi

# ── Preconditions ─────────────────────────────────────────────────────────────
command -v apt-get >/dev/null || die "This installer targets Debian/Ubuntu/Mint (apt-get not found). See INSTALL.md for other distros."
SUDO=""
if [ "$(id -u)" -ne 0 ]; then command -v sudo >/dev/null && SUDO="sudo" || die "Need root or sudo to install system packages."; fi

# ── 1. System dependencies ────────────────────────────────────────────────────
say "Installing system dependencies (may prompt for your password)…"
$SUDO apt-get update -qq
# WebKit backend package name varies by release; try 4.1 then fall back to 4.0.
WEBKIT="gir1.2-webkit2-4.1"
apt-cache show "$WEBKIT" >/dev/null 2>&1 || WEBKIT="gir1.2-webkit2-4.0"
$SUDO apt-get install -y --no-install-recommends \
    git python3 python3-venv python3-pip ffmpeg \
    python3-gi python3-gi-cairo "$WEBKIT" libgirepository1.0-dev

# ── 2. Get / update the code ──────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    say "Updating existing install at $INSTALL_DIR …"
    git -C "$INSTALL_DIR" pull --ff-only || say "(could not fast-forward; keeping current code)"
else
    say "Cloning into $INSTALL_DIR …"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

# ── 3. Python virtualenv + deps ───────────────────────────────────────────────
say "Setting up the Python environment…"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

# ── 4. Program-menu entry + icon ──────────────────────────────────────────────
say "Adding '$APP_NAME' to your program menu…"
chmod +x "$INSTALL_DIR/packaging/install-menu.sh"
"$INSTALL_DIR/packaging/install-menu.sh"

# ── Done ──────────────────────────────────────────────────────────────────────
cat <<EOF

✅ Installed $APP_NAME.

  • Launch it from your application menu (search "$APP_NAME"), or run:
        $INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
  • Update later:   bash $INSTALL_DIR/install.sh
  • Uninstall:      bash $INSTALL_DIR/install.sh --uninstall

Downloads default to your ~/Downloads folder. Enjoy!
EOF
