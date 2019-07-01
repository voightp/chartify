from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar, QVBoxLayout, QSizePolicy, \
    QPushButton, QHBoxLayout
from PySide2.QtCore import Signal, Qt
from threads import MonitorThread
from queue import Queue


class StatusBar(QStatusBar):
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
    child_spacing = 3

    def __init__(self, parent, queue):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.child_spacing)
        layout.setAlignment(Qt.AlignLeft)

        self.files = {}

        self.widgets = self.create_widgets()
        self.monitor_thread = MonitorThread(queue)
        self.connect_monitor_actions()
        self.monitor_thread.start()

    @property
    def sorted_files(self):
        """ Sort widgets by value (descending order). """
        files = list(self.files.values())
        return sorted(files, key=lambda x: x.value, reverse=True)

    @property
    def failed_files(self):
        """ Extract 'failed' jobs. """
        return list(filter(lambda x: x.failed, self.sorted_wgts))

    @property
    def visible_files(self):
        """ Get currently visible files. """
        wgts = self.visible_widgets
        return [wgt.file_ref for wgt in wgts]

    @property
    def visible_widgets(self):
        """ Get currently visible widgets. """
        return list(filter(lambda x: x.file_ref, self.widgets))

    def visible_index(self, file):
        """ Get visible index, returns 'None' if invalid. """
        try:
            return self.visible_files.index(file)
        except ValueError:
            return None

    def position_changed(self, file):
        """ Check if the current widget triggers repositioning. """
        pos = self.sorted_files.index(file)

        i = self.visible_index(file)

        if i is not None:
            # widget is in pending section, although it
            # can still be being processed on machines with
            # number of cpu greater than max_active_jobs
            vals = [v.value for v in self.visible_files]
            return any(map(lambda x: x < (file.value + 1), vals))

        return pos != i

    def update_file_progress(self, id_, val):
        """ Update progress value on a widget. """
        f = self.files[id_]
        f.set_value(val)

        i = self.visible_index(f)
        if i is not None:
            self.widgets[i].set_value(val)

        # check if file visible position has changed
        if self.position_changed(f):
            self.update_bar()

    def set_max_value(self, id_, max_value):
        """ Set up maximum progress value. """
        f = self.files[id_]
        f.set_maximum(max_value)

        i = self.visible_index(f)
        if i is not None:
            self.widgets[i].set_maximum(max_value)

    def update_bar(self):
        """ Update progress widget display on the status bar. """
        files = self.sorted_files
        widgets = self.widgets
        max_ = self.max_active_jobs
        n = len(files)

        disp = files[0:max_]
        if n > max_:
            n = n - max_ - 1
            sm = SummaryFile()
            sm.update_label(n)
            disp[-1] = sm

        for f, w in zip(disp, widgets):
            if f != w.file_ref:
                w.update_file_ref(f)

        for w in widgets:
            w.setVisible(bool(w.file_ref))

    def create_widgets(self):
        """ Initialize progress widgets. """
        wgts = []
        for i in range(self.max_active_jobs):
            wgt = ProgressWidget(self)
            wgt.remove.connect(self.remove_file)
            wgt.set_pending()
            wgt.setVisible(False)
            wgts.append(wgt)
            self.layout().addWidget(wgt)
        return wgts

    def add_file(self, id_, name):
        """ Add progress widget to the status bar. """
        f = ProgressFile(id_, name)
        self.files[id_] = f
        self.update_bar()

    def remove_file(self, id_):
        """ Remove widget from the status bar. """
        del_file = self.files.pop(id_)

        i = self.visible_files.index(del_file)
        if i is not None:
            self.widgets[i].file_ref = None

        self.update_bar()

    def set_failed(self, id_):
        """ Set failed status on the given widget. """
        self.files[id_].set_failed_status()

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
        self.update_file_progress(monitor_id, value)

    def file_loaded(self, monitor_id):
        """ Remove a progress bar when the file is loaded. """
        self.remove_file(monitor_id)

    def file_failed(self, monitor_id):
        """ Set failed status on the progress widget. """
        self.set_failed(monitor_id)

    def connect_monitor_actions(self):
        """ Create monitor actions. """
        self.monitor_thread.initialized.connect(self.initialize_file_progress)
        self.monitor_thread.started.connect(self.update_progress_text)
        self.monitor_thread.progress_text_updated.connect(self.update_progress_text)
        self.monitor_thread.progress_bar_updated.connect(self.update_bar_progress)
        self.monitor_thread.preprocess_finished.connect(self.set_progress_bar_max)
        self.monitor_thread.finished.connect(self.file_loaded)
        self.monitor_thread.failed.connect(self.file_failed)


class ProgressFile:
    """
    Helper to store file progress details.
    """

    def __init__(self, id_, name):
        self.id_ = id_
        self.label = name
        self._maximum = 0
        self._value = 0
        self._failed = False

    @property
    def perc_value(self):
        """ Get current progress value (as percentage). """
        try:
            val = self._value / self._maximum * 100
        except ZeroDivisionError:
            val = -1

        return val

    @property
    def value(self):
        """ Get current progress value. """
        return self._value

    @property
    def maximum(self):
        """ Get current maximum. """
        return self._maximum

    def set_value(self, val):
        """ Set current progress value. """
        self._value = val

    def set_failed(self):
        """ Apply 'failed' style on the progress widget. """
        self._failed = True

    def set_maximum(self, maximum):
        """ Set progress bar maximum value. """
        self._maximum = maximum


class SummaryFile:
    """
    A special type of progress file to report
    remaining number of jobs.

    The status is always pending.

    """

    def __init__(self):
        self.maximum = 999
        self.value = 999
        self.label = ""
        self.file_ref = "summary"

    def update_label(self, n):
        """ Update number of pending jobs. """
        self.label = "processing {} files...".format(n)


class ProgressWidget(QWidget):
    """
    A widget to display current eso file
    processing progress.

    """
    remove = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.file_ref = None

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

    def set_file_ref(self, file):
        """ Assign file reference. """
        self.file_ref = file

    def update_file_ref(self, file):
        """ Update widget properties. """
        self.file_ref = file
        self.set_maximum(file.maximum)
        self.set_value(file.value)
        self.set_label(file.label)

    def set_maximum(self, maximum):
        """ Set progress bar maximum value. """
        self.progress_bar.setRange(1, maximum)

    def set_pending(self):
        """ Set pending status. """
        self.progress_bar.setRange(0, 0)

    def set_label(self, text):
        """ Set text on the label. """
        self.label.setText(text)

    def set_value(self, val):
        """ Set current value. """
        self.progress_bar.setValue(val)

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
