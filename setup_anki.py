# -*- coding: utf-8 -*-
from PyQt4 import QtGui

import aqt
from aqt.webview import AnkiWebView
from aqt.qt import *
from aqt.utils import tooltip

from imagepicker.core import Core

from config import shortcut

# Initialize only once
core = Core()

def setup():
    from anki.hooks import addHook
    addHook('browser.setupMenus', menu_action_factory, )


def _run(_browser, core, how):
    _notes = [_browser.mw.col.getNote(note_id) for note_id in _browser.selectedNotes()]
    if len(_notes) != 1:
        aqt.utils.showWarning('Please select (only) one item.', _browser)
        return
    _browser.model.beginReset()
    core.doSearch(_browser, _notes[0], how)
    _browser.model.endReset()


def menu_action_factory(_browser):
    menu = QtGui.QMenu('ImagePicker', _browser.form.menubar)
    _browser.form.menubar.addMenu(menu)

    def append_Munu(_text, how):
        action = QtGui.QAction(_text, menu)

        _browser.connect(action, SIGNAL('triggered()'),
                         lambda b=_browser: _run(b, core, how))
        from PyQt4.QtGui import QKeySequence
        action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)

    append_Munu('Search images for selected word...', 'useless parameter')


