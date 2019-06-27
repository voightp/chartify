from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy, \
    QPushButton, QHBoxLayout
from PySide2.QtCore import Signal, Qt
from threads import MonitorThread
from queue import Queue


class MyStatusBar(QStatusBar):
    """
    Wrapper class with added functionality to
    display widgets with file processing progress.

    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(20)


class ProgressContainer(QWidget):
    """
    A container to hold all progress widgets.

    """
    max_active_jobs = 5
    child_width = 140

    def __init__(self, parent, queue):
        super().__init__(parent)
        m = self.max_active_jobs * self.child_width
        self.setFixedWidth(m)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft)

        self.widgets = {}
        self.summary_wgt = SummaryWidget(self, None)
        self.summary_wgt.set_pending()

        self._visible = []

        self.monitor_thread = MonitorThread(queue)
        self.monitor_thread.start()
        self.monitor_thread.initialized.connect(self.initialize_file_progress)
        self.monitor_thread.started.connect(self.update_progress_text)
        self.monitor_thread.progress_text_updated.connect(self.update_progress_text)
        self.monitor_thread.progress_bar_updated.connect(self.update_bar_progress)
        self.monitor_thread.preprocess_finished.connect(self.set_progress_bar_max)
        self.monitor_thread.finished.connect(self.file_loaded)
        self.monitor_thread.failed.connect(self.file_failed)

    @property
    def sorted_wgts(self):
        """ Sort widgets by their value (descending order). """
        wgts = list(self.widgets.values())
        return sorted(wgts, key=lambda x: x.value(), reverse=True)

    def position_changed(self, wgt):
        """ Check if the current widget triggers repositioning. """
        pos = self.sorted_wgts.index(wgt)

        try:
            i = self._visible.index(wgt)
        except ValueError:
            # widget is in pending section, although it
            # can still be being processed on machines with
            # number of cpu greater than max_active_jobs
            vals = [v.value() for v in self._visible]
            return any(map(lambda x: x < (wgt.value() + 1), vals))

        return pos != i

    def update_wgt_progress(self, id_, val):
        """ Update progress value on a widget. """
        wgt = self.widgets[id_]
        wgt.progress_bar.setValue(val)

        changed = self.position_changed(wgt)

        if changed:
            self.update_bar()

    def set_max_value(self, id_, max_value):
        """ Set up maximum progress value. """
        self.widgets[id_].set_maximum(max_value)

    def update_bar(self):
        """ Update progress widget display on the status bar. """
        wgts = self.sorted_wgts
        max_ = self.max_active_jobs
        vis = self._visible

        if wgts != vis:
            for w in vis:
                self.layout().removeWidget(w)

            disp = wgts[0:max_]
            if len(wgts) > max_:
                disp = wgts[0:(max_ - 1)]
                n = len(wgts) - len(disp)
                self.summary_wgt.update_label(n)
                disp.append(self.summary_wgt)
            else:
                self.summary_wgt.hide()

            vis.clear()
            for d in disp:
                d.show()
                vis.append(d)
                self.layout().addWidget(d)

    def add_file(self, id_, name):
        """ Add progress widget to the status bar. """
        wgt = ProgressWidget(self, id_)
        wgt.set_label(name)
        wgt.set_pending()
        wgt.remove.connect(self.remove_file)

        self.widgets[id_] = wgt
        self.update_bar()

    def remove_file(self, id_):
        """ Remove widget from the status bar. """
        del_wgt = self.widgets[id_]
        del_wgt.deleteLater()
        del self.widgets[id_]

        try:
            self._visible.remove(del_wgt)
        except ValueError:
            pass

        self.update_bar()

    def set_failed(self, id_):
        """ Set failed status on the given widget. """
        self.widgets[id_].set_failed_status()

    def initialize_file_progress(self, monitor_id, monitor_name):
        """ Add a progress bar on the interface. """
        self.add_file(monitor_id, monitor_name)

    def update_progress_text(self, monitor_id, text):
        """ Update text info for a given monitor. """
        pass
        # self.status_bar.progressBars[monitor_id].setText(text)

    def set_progress_bar_max(self, monitor_id, max_value):
        """ Set maximum progress value for a given monitor. """
        self.set_max_value(monitor_id, max_value)

    def update_bar_progress(self, monitor_id, value):
        """ Update progress value for a given monitor. """
        self.update_wgt_progress(monitor_id, value)

    def file_loaded(self, monitor_id):
        """ Remove a progress bar when the file is loaded. """
        self.remove_file(monitor_id)

    def file_failed(self, monitor_id):
        """ Set failed status on the progress widget. """
        self.set_failed(monitor_id)


class ProgressWidget(QWidget):
    """
    A widget to display current eso file
    processing progress.

    """
    remove = Signal(int)

    def __init__(self, parent, id_):
        super().__init__(parent)
        self.id_ = id_
        self.maximum = 0

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(ProgressContainer.child_width)

        wgt = QWidget(self)
        layout = QHBoxLayout(wgt)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.progress_bar = QProgressBar(wgt)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFixedHeight(1)

        self.del_btn = QPushButton(wgt)
        self.del_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.del_btn.setFixedSize(15, 15)
        self.del_btn.setVisible(False)
        self.del_btn.clicked.connect(self.send_remove_me)

        self.label = QLabel(wgt)

        layout.addWidget(self.del_btn)
        layout.addWidget(self.label)

        self.main_layout.addWidget(wgt)
        self.main_layout.addWidget(self.progress_bar)

    def __repr__(self):
        return "Progress widget '{}'\n" \
               "\t- maximum value '{}'" \
               "\t- current value '{}'".format(self.label.text(),
                                               self.progress_bar.maximum(),
                                               self.value())

    def set_maximum(self, maximum):
        """ Set progress bar maximum value. """
        self.maximum = maximum
        self.progress_bar.setRange(1, maximum)

    def set_pending(self):
        """ Set pending status. """
        self.progress_bar.setRange(0, 0)

    def set_label(self, text):
        """ Set text on the label. """
        self.label.setText(text)

    def value(self):
        """ Get current progress value (as percentage). """
        bar = self.progress_bar
        try:
            val = bar.value() / bar.maximum() * 100
        except ZeroDivisionError:
            val = -1

        return val

    def send_remove_me(self):
        """ Give signal to status bar to remove this widget. """
        self.remove.emit(self.id_)

    def set_failed_status(self):
        """ Apply 'failed' style on the progress widget. """
        bar = self.progress_bar
        bar.setMaximum(999)
        bar.setValue(999)

        self.setProperty("failed", "true")
        self.style().unpolish(self.label)
        self.style().unpolish(self.progress_bar)
        self.style().polish(self.label)
        self.style().polish(self.progress_bar)

        self.del_btn.show()
        self.setToolTip("FAILED - INCOMPLETE FILE")


class SummaryWidget(ProgressWidget):
    """
    A special type of progress widget to report
    remaining number of jobs.

    The status is always pending.

    """

    def __init__(self, parent, id_):
        super().__init__(parent, id_)
        self.set_pending()

    def update_label(self, n):
        """ Update number of pending jobs. """
        self.label.setText("+ {} files...".format(n))
