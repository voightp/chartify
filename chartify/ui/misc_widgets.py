from typing import List

from PySide2.QtCore import Signal
from PySide2.QtGui import QDragEnterEvent, QDropEvent, QDragLeaveEvent
from PySide2.QtWidgets import (
    QWidget,
    QSizePolicy,
    QLineEdit,
    QHBoxLayout,
    QTabWidget,
    QToolButton,
    QFrame,
)

from chartify.ui.treeview import TreeView
from chartify.utils.utils import refresh_css, filter_files


class TabWidget(QTabWidget):
    """ Tab widget which displays information button when empty. """
    tabClosed = Signal(TreeView)

    def __init__(self, parent):
        super().__init__(parent)
        self.setUsesScrollButtons(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setTabPosition(QTabWidget.North)

        layout = QHBoxLayout(self)
        self.drop_btn = QToolButton(self)
        self.drop_btn.setObjectName("dropButton")
        self.drop_btn.setText("Choose a file or drag it here!")
        layout.addWidget(self.drop_btn)

        self.tabCloseRequested.connect(self.close_tab)

    def is_empty(self) -> bool:
        """ Check if there's at least one loaded file. """
        return self.count() <= 0

    def get_all_children(self) -> List[QWidget]:
        return [self.widget(i) for i in range(self.count())]

    def get_all_child_names(self) -> List[str]:
        return [self.tabText(i) for i in range(self.count())]

    def add_tab(self, wgt: QWidget, title: str) -> None:
        if self.is_empty():
            self.drop_btn.setVisible(False)
        self.addTab(wgt, title)

    def close_tab(self, index: int) -> None:
        wgt = self.widget(index)
        self.removeTab(index)
        if self.is_empty():
            self.drop_btn.setVisible(True)
        self.tabClosed.emit(wgt)


class DropFrame(QFrame):
    """ A custom frame accepting .eso file drops.

    Works together with custom .css to allow
    changing colours based on file extension.

    """

    fileDropped = Signal(list)

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """ Handle appearance when a drag event is entering. """
        mime = event.mimeData()
        if mime.hasUrls():
            event.acceptProposedAction()
            files = filter_files([url.toString() for url in mime.urls()])
            self.setProperty("drag-accept", bool(files))
            refresh_css(self)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """ Handle appearance when a drag event is leaving. """
        self.setProperty("drag-accept", "")
        refresh_css(self)

    def dropEvent(self, event: QDropEvent) -> None:
        """ Handle file drops. """
        mime = event.mimeData()
        files = filter_files([url.toString() for url in mime.urls()])
        if files:
            # invoke load files
            self.fileDropped.emit(files)
        self.setProperty("drag-accept", "")
        refresh_css(self)


class LineEdit(QFrame):
    """
    A custom line edit to allow changing cursor color.

    Which is not working!

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

    def placeholderText(self):
        """ Get placeholderText attribute. """
        return self.line_edit.placeholderText()
