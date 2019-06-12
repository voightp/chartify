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

    def update_summary(self, n_pending):
        self.active_jobs[-1].update_label(n_pending)

    def add_summary_widget(self):
        n = len(self.pending_jobs)
        wgt = SummaryWidget(self)
        wgt.update_label(n)
        self.active_jobs.append(wgt)
        self.addWidget(wgt)

    def remove_summary_widget(self):
        wgt = self.summary_wgt
        self.removeWidget(wgt)
        self.active_jobs.remove(wgt)

    def move_widget(self, wgt):
        self.removeWidget(wgt)
        self.active_jobs.remove(wgt)
        self.pending_jobs.insert(0, wgt)

    def add_widget(self, wgt):
        self.addWidget(wgt)
        self.active_jobs.append(wgt)

    def add_file(self, id_, name):
        wgt = ProgressWidget(self, name)
        wgt.set_pending()
        self.widgets[id_] = wgt

        n_active = len(self.active_jobs)
        n_pending = len(self.pending_jobs)

        if n_active <= self.max_active_jobs:
            self.add_widget(wgt)

        elif n_active == (self.max_active_jobs + 1):
            self.pending_jobs.insert(0, wgt)

            last_wgt = self.active_jobs[-1]
            self.move_widget(last_wgt)
            self.add_summary_widget()

        else:
            self.pending_jobs.insert(0, wgt)
            self.update_summary(n_pending)

        print("FILE ADDED N PENDING {} N ACTIVE {}".format(len(self.pending_jobs), len(self.active_jobs)))

    def update_progress(self, id_, val):
        self.widgets[id_].progress_bar.setValue(val)

    def file_loaded(self, id_):
        print("FILE LOADED N PENDING {} N ACTIVE {}".format(len(self.pending_jobs), len(self.active_jobs)))
        del_wgt = self.widgets[id_]
        del_wgt.deleteLater()
        self.active_jobs.remove(del_wgt)
        del self.widgets[id_]

        n_pending = len(self.pending_jobs)
        n_active = len(self.active_jobs)

        if n_pending == 1 and n_active == 4:
            self.remove_summary_widget()
            new_wgt = self.pending_jobs.pop(0)
            self.active_jobs.insert(0, new_wgt)
            self.addWidget(new_wgt)


class SummaryWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.label = QLabel(self)
        layout.addWidget(self.label)

    def update_label(self, n):
        self.label.setText("and other {} files...".format(n))


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
