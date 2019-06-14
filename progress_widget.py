from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy
from queue import Queue


class MyStatusBar(QStatusBar):
    max_active_jobs = 4

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(20)

        self.widgets = {}
        self._active_jobs = []
        self._pending_jobs = []

    def set_max_value(self, monitor_id, max_value):
        self.widgets[monitor_id].set_maximum(max_value)

    def update_progress(self, id_, val):
        self.widgets[id_].progress_bar.setValue(val)

    def update_summary(self, n_pending):
        self._active_jobs[-1].update_label(n_pending)

    def remove_summary_widget(self, active):
        wgt = active.pop(-1)
        self.removeWidget(wgt)

    def add_widget(self, wgt):
        self.insertWidget(0, wgt)
        self._active_jobs.insert(0, wgt)

    def create_summary_widget(self, n_pending):
        wgt = SummaryWidget(self)
        wgt.update_label(n_pending)
        return wgt

    def handle_adding_summary(self, wgt, active, pending):
        self.removeWidget(wgt)
        pending.insert(0, wgt)

        sum_wgt = self.create_summary_widget(len(pending))
        active.append(sum_wgt)
        self.add_widget(sum_wgt)

    def add_file(self, id_, name):
        wgt = ProgressWidget(self)
        wgt.set_label(name)
        wgt.set_pending()
        self.widgets[id_] = wgt

        a = self._active_jobs
        p = self._pending_jobs
        max_ = self.max_active_jobs

        if len(a) < max_:
            self.add_widget(wgt)

        elif len(a) == max_ and len(p) == 0:
            p.insert(0, wgt)
            last_wgt = a.pop(-1)
            self.handle_adding_summary(last_wgt, a, p)

        else:
            p.insert(0, wgt)
            self.update_summary(len(p))

    def file_loaded(self, id_):
        del_wgt = self.widgets[id_]
        del_wgt.deleteLater()

        p = self._pending_jobs
        a = self._active_jobs

        if del_wgt in a:
            a.remove(del_wgt)
            if len(p) > 1:
                wgt = p.pop(0)
                self.add_widget(wgt)
                self.update_summary(len(p))

        else:
            p.remove(del_wgt)
            if len(p) == 1:
                self.remove_summary_widget(a)
            else:
                self.update_summary(len(p))

        del self.widgets[id_]


class ProgressWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(200)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFixedHeight(2)

        self.label = QLabel(self)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        self._maximum = 0

    def set_maximum(self, maximum):
        self._maximum = maximum
        self.progress_bar.setRange(1, maximum)

    def set_pending(self):
        self.progress_bar.setRange(0, 0)

    def set_label(self, text):
        self.label.setText(text)

    def set_failed_state(self):
        pass


class SummaryWidget(ProgressWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.set_pending()

    def update_label(self, n):
        self.label.setText("and other {} files...".format(n))
