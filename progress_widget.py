from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy
from queue import Queue


class MyStatusBar(QStatusBar):
    max_active_jobs = 4

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.widgets = {}
        self.active_jobs = []
        self.pending_jobs = []

    def set_max_value(self, monitor_id, max_value):
        self.widgets[monitor_id].set_maximum(max_value)

    def add_file(self, id_, name):
        wgt = ProgressWidget(self, name)
        self.widgets[id_] = wgt

        if len(self.active_jobs) < self.max_active_jobs:
            self.display_wgt(wgt)

        else:
            self.pending_jobs.insert(0, wgt)

    def display_wgt(self, wgt):
        self.active_jobs.append(wgt)
        self.addWidget(wgt)
        wgt.set_pending()

    def update_progress(self, id_, val):
        self.widgets[id_].progress_bar.setValue(val)

    def file_loaded(self, id_):
        del_wgt = self.widgets[id_]
        del_wgt.deleteLater()
        del self.widgets[id_]

        try:
            wgt = self.pending_jobs.pop(0)
            self.display_wgt(wgt)
        except IndexError:
            pass


class ProgressWidget(QWidget):
    def __init__(self, parent, name):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setToolTip("FOOOOOO")

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(200)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFixedHeight(2)

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
