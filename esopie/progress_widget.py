from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QStatusBar, QVBoxLayout, QSizePolicy, \
    QPushButton, QHBoxLayout
from PySide2.QtCore import Signal, Qt
from esopie.threads import MonitorThread


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
        return sorted(files, key=lambda x: x.rel_value, reverse=True)

    @property
    def visible_files(self):
        """ Get currently visible files. """
        wgts = self.visible_widgets
        return [wgt.file_ref for wgt in wgts]

    @property
    def visible_widgets(self):
        """ Get currently visible widgets. """
        return list(filter(lambda x: x.file_ref, self.widgets))

    def create_widgets(self):
        """ Initialize progress widgets. """
        wgts = []
        for i in range(self.max_active_jobs):
            wgt = ProgressWidget(self)
            wgt.remove.connect(self.remove_file)
            wgt.setVisible(False)
            wgts.append(wgt)
            self.layout().addWidget(wgt)
        return wgts

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

        if i is None:
            # widget is in pending section, although it
            # can still be being processed on machines with
            # number of cpu greater than max_active_jobs
            vals = [v.rel_value for v in self.visible_files if not isinstance(v, SummaryFile)]
            return any(map(lambda x: x < (file.rel_value + 3), vals))

        return pos != i

    def update_file_progress(self, id_, val):
        """ Update file progress. """
        f = self.files[id_]
        f.set_value(val)

        i = self.visible_index(f)
        if i is not None:
            self.widgets[i].update_value()

        # check if file visible position has changed
        if self.position_changed(f):
            self.update_bar()

    def update_bar(self):
        """ Update progress widget display on the status bar. """
        files = self.sorted_files
        widgets = self.widgets
        max_ = self.max_active_jobs
        n = len(files)

        disp = files[0:max_] if n > max_ else files + [None for _ in range(n, max_)]
        if n > max_:
            n = n - max_ + 1
            sm = SummaryFile()
            sm.update_label(n)
            disp[-1] = sm

        for f, w in zip(disp, widgets):
            if not f:
                w.file_ref = None
            elif f != w.file_ref:
                w.set_file_ref(f)

        for w in widgets:
            w.setVisible(bool(w.file_ref))

    def add_file(self, id_, name):
        """ Add progress file to the container. """
        f = ProgressFile(id_, name)
        self.files[id_] = f
        self.update_bar()

    def set_max_value(self, id_, max_value):
        """ Set up maximum progress value. """
        f = self.files[id_]
        f.set_maximum(max_value)

        i = self.visible_index(f)
        if i is not None:
            self.widgets[i].update_max()

    def set_failed(self, id_):
        """ Set failed status on the given file. """
        self.files[id_].set_failed()
        i = self.visible_index(self.files[id_])
        if i is not None:
            self.widgets[i].update_all_refs()
            self.widgets[i].set_failed_status()

    def remove_file(self, id_):
        """ Remove file from the container. """
        del_file = self.files.pop(id_)

        i = self.visible_index(del_file)
        if i is not None:
            self.widgets[i].file_ref = None

        self.update_bar()

    def update_progress_text(self, monitor_id, text):
        """ Update text info for a given monitor. """
        pass  # TODO review if needed
        # self.status_bar.progressBars[monitor_id].setText(text)

    def connect_monitor_actions(self):
        """ Create monitor actions. """
        self.monitor_thread.initialized.connect(self.add_file)
        self.monitor_thread.started.connect(self.update_progress_text)
        self.monitor_thread.progress_text_updated.connect(self.update_progress_text)
        self.monitor_thread.progress_bar_updated.connect(self.update_file_progress)
        self.monitor_thread.preprocess_finished.connect(self.set_max_value)
        self.monitor_thread.finished.connect(self.remove_file)
        self.monitor_thread.failed.connect(self.set_failed)


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
    def value(self):
        """ Get current progress value. """
        return self._value

    @property
    def rel_value(self):
        """ Get current progress value (as percentage). """
        try:
            val = self._value / self._maximum * 100
        except ZeroDivisionError:
            val = -1
        return val

    @property
    def failed(self):
        """ Check if the file processing has failed. """
        return self._failed

    @property
    def maximum(self):
        """ Get current maximum. """
        return self._maximum

    def set_value(self, val):
        """ Set current progress value. """
        self._value = val

    def set_failed(self):
        """ Set failed values. """
        self._failed = True
        self.set_value(999)
        self.set_maximum(999)

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
        self.maximum = 0
        self.value = 0
        self.label = ""
        self.file_ref = "summary"
        self.failed = False

    def update_label(self, n):
        """ Update number of pending jobs. """
        self.label = "processing {} files...".format(n)


class ProgressWidget(QWidget):
    """
    A widget to display current eso file
    processing progress.

    """
    remove = Signal(ProgressFile)

    def __init__(self, parent):
        super().__init__(parent)
        self.file_ref = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(ProgressContainer.child_width)
        self.setProperty("failed", False)

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

    def set_file_ref(self, file):
        """ Update widget properties. """
        self.file_ref = file
        self.update_all_refs()

        if file.failed:
            self.set_failed_status()
        elif self.property("failed"):
            # widget has been in 'failed' state, reapply standard appearance
            self.set_normal_status()

    def update_all_refs(self):
        """ Refresh all attributes. """
        self.update_label()
        self.update_max()
        self.update_value()

    def update_max(self):
        """ Set progress bar maximum value. """
        self.progress_bar.setMaximum(self.file_ref.maximum)

    def update_label(self):
        """ Set text on the label. """
        self.label.setText(self.file_ref.label)

    def update_value(self):
        """ Set current value. """
        self.progress_bar.setValue(self.file_ref.value)

    def set_normal_status(self):
        """ Apply standard style. """
        self.setProperty("failed", "false")
        self.style().unpolish(self.label)
        self.style().unpolish(self.progress_bar)
        self.style().polish(self.label)
        self.style().polish(self.progress_bar)

        self.del_btn.hide()
        self.setToolTip("")

    def set_failed_status(self):
        """ Apply 'failed' style. """
        self.setProperty("failed", "true")
        self.style().unpolish(self.label)
        self.style().unpolish(self.progress_bar)
        self.style().polish(self.label)
        self.style().polish(self.progress_bar)

        self.del_btn.show()
        self.setToolTip("FAILED - INCOMPLETE FILE")

    def send_remove_me(self):
        """ Give signal to status bar to remove this widget. """
        self.remove.emit(self.file_ref.id_)