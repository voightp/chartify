from pathlib import Path
from typing import List

from PySide2.QtCore import Signal, QUrl
from PySide2.QtGui import QDragEnterEvent, QDropEvent, QDragLeaveEvent
from PySide2.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QTabWidget,
    QToolButton,
    QFrame,
)

from chartify.ui.widget_functions import refresh_css


class TabWidget(QTabWidget):
    """ Tab widget which displays information button when empty. """

    tabClosed = Signal(int)

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

    def tabRemoved(self, index: int) -> None:
        if self.is_empty():
            self.drop_btn.setVisible(True)
        self.tabClosed.emit(index)

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


class DropFrame(QFrame):
    """ A custom frame accepting .eso file drops.

    Works together with custom .css to allow
    changing colours based on file extension.

    """

    fileDropped = Signal(list)

    def __init__(self, parent: QWidget, extensions: List[str]):
        super().__init__(parent)
        self.extensions = extensions
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def filter_files(self, urls: List[QUrl]) -> List[Path]:
        """ Verify if file can be accepted. """
        paths = []
        for url in urls:
            path = Path(url.toLocalFile())
            if path.suffix in self.extensions:
                paths.append(path)
        return paths

    @refresh_css
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """ Handle appearance when a drag event is entering. """
        mime = event.mimeData()
        if mime.hasUrls():
            event.acceptProposedAction()
            files = self.filter_files(mime.urls())
            self.setProperty("drag-accept", bool(files))

    @refresh_css
    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """ Handle appearance when a drag event is leaving. """
        self.setProperty("drag-accept", "")

    @refresh_css
    def dropEvent(self, event: QDropEvent) -> None:
        """ Handle file drops. """
        mime = event.mimeData()
        files = self.filter_files(mime.urls())
        if files:
            # invoke load files
            self.fileDropped.emit(files)
        self.setProperty("drag-accept", "")
