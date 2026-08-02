---
date: 2026-08-02
type: packaging
files_changed:
  - packaging/build-deb.sh (new)
  - .gitignore (build/ dist/)
  - docs/packaging.md, README.md, ROADMAP.md, changelog.md
---
## Change: .deb package builder

- `packaging/build-deb.sh` assembles a Debian package and builds it with `dpkg-deb`
  (fakeroot). Layout: app under `/opt/linux-media-downloader`, launcher
  `/usr/bin/linux-media-downloader` (runs app.py but sets cwd to
  `~/.local/share/linux-media-downloader` so downloads/history stay user-writable),
  `.desktop` menu entry + hicolor svg icon.
- `control` Depends: python3(>=3.8), python3-venv, python3-pip, ffmpeg, python3-gi,
  python3-gi-cairo, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0 (Architecture: all).
- `postinst` builds a venv (`--system-site-packages` for PyGObject/WebKit) and pip-installs
  Flask/yt-dlp/pywebview (keeps yt-dlp current). `prerm` removes the venv.
- Output `dist/linux-media-downloader_1.0.0_all.deb`; `build/` + `dist/` git-ignored
  (binaries belong on GitHub Releases).

### Verification
- Built locally with dpkg-deb 1.22.6: 67 KB, control metadata correct, all files present
  (/opt app, launcher, .desktop, icon, postinst, prerm). Packaged `.desktop` passes
  desktop-file-validate. Not installed here (needs apt/root); the build itself is verified.

### Next (offered, not yet done)
- GitHub Actions to build the .deb (and AppImage) and attach to Releases.
- `pyproject.toml` for pipx; Windows PyInstaller .exe.
