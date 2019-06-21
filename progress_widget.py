from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy
from queue import Queue


class MyStatusBar(QStatusBar):
    max_active_jobs = 5

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(20)

        self.widgets = {}
        self.summary_wgt = SummaryWidget(self)
        self.summary_wgt.set_pending()

        self._visible = []

    @property
    def sorted_wgts(self):
        wgts = list(self.widgets.values())
        return sorted(wgts, key=lambda x: x.value(), reverse=True)

    def position_changed(self, wgt):
        pos = self.sorted_wgts.index(wgt)

        try:
            i = self._visible.index(wgt)
        except ValueError:
            vals = [v.value() for v in self._visible]
            return any(map(lambda x: x < wgt.value(), vals))

        return pos != i

    def update_wgt_progress(self, id_, val):
        wgt = self.widgets[id_]
        wgt.progress_bar.setValue(val)

        changed = self.position_changed(wgt)

        if changed:
            self.update_bar_progress()

    def set_max_value(self, id_, max_value):
        self.widgets[id_].set_maximum(max_value)

    def update_bar_progress(self):
        wgts = self.sorted_wgts
        max_ = self.max_active_jobs
        vis = self._visible

        if wgts != vis:
            for w in vis:
                self.removeWidget(w)

            disp = wgts[0:max_]
            if len(wgts) > max_:
                disp = wgts[0:(max_ - 1)]
                n = len(wgts) - len(disp)
                self.summary_wgt.update_label(n)
                disp.append(self.summary_wgt)

            vis.clear()
            for d in disp:
                d.show()
                vis.append(d)
                self.addWidget(d)

    def add_file(self, id_, name):
        wgt = ProgressWidget(self)
        wgt.set_label(name)
        wgt.set_pending()
        self.widgets[id_] = wgt
        self.update_bar_progress()

    def file_loaded(self, id_):
        del_wgt = self.widgets[id_]
        del_wgt.deleteLater()
        del self.widgets[id_]

        try:
            self._visible.remove(del_wgt)
        except ValueError:
            pass

        self.update_bar_progress()


class ProgressWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(140)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFixedHeight(2)

        self.label = QLabel(self)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        self._maximum = 0

    def __repr__(self):
        return "Progress widget '{}'\n" \
               "\t- maximum value '{}'" \
               "\t- current value '{}'".format(self.label.text(),
                                               self.progress_bar.maximum(),
                                               self.value())

    def set_maximum(self, maximum):
        self._maximum = maximum
        self.progress_bar.setRange(1, maximum)

    def set_pending(self):
        self.progress_bar.setRange(0, 0)

    def set_label(self, text):
        self.label.setText(text)

    def value(self):
        bar = self.progress_bar
        try:
            val = bar.value() / bar.maximum()
        except ZeroDivisionError:
            val = -1

        return val

    def set_failed_state(self):
        pass


class SummaryWidget(ProgressWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.set_pending()

    def update_label(self, n):
        self.label.setText("and other {} files...".format(n))
