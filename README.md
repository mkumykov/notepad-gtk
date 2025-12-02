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

## Desktop launcher

The repository now includes a `notepad.desktop` file that you can install to make the app available from your desktop environment's application menu.

To install for the current user (recommended):

```bash
# copy to local applications
mkdir -p ~/.local/share/applications
cp notepad.desktop ~/.local/share/applications/
# make the script executable and ensure Exec points to the correct path
chmod +x notepad.py
# If the launcher doesn't start the app, edit the copied file and set `Exec` to the full path:
# Exec=/home/<you>/workspace/notepad/notepad.py %f
```

To install system-wide (requires root):

```bash
sudo cp notepad.desktop /usr/share/applications/
sudo chmod 644 /usr/share/applications/notepad.desktop
```

After installing, the launcher should appear in your desktop environment's app menu. You can also drag it to your favorites or create a shortcut.
