# Postmortem — "Menu icon launches, no window appears"

**Date:** 2026-08-04
**Component:** Desktop launch path (`install.sh` → venv → `app.py` → PyWebView/WebKit2GTK)
**Severity:** High (app 100% unusable from the program menu; browser mode unaffected)
**Status:** Resolved
**Platform observed:** Linux Mint / Ubuntu 22.04 base, Python 3.10.12, X11

---

## 1. Symptom

The user installed the app via `install.sh`, saw "Linux Media Downloader" in the
Mint application menu with its icon, but **clicking it did nothing** — no window,
no error dialog, no visible process. Launching from a terminal was never attempted
by the user, so the failure was completely silent.

This is the classic "GUI app dies before it can draw" signature: the launcher
succeeds in starting a process, the process raises an unhandled exception within
about a second, and because `Terminal=false` in the `.desktop` file there is
nowhere for the traceback to go.

## 2. Reproduction

Run the launcher's exact command by hand to surface the hidden output:

```bash
/home/user/.local/share/linux-media-downloader/venv/bin/python \
  /home/user/.local/share/linux-media-downloader/app.py
```

Output:

```
[pywebview] GTK cannot be loaded
ModuleNotFoundError: No module named 'gi'
[pywebview] QT cannot be loaded
ModuleNotFoundError: No module named 'qtpy'
webview.errors.WebViewException: You must have either QT or GTK with
Python extensions installed in order to use pywebview.
```

The process exits non-zero in <1s. That matches the symptom exactly.

## 3. Root cause

**PyWebView had no GUI backend available inside the virtual environment.**

PyWebView is only a thin abstraction; it needs a real native webview toolkit:

- **GTK path** — needs `PyGObject` (the `gi` module) **and** WebKit2GTK typelibs.
- **Qt path** — needs `qtpy` + PyQt/PySide.

On Debian/Ubuntu/Mint, `PyGObject` and WebKit2GTK are **distribution (apt)
packages** — `python3-gi`, `python3-gi-cairo`, `gir1.2-webkit2-4.1`. They are
compiled against the system Python and are effectively **not pip-installable** into
an isolated venv (PyGObject needs GObject-introspection dev headers and a build
toolchain, and even then WebKit2 typelibs live in system paths).

The installer created the venv **without** `--system-site-packages`:

```
# venv/pyvenv.cfg
include-system-site-packages = false      # <-- the bug
```

So although the host had every required apt package installed (verified:
`python3-gi 3.42.1`, `gir1.2-webkit2-4.1 2.50.4`, `gir1.2-gtk-3.0`), the venv was
walled off from them. `import gi` failed, the GTK backend was skipped, the Qt
backend was absent too, and `webview.start()` raised `WebViewException`.

**Key fact that makes the fix safe:** the venv's interpreter and the system
interpreter are the *same build* — Python `3.10.12` in both. System site-packages
are therefore ABI-compatible; exposing them to the venv cannot cause a version/ABI
mismatch.

### Contributing cause (secondary)

Even once a backend loads, WebKit2GTK's **DMABUF renderer** crashes on many VMs and
GPU-driver combinations, producing a *different* "window opens then instantly
closes" failure. The installed `app.py` predated the fix for this and did not
disable it.

## 4. The fix

Two changes, both minimal and reversible.

### 4.1 Let the venv see system GTK/WebKit (primary)

`venv/pyvenv.cfg`:

```diff
-include-system-site-packages = false
+include-system-site-packages = true
```

And in `install.sh`, create the venv correctly from the start:

```diff
-python3 -m venv "$INSTALL_DIR/venv"
+python3 -m venv --system-site-packages "$INSTALL_DIR/venv"
```

An install-time sanity check now imports `gi` + `WebKit2` and **fails loudly** if
the backend is missing, so a broken environment is caught at install time rather
than silently at launch.

### 4.2 Disable the DMABUF renderer (defense-in-depth)

Top of `app.py`, before `import webview`:

```python
import os
# WebKit2GTK's DMABUF renderer crashes on many Linux setups (VMs, some GPU
# drivers, sandboxes), making the window open then immediately close.
os.environ.setdefault('WEBKIT_DISABLE_DMABUF_RENDERER', '1')
```

`setdefault` means an advanced user can still override it.

## 5. Verification

| Check | Before | After |
|-------|--------|-------|
| `venv/bin/python -c "import gi; from gi.repository import WebKit2"` | `ModuleNotFoundError` | OK |
| `venv/bin/python app.py` (no env overrides) | exits 1, traceback in <1s | stays running in window loop |
| Flask + yt-dlp import inside venv | OK | OK (unaffected) |

`app.py` launched with a 10s timeout and had to be *killed* (exit 124) — i.e. it
stayed alive in the event loop instead of crashing. That is the pass condition for
a GUI process under a headless timeout harness.

## 6. Prevention

- **Installer** now uses `--system-site-packages` and verifies the backend before
  reporting success (`install.sh`).
- **App** disables the DMABUF renderer by default (`app.py`).
- **Docs** — `INSTALL.md` / README call out the apt GUI dependencies explicitly.
- **Future guard idea:** wrap `webview.start()` so a `WebViewException` prints a
  one-line remediation hint to `logs/app.log` and, when interactive, stderr —
  turning a silent death into an actionable message.

---

## 7. Review analysis — how this reached a user

A short "five whys" on why a launch-blocking defect shipped:

1. **Why did the window never appear?** PyWebView found no GUI backend → uncaught
   `WebViewException`.
2. **Why no backend?** The venv could not import system `PyGObject`/WebKit2.
3. **Why not?** The venv was created without `--system-site-packages`, and those
   libraries are apt-only, not in `requirements.txt`.
4. **Why wasn't it caught before release?** The app was almost certainly developed
   and tested from a shell where the traceback *was* visible, and/or with system
   site-packages reachable (running `python3 app.py` directly rather than through
   the isolated venv). The **isolated-venv + no-terminal** launch path — the one
   real users hit — was never exercised end to end.
5. **Why was the failure invisible?** `Terminal=false` in the `.desktop` entry
   discards stdout/stderr, so the only diagnostic signal was suppressed.

**Themes:**

- **Environment parity gap.** "Works when I run it" ≠ "works from the menu." The
  developer environment (system Python, terminal attached) differed from the
  delivered environment (isolated venv, detached GUI launch) in exactly the two
  dimensions that hid the bug.
- **Native GUI deps don't fit the pip/venv model.** Any PyWebView/PyGObject/PyQt
  desktop app on Debian-family distros must either (a) use
  `--system-site-packages`, or (b) `apt install` the GUI stack and run under system
  Python. Treating them like ordinary pip dependencies guarantees this failure.
- **Silent launchers hide crashes.** `Terminal=false` is correct for a shipped app
  but means the app itself must surface fatal errors (log file + user-visible
  dialog); it cannot rely on the console.

**Cheapest control that would have caught it:** the install-time backend import
check added in §4.1 — three lines that convert a silent runtime death into a loud,
specific install-time error.
