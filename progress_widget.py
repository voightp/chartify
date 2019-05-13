from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy


class MyStatusBar(QStatusBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.widgets = {}

    def set_max_value(self, monitor_id, max_value):
        self.widgets[monitor_id].set_maximum(max_value)

    def start_loading(self, id, name):
        wgt = ProgressWidget(self, name)
        self.addWidget(wgt)
        self.widgets[id] = wgt
        self.set_pending(id)

    def file_loaded(self, id):
        self.widgets[id].deleteLater()
        del self.widgets[id]

    def set_pending(self, id):
        self.widgets[id].set_pending()

    def update_progress(self, id, val):
        self.widgets[id].progress_bar.setValue(val)


class ProgressWidget(QWidget):
    def __init__(self, parent, name):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(200)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFixedHeight(10)

        self.name = QLabel(name)
        layout.addWidget(self.name)
        layout.addWidget(self.progress_bar)

        self._maximum = 0

    def set_maximum(self, maximum):
        self._maximum = maximum
        self.progress_bar.setRange(1, maximum)

    def set_pending(self):
        self.progress_bar.setRange(0, 0)


class MyProgressBar(QProgressBar):
    def __init__(self, parent):
        super().__init__(parent)
        self._text = None

        self.setAlignment(QtCore.Qt.AlignCenter)

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text
