from pathlib import Path
from typing import List

from PySide2.QtCore import Signal, QUrl
from PySide2.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide2.QtWidgets import QFrame, QWidget

from chartify.ui.widget_functions import refresh_css


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
