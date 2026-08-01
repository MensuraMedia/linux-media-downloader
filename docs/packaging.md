# Packaging & Distribution Guide

How to turn Linux Media Downloader into an installable desktop application for **Linux**
and **Windows**. Grounded in the current repo (there is already a partial `AppDir/` AppImage
scaffold and a `.desktop` file).

---

## 0. It is already a desktop app

`app.py` runs the UI in a **native PyWebView window** — that is the desktop application
(`browser_app.py` is the headless/browser fallback). "Packaging" is about letting people
**install and launch it** without manually installing Python and dependencies.

Every route below wraps the same two runtime needs:
- **Python 3.8+** with `Flask`, `yt-dlp`, `pywebview` (+ a PyWebView GUI backend:
  GTK/Qt/WebKit on Linux, EdgeWebView2 on Windows).
- **ffmpeg / ffprobe** on `PATH` — used for audio extraction, chapter splitting, and
  duration reads. **System-Python routes must declare it; self-contained routes must bundle it.**

---

## 1. Current scaffold & its gaps

```
AppDir/
├── usr/bin/…                 # a full copy of the app (kept in sync with the source)
└── usr/share/applications/linux-media-downloader.desktop
```

`linux-media-downloader.desktop`:
```ini
[Desktop Entry]
Name=Linux Media Downloader
Exec=python3 /usr/bin/app.py
Icon=linux-media-downloader
Type=Application
Categories=AudioVideo;Utility;
```

**Gaps to close before it builds:**
- No **`AppRun`** entry script (AppImage requires it).
- No **icon** file (`.desktop` references `linux-media-downloader` but none is shipped).
- `Exec=python3 /usr/bin/app.py` assumes a system Python and absolute path — won't work
  inside an AppImage sandbox; should call the bundled interpreter / `AppRun`.
- No **bundled Python or ffmpeg** — the AppImage would still depend on the host.
- Committed **`__pycache__`** under `AppDir/usr/bin/` should be removed and git-ignored.

---

## 2. Linux — routes by effort

### 2A. pipx / pip from git  ← simplest "install from git"

Add packaging metadata and a console entry point, then anyone installs with one line.

`pyproject.toml` (new):
```toml
[project]
name = "linux-media-downloader"
version = "1.0.0"
requires-python = ">=3.8"
dependencies = ["Flask", "yt-dlp", "pywebview"]

[project.scripts]
mbs = "app:main"        # `mbs` on PATH launches the native window

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

Install / run:
```bash
pipx install git+https://github.com/MensuraMedia/linux-media-downloader.git
mbs
```
- ✅ Trivial for the user; updates via `pipx upgrade`.
- ⚠️ Requires system Python, a PyWebView GUI backend, and **ffmpeg** (`sudo apt install ffmpeg`).
- Needs `MANIFEST.in`/package-data config so `templates/` and `static/` ship with the wheel
  (or move them under a package dir).

### 2B. AppImage  ← single portable download, no install

A one-file executable the user downloads, marks executable, and runs — the classic
"download from git Releases and run" experience.

Steps:
1. Fix the scaffold (§1): add `AppRun`, an icon (`linux-media-downloader.png` at AppDir root),
   correct the `.desktop` `Exec`.
2. Bundle Python + deps into `AppDir` (e.g. `linuxdeploy` + its `python` plugin — already
   named in `.gitignore`), and drop a **static ffmpeg** binary into `AppDir/usr/bin/`.
3. Build:
   ```bash
   ./linuxdeploy-x86_64.AppImage --appdir AppDir \
       --desktop-file AppDir/usr/share/applications/linux-media-downloader.desktop \
       --icon-file linux-media-downloader.png --output appimage
   ```
4. Ship `Linux_Media_Downloader-x86_64.AppImage` on the GitHub **Releases** page.

Minimal `AppRun`:
```bash
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"     # bundled ffmpeg
exec "$HERE/usr/bin/python3" "$HERE/usr/bin/app.py" "$@"
```
- ✅ No install, portable across distros; store in `~/Applications`.
- ⚠️ Largest artifact; must bundle a GUI/WebKit backend for PyWebView.

### 2C. .deb package  ← standard Debian/Ubuntu/Mint install

Native install that integrates into the app menu and declares dependencies.

Layout:
```
mbs_1.0.0/
├── DEBIAN/control          # Depends: python3, python3-flask, ffmpeg, gir1.2-webkit2-4.1
├── usr/lib/mbs/…           # the app
├── usr/bin/mbs             # launcher shim -> python3 /usr/lib/mbs/app.py
└── usr/share/applications/linux-media-downloader.desktop
```
Build: `dpkg-deb --build mbs_1.0.0` → `sudo apt install ./mbs_1.0.0.deb`.
- ✅ Feels native; `apt` resolves ffmpeg/webkit automatically.
- ⚠️ Debian-family only; `yt-dlp` from apt lags upstream — pin via pip in a venv or
  `Recommends` the pip install (yt-dlp changes fast; a stale one breaks downloads).

### 2D. Flatpak / Snap  ← sandboxed, cross-distro, auto-updating

A `flatpak` manifest or `snapcraft.yaml` builds a sandboxed bundle publishable to Flathub /
Snap Store with automatic updates. Most robust distribution, most build overhead; the sandbox
needs explicit filesystem permission for the user's download folder.

---

## 3. Windows

**PyInstaller** freezes the app into a standalone `.exe`:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "MediaBackupSystem" \
    --add-data "templates;templates" --add-data "static;static" \
    --add-binary "ffmpeg.exe;." app.py
```
- Produces `dist/MediaBackupSystem.exe` — no Python needed on the target.
- PyWebView uses the **Edge WebView2** runtime (present on Win10/11).
- Bundle `ffmpeg.exe` (via `--add-binary`) so splitting/extraction works offline.
- Optional: wrap with **Inno Setup** or **NSIS** for a Start-menu installer + uninstaller.
- `cx_Freeze` is an alternative if PyInstaller antivirus false-positives are a problem.

---

## 4. Recommendation

| Goal | Use |
|------|-----|
| Fastest "install from git" for technical users | **2A – pipx** |
| A downloadable file that "just runs" on any Linux | **2B – AppImage** (finish the scaffold) |
| Feels native on Ubuntu/Mint, menu integration | **2C – .deb** |
| Store presence + auto-updates | **2D – Flatpak** |
| Windows | **PyInstaller** (+ Inno Setup for an installer) |

A practical rollout: **pipx (2A)** first (cheapest, immediately usable), then **AppImage (2B)**
for a friendly Releases download, then **.deb (2C)** for Debian-family menus. All three can
publish from the same GitHub Releases page.

---

## 5. Cross-cutting checklist

- [ ] Bundle or declare **ffmpeg/ffprobe** (every route).
- [ ] Ship a **PyWebView GUI backend** (GTK/Qt/WebKit on Linux; WebView2 on Windows).
- [ ] Keep **`yt-dlp` current** — it breaks often against YouTube; prefer pip over distro pkgs,
      and consider a self-update or a "yt-dlp version" note in About.
- [ ] Anchor **runtime data** to a fixed app-data dir (`~/.local/share/linux-media-downloader`)
      instead of the cwd, so an installed app doesn't scatter `data/`, `downloads/` (already
      flagged in the roadmap).
- [ ] Add an **icon** asset; remove committed `__pycache__` from `AppDir/`.
- [ ] Automate builds in **GitHub Actions** → attach artifacts to Releases.
