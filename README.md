# Notepad (GTK) — simple text editor

This is a small Notepad-like text editor implemented in Python using GTK3 (PyGObject). It provides basic functionality: New/Open/Save, cut/copy/paste, undo/redo (snapshot-based), word wrap toggle, Find/Replace, and a statusbar showing line/column.

## Requirements

- Python 3
- PyGObject (GTK3)

On Debian/Ubuntu install runtime deps:

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

On Fedora:

```bash
sudo dnf install python3-gobject gtk3
```

Or install PyGObject via pip in environments where available (not recommended over distro packages):

```bash
pip install PyGObject
```

## Run

```bash
python3 ~/workspace/notepad/notepad.py
```

## Files

- `~/workspace/notepad/notepad.py` — main application
- `~/workspace/notepad/requirements.txt` — pip-style requirements placeholder

Repository: https://github.com/mkumykov/notepad-gtk

Continuous integration: a simple GitHub Action checks Python syntax on push/pull requests.

## Notes

- Undo/Redo is implemented using periodic snapshots to keep implementation small and avoid external dependencies. It works well for normal typing but is not a fine-grained operation history.
- This is intentionally minimal; you can extend it with syntax highlighting (for example using `GtkSourceView`), preferences, or packaging helpers.

If you want, I can add a `.desktop` file, packaging instructions, or port the app to GTK4.
