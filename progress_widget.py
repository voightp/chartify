from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy
from queue import Queue


class MyStatusBar(QStatusBar):
    max_active_jobs = 5

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(20)

        self.widgets = {}
        self._active_jobs = []
        self._pending_jobs = []

        self._visible = []
        self.summary_wgt = SummaryWidget(self)
        self.summary_wgt.set_pending()

    @property
    def sorted_wgts(self):
        wgts = list(self.widgets.values())
        return sorted(wgts, key=lambda x: x.value())

    def set_max_value(self, monitor_id, max_value):
        self.widgets[monitor_id].set_maximum(max_value)

    def render_stuff(self):
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

            m = []
            vis.clear()
            for d in disp:
                m.append((d.label.text(), d.value()))
                vis.append(d)
                d.show()
                self.addWidget(d)

            print(m)

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

    def add_file(self, id_, name):
        wgt = ProgressWidget(self)
        wgt.set_label(name)
        wgt.set_pending()
        self.widgets[id_] = wgt

        self.render_stuff()

        # print("ADDING", len(a), len(p)) # TODO remove this

        # if len(a) < max_:
        #     self.add_widget(wgt)
        #
        # elif len(a) == max_ and len(p) == 0:
        #     p.append(wgt)
        #     last_wgt = a.pop(-1)
        #
        #     self.removeWidget(last_wgt)
        #     p.insert(0, last_wgt)
        #
        #     sum_wgt = self.create_summary_widget(len(p))
        #     a.append(sum_wgt)
        #     self.addWidget(sum_wgt)
        #
        # else:
        #     p.append(wgt)
        #     self.update_summary(len(p))

        # print("ADDING DONE", len(a), len(p))# TODO remove this

    def file_loaded(self, id_):
        del_wgt = self.widgets[id_]
        del_wgt.deleteLater()
        del self.widgets[id_]

        p = self._pending_jobs
        a = self._active_jobs

        try:
            self._visible.remove(del_wgt)
        except ValueError:
            print("FOO")

        self.render_stuff()

        # print("FILE LOADED", len(a), len(p)) # TODO remove this

        # if del_wgt in a:
        #     a.remove(del_wgt)
        #     if len(p) > 0:
        #         wgt = p.pop(0)
        #         if len(p) == 1:
        #             self.remove_summary_widget(a)
        #             wg = p.pop(0)
        #             self.add_widget(wg)
        #         else:
        #             self.update_summary(len(p))
        #
        #         self.add_widget(wgt)
        #
        # else:
        #     p.remove(del_wgt)
        #     if len(p) == 1:
        #         self.remove_summary_widget(a)
        #         wg = p.pop(0)
        #         self.add_widget(wg)
        #     else:
        #         self.update_summary(len(p))

        # print("FILE LOADED DONE", len(a), len(p))# TODO remove this


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

    def set_maximum(self, maximum):
        self._maximum = maximum
        self.progress_bar.setRange(1, maximum)

    def set_pending(self):
        self.progress_bar.setRange(0, 0)

    def set_label(self, text):
        self.label.setText(text)

    def value(self):
        return self.progress_bar.value()

    def set_failed_state(self):
        pass


class SummaryWidget(ProgressWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.set_pending()

    def update_label(self, n):
        self.label.setText("and other {} files...".format(n))
