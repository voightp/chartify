from PySide2.QtWidgets import QTextEdit, QSizePolicy, QLineEdit, QFrame, QHBoxLayout
from PySide2.QtGui import QTextOption
from PySide2.QtCore import Qt, Signal, QFileInfo
from PySide2.QtWidgets import QFrame
from PySide2 import QtGui, QtCore


def update_appearance(wgt):
    """ Refresh CSS of the widget. """
    wgt.style().unpolish(wgt)
    wgt.style().polish(wgt)


class DropFrame(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def dragEnterEvent(self, event):
        print("Drag enter event.")
        mime = event.mimeData()

        if not mime.hasUrls():
            return

        files = []
        for url in mime.urls():
            f = url.toLocalFile()
            info = QFileInfo(f)
            if info.suffix() in ("eso",):
                files.append(f)

        if files:
            print(files)

        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        pass

    def dragLeaveEvent(self, event):
        print("Drag leave event.")

    def dropEvent(self, event):
        print("Drop event.")

    def mouseDoubleClickEvent(self, event):
        print("double click")


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
