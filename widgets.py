from PySide2.QtWidgets import QTextEdit, QSizePolicy, QLineEdit, QFrame, QHBoxLayout
from PySide2.QtGui import QTextOption
from PySide2.QtCore import Qt, Signal, QFileInfo
from PySide2.QtWidgets import QFrame
from PySide2 import QtGui, QtCore


def update_appearance(wgt):
    """ Refresh CSS of the widget. """
    wgt.style().unpolish(wgt)
    wgt.style().polish(wgt)


def filter_eso_files(urls, extensions=("eso",)):
    """ Return a list of file paths with given extensions. """
    files = []
    for url in urls:
        f = url.toLocalFile()
        info = QFileInfo(f)
        if info.suffix() in extensions:
            files.append(f)
    return files


class DropFrame(QFrame):
    """
    A custom frame accepting .eso file drops.

    Works together with custom .css to allow
    changing colours based on file extension.

    """

    def __init__(self, *args, callbacks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.callbacks = callbacks

    def dragEnterEvent(self, event):
        """ Handle appearance when a drag event is entering. """
        mime = event.mimeData()

        if not mime.hasUrls():
            return

        event.acceptProposedAction()
        files = filter_eso_files(mime.urls())

        # update appearance
        self.setProperty("drag-accept", bool(files))
        update_appearance(self)

    def dragLeaveEvent(self, event):
        """ Handle appearance when a drag event is leaving. """
        self.setProperty("drag-accept", "")
        update_appearance(self)

    def dropEvent(self, event):
        """ Handle file drops. """
        mime = event.mimeData()
        files = filter_eso_files(mime.urls())

        if files:
            # invoke load files
            self.callbacks["load_eso_files"](files)

        # update appearance
        self.setProperty("drag-accept", "")
        update_appearance(self)


# TODO this might not be necessary
# the reason behind this is that I'd like to find a way to hack cursor color
class LineEdit(QFrame):
    """
    A custom line edit to allow changing cursor color.

    """
    textEdited = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.line_edit = QLineEdit(self)
        self.line_edit.textEdited.connect(self.on_text_change)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.line_edit)

    def on_text_change(self):
        """ Trigger textEdited signal. """
        self.textEdited.emit()

    def text(self):
        """ Get str content. """
        return self.line_edit.text()

    def setPlaceholderText(self, text):
        """ Set LineEdit placeholder text. """
        self.line_edit.setPlaceholderText(text)
