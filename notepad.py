#!/usr/bin/env python3
"""
Simple Notepad-like text editor using GTK3 (PyGObject).

Features:
- New / Open / Save / Save As
- Cut / Copy / Paste / Select All
- Basic Undo/Redo (snapshot-based)
- Word-wrap toggle
- Line/Column statusbar
- About dialog

Run: `python3 notepad.py`
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango
import os
import sys
import time


class NotepadWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Notepad - Untitled")
        self.set_default_size(800, 600)

        self.current_file = None
        self.dirty = False

        self.undo_stack = []
        self.redo_stack = []
        self._last_snapshot_time = 0
        self._snapshot_debounce = 0.8

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        menubar = self._create_menubar()
        vbox.pack_start(menubar, False, False, 0)

        self.toolbar = self._create_toolbar()
        vbox.pack_start(self.toolbar, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.textview.get_buffer()
        font_desc = Pango.FontDescription('Monospace 11')
        self.textview.modify_font(font_desc)

        scrolled.add(self.textview)
        vbox.pack_start(scrolled, True, True, 0)

        self.statusbar = Gtk.Statusbar()
        vbox.pack_end(self.statusbar, False, False, 0)
        self.status_ctx = self.statusbar.get_context_id('pos')

        self._create_accels()

        # Signals
        self.textbuffer.connect('changed', self.on_text_changed)
        self.textview.connect('move-cursor', self.on_cursor_moved)
        self.connect('delete-event', self.on_delete_event)

        # initial empty snapshot
        self._push_undo_snapshot()
        self.update_statusbar()

    def _create_menubar(self):
        menubar = Gtk.MenuBar()

        # File
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem.new_with_label('File')
        file_item.set_submenu(file_menu)

        new_item = Gtk.MenuItem.new_with_label('New')
        new_item.connect('activate', lambda w: self.new_file())
        file_menu.append(new_item)

        open_item = Gtk.MenuItem.new_with_label('Open...')
        open_item.connect('activate', lambda w: self.open_file())
        file_menu.append(open_item)

        save_item = Gtk.MenuItem.new_with_label('Save')
        save_item.connect('activate', lambda w: self.save_file())
        file_menu.append(save_item)

        saveas_item = Gtk.MenuItem.new_with_label('Save As...')
        saveas_item.connect('activate', lambda w: self.save_file_as())
        file_menu.append(saveas_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem.new_with_label('Quit')
        quit_item.connect('activate', lambda w: self.on_quit())
        file_menu.append(quit_item)

        menubar.append(file_item)

        # Edit
        edit_menu = Gtk.Menu()
        edit_item = Gtk.MenuItem.new_with_label('Edit')
        edit_item.set_submenu(edit_menu)

        undo_item = Gtk.MenuItem.new_with_label('Undo')
        undo_item.connect('activate', lambda w: self.undo())
        edit_menu.append(undo_item)

        redo_item = Gtk.MenuItem.new_with_label('Redo')
        redo_item.connect('activate', lambda w: self.redo())
        edit_menu.append(redo_item)

        edit_menu.append(Gtk.SeparatorMenuItem())

        cut_item = Gtk.MenuItem.new_with_label('Cut')
        cut_item.connect('activate', lambda w: self.textview.get_buffer().cut_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD), True))
        edit_menu.append(cut_item)

        copy_item = Gtk.MenuItem.new_with_label('Copy')
        copy_item.connect('activate', lambda w: self.textview.get_buffer().copy_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)))
        edit_menu.append(copy_item)

        paste_item = Gtk.MenuItem.new_with_label('Paste')
        paste_item.connect('activate', lambda w: self.textview.get_buffer().paste_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD), None, True))
        edit_menu.append(paste_item)

        selectall_item = Gtk.MenuItem.new_with_label('Select All')
        selectall_item.connect('activate', lambda w: self.select_all())
        edit_menu.append(selectall_item)

        find_item = Gtk.MenuItem.new_with_label('Find/Replace...')
        find_item.connect('activate', lambda w: self.show_find_dialog())
        edit_menu.append(find_item)

        menubar.append(edit_item)

        # View
        view_menu = Gtk.Menu()
        view_item = Gtk.MenuItem.new_with_label('View')
        view_item.set_submenu(view_menu)

        wrap_item = Gtk.CheckMenuItem.new_with_label('Word Wrap')
        wrap_item.set_active(True)
        wrap_item.connect('toggled', lambda w: self.toggle_wrap(w.get_active()))
        view_menu.append(wrap_item)

        menubar.append(view_item)

        # Help
        help_menu = Gtk.Menu()
        help_item = Gtk.MenuItem.new_with_label('Help')
        help_item.set_submenu(help_menu)

        about_item = Gtk.MenuItem.new_with_label('About')
        about_item.connect('activate', lambda w: self.show_about())
        help_menu.append(about_item)

        menubar.append(help_item)

        return menubar

    def _create_toolbar(self):
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)

        new_tb = Gtk.ToolButton.new_from_stock(Gtk.STOCK_NEW)
        new_tb.connect('clicked', lambda w: self.new_file())
        toolbar.insert(new_tb, -1)

        open_tb = Gtk.ToolButton.new_from_stock(Gtk.STOCK_OPEN)
        open_tb.connect('clicked', lambda w: self.open_file())
        toolbar.insert(open_tb, -1)

        save_tb = Gtk.ToolButton.new_from_stock(Gtk.STOCK_SAVE)
        save_tb.connect('clicked', lambda w: self.save_file())
        toolbar.insert(save_tb, -1)

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        cut_tb = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CUT)
        cut_tb.connect('clicked', lambda w: self.textbuffer.cut_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD), True))
        toolbar.insert(cut_tb, -1)

        copy_tb = Gtk.ToolButton.new_from_stock(Gtk.STOCK_COPY)
        copy_tb.connect('clicked', lambda w: self.textbuffer.copy_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)))
        toolbar.insert(copy_tb, -1)

        paste_tb = Gtk.ToolButton.new_from_stock(Gtk.STOCK_PASTE)
        paste_tb.connect('clicked', lambda w: self.textbuffer.paste_clipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD), None, True))
        toolbar.insert(paste_tb, -1)

        return toolbar

    def _create_accels(self):
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        # File
        key, mod = Gtk.accelerator_parse('<Control>n')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.new_file())
        key, mod = Gtk.accelerator_parse('<Control>o')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.open_file())
        key, mod = Gtk.accelerator_parse('<Control>s')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.save_file())

        # Edit
        key, mod = Gtk.accelerator_parse('<Control>z')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.undo())
        key, mod = Gtk.accelerator_parse('<Control><Shift>Z')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.redo())
        key, mod = Gtk.accelerator_parse('<Control>a')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.select_all())
        key, mod = Gtk.accelerator_parse('<Control>f')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.show_find_dialog())
        key, mod = Gtk.accelerator_parse('<Control>h')
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *args: self.show_find_dialog())

    def new_file(self):
        if not self._maybe_save():
            return
        self.textbuffer.set_text('')
        self.current_file = None
        self.dirty = False
        self.set_title('Notepad - Untitled')
        self.undo_stack = []
        self.redo_stack = []
        self._push_undo_snapshot()

    def open_file(self):
        if not self._maybe_save():
            return

        dialog = Gtk.FileChooserDialog(title='Open File', parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.textbuffer.set_text(text)
                self.current_file = path
                self.dirty = False
                self.set_title(f'Notepad - {os.path.basename(path)}')
                self.undo_stack = []
                self.redo_stack = []
                self._push_undo_snapshot()
            except Exception as e:
                self._message('Error', f'Could not open file:\n{e}')
        dialog.destroy()

    def save_file(self):
        if self.current_file:
            return self._save_to(self.current_file)
        return self.save_file_as()

    def save_file_as(self):
        dialog = Gtk.FileChooserDialog(title='Save File As', parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            ok = self._save_to(path)
            dialog.destroy()
            return ok
        dialog.destroy()
        return False

    def _save_to(self, path):
        start, end = self.textbuffer.get_bounds()
        text = self.textbuffer.get_text(start, end, True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.current_file = path
            self.dirty = False
            self.set_title(f'Notepad - {os.path.basename(path)}')
            return True
        except Exception as e:
            self._message('Error', f'Could not save file:\n{e}')
            return False

    def _maybe_save(self):
        if not self.dirty:
            return True
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.NONE, text='The document has unsaved changes.')
        dialog.format_secondary_text('Do you want to save your changes?')
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Don\'t Save', Gtk.ResponseType.NO)
        dialog.add_button('Save', Gtk.ResponseType.YES)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.CANCEL:
            return False
        if response == Gtk.ResponseType.NO:
            return True
        if response == Gtk.ResponseType.YES:
            return self.save_file()
        return True

    def on_text_changed(self, buffer):
        self.dirty = True
        now = time.time()
        if now - self._last_snapshot_time > self._snapshot_debounce:
            self._push_undo_snapshot()
            self._last_snapshot_time = now
        self.update_statusbar()

    def _push_undo_snapshot(self):
        start, end = self.textbuffer.get_bounds()
        text = self.textbuffer.get_text(start, end, True)
        # Avoid duplicate snapshots
        if self.undo_stack and self.undo_stack[-1] == text:
            return
        self.undo_stack.append(text)
        # limit stack size
        if len(self.undo_stack) > 200:
            self.undo_stack.pop(0)

    def undo(self):
        if len(self.undo_stack) < 2:
            return
        # move current snapshot to redo
        current = self.undo_stack.pop()
        self.redo_stack.append(current)
        text = self.undo_stack[-1]
        self._apply_text_without_snapshot(text)

    def redo(self):
        if not self.redo_stack:
            return
        text = self.redo_stack.pop()
        self._apply_text_without_snapshot(text)
        self.undo_stack.append(text)

    def _apply_text_without_snapshot(self, text):
        # Block pushing new snapshot while setting text
        self.textbuffer.handler_block_by_func(self.on_text_changed)
        self.textbuffer.set_text(text)
        self.textbuffer.handler_unblock_by_func(self.on_text_changed)
        self.dirty = True
        self.update_statusbar()

    def select_all(self):
        start, end = self.textbuffer.get_bounds()
        self.textbuffer.select_range(start, end)

    def toggle_wrap(self, enabled: bool):
        if enabled:
            self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            self.textview.set_wrap_mode(Gtk.WrapMode.NONE)

    def update_statusbar(self):
        # Compute line/column
        iter_ = self.textbuffer.get_iter_at_mark(self.textbuffer.get_insert())
        line = iter_.get_line() + 1
        col = iter_.get_line_offset() + 1
        self.statusbar.pop(self.status_ctx)
        self.statusbar.push(self.status_ctx, f'Ln {line}, Col {col}')

    def on_cursor_moved(self, widget, step, count, extend_selection):
        # update position after cursor movement
        Gtk.idle_add(self.update_statusbar)

    def show_about(self):
        about = Gtk.AboutDialog(transient_for=self, modal=True)
        about.set_program_name('Notepad (GTK)')
        about.set_version('0.1')
        about.set_comments('Simple Notepad-like editor built with GTK and Python.')
        about.set_website('https://example.local')
        about.run()
        about.destroy()

    def _message(self, title, text):
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

    def on_delete_event(self, *args):
        if not self._maybe_save():
            return True
        return False

    def on_quit(self):
        if not self._maybe_save():
            return
        Gtk.main_quit()

    # --- Find / Replace dialog ---
    def show_find_dialog(self):
        dialog = Gtk.Dialog(title='Find / Replace', transient_for=self, modal=True)
        dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        content = dialog.get_content_area()

        grid = Gtk.Grid(column_spacing=6, row_spacing=6, margin=12)

        lbl_find = Gtk.Label(label='Find:')
        self.entry_find = Gtk.Entry()
        lbl_replace = Gtk.Label(label='Replace:')
        self.entry_replace = Gtk.Entry()

        self.check_case = Gtk.CheckButton(label='Case sensitive')

        btn_find_next = Gtk.Button(label='Find Next')
        btn_replace = Gtk.Button(label='Replace')
        btn_replace_all = Gtk.Button(label='Replace All')

        btn_find_next.connect('clicked', lambda w: self.find_next())
        btn_replace.connect('clicked', lambda w: self.replace_once())
        btn_replace_all.connect('clicked', lambda w: self.replace_all())

        grid.attach(lbl_find, 0, 0, 1, 1)
        grid.attach(self.entry_find, 1, 0, 2, 1)
        grid.attach(lbl_replace, 0, 1, 1, 1)
        grid.attach(self.entry_replace, 1, 1, 2, 1)
        grid.attach(self.check_case, 0, 2, 3, 1)
        grid.attach(btn_find_next, 0, 3, 1, 1)
        grid.attach(btn_replace, 1, 3, 1, 1)
        grid.attach(btn_replace_all, 2, 3, 1, 1)

        content.pack_start(grid, True, True, 0)
        dialog.show_all()

        response = dialog.run()
        dialog.destroy()
        return response

    def _search_from_iter(self, start_iter, pattern, case_sensitive=False):
        flags = Gtk.TextSearchFlags.TEXT_SEARCH_VISIBLE_ONLY
        if not case_sensitive:
            flags = 0
        # use forward_search on TextBuffer
        result = self.textbuffer.forward_search(pattern, flags, start_iter)
        return result

    def find_next(self):
        pattern = self.entry_find.get_text()
        if not pattern:
            return
        insert_mark = self.textbuffer.get_insert()
        start_iter = self.textbuffer.get_iter_at_mark(insert_mark)
        # start search after current insert
        if not start_iter.ends_line() and start_iter.forward_char():
            pass
        res = self._search_from_iter(start_iter, pattern, self.check_case.get_active())
        if not res:
            # wrap-around search
            start = self.textbuffer.get_start_iter()
            res = self._search_from_iter(start, pattern, self.check_case.get_active())
            if not res:
                self._message('Find', 'Pattern not found')
                return
        match_start, match_end = res
        self.textbuffer.select_range(match_start, match_end)
        self.textview.scroll_to_iter(match_start, 0.1, use_align=True, xalign=0.5, yalign=0.5)

    def replace_once(self):
        sel_bounds = self.textbuffer.get_selection_bounds()
        if sel_bounds:
            start, end = sel_bounds
            # replace selection
            self.textbuffer.begin_user_action()
            self.textbuffer.delete(start, end)
            self.textbuffer.insert(start, self.entry_replace.get_text())
            self.textbuffer.end_user_action()
            self._push_undo_snapshot()
        else:
            # find next then replace
            self.find_next()
            sel_bounds = self.textbuffer.get_selection_bounds()
            if sel_bounds:
                start, end = sel_bounds
                self.textbuffer.begin_user_action()
                self.textbuffer.delete(start, end)
                self.textbuffer.insert(start, self.entry_replace.get_text())
                self.textbuffer.end_user_action()
                self._push_undo_snapshot()

    def replace_all(self):
        pattern = self.entry_find.get_text()
        if not pattern:
            return
        replace_text = self.entry_replace.get_text()
        iter_ = self.textbuffer.get_start_iter()
        count = 0
        while True:
            res = self._search_from_iter(iter_, pattern, self.check_case.get_active())
            if not res:
                break
            start, end = res
            self.textbuffer.begin_user_action()
            self.textbuffer.delete(start, end)
            self.textbuffer.insert(start, replace_text)
            self.textbuffer.end_user_action()
            count += 1
            # continue after replacement
            iter_ = start
        if count == 0:
            self._message('Replace All', 'No matches found')
        else:
            self._message('Replace All', f'Replaced {count} occurrence(s)')
            self._push_undo_snapshot()


def main():
    app = NotepadWindow()
    app.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
