from PySide2.QtCore import Signal, Qt
from PySide2.QtWidgets import (QWidget, QLabel, QProgressBar,
                               QVBoxLayout, QSizePolicy,
                               QPushButton, QHBoxLayout)


class ProgressContainer(QWidget):
    """

    A container to hold all progress widgets.

    All the currently processed files are stored as 'masks'.
    Masks data is being updated using signals mechanism from
    application controller.

    """

    MAX_VISIBLE_JOBS = 5
    CHILD_SPACING = 3

    def __init__(self, parent):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.CHILD_SPACING)
        layout.setAlignment(Qt.AlignLeft)

        self.files = {}
        self.widgets = self._create_widgets()

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

    def _create_widgets(self):
        """ Initialize progress widgets. """
        wgts = []
        for i in range(self.MAX_VISIBLE_JOBS):
            wgt = ProgressWidget(self)
            wgt.remove.connect(self.remove_file)
            wgt.setVisible(False)
            wgts.append(wgt)
            self.layout().addWidget(wgt)
        return wgts

    def _get_visible_index(self, file):
        """ Get visible index, returns 'None' if invalid. """
        try:
            return self.visible_files.index(file)
        except ValueError:
            return None

    def _position_changed(self, file):
        """ Check if the current widget triggers repositioning. """
        pos = self.sorted_files.index(file)
        i = self._get_visible_index(file)

        if i is None:
            # widget is in pending section, although it
            # can still be being processed on machines with
            # number of cpu greater than MAX_VISIBLE_JOBS
            vals = [v.rel_value for v in self.visible_files
                    if not isinstance(v, SummaryFile)]
            return any(map(lambda x: x < (file.rel_value + 3), vals))

        return pos != i

    def _update_bar(self):
        """ Update progress widget order on the status bar. """
        files = self.sorted_files
        widgets = self.widgets
        max_ = self.MAX_VISIBLE_JOBS
        n = len(files)

        fill = [None for _ in range(n, max_)]
        disp = files[0:max_] if n > max_ else files + fill
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
        self._update_bar()

    def set_range(self, id_, min_value, max_value):
        """ Set up maximum progress value. """
        try:
            f = self.files[id_]
            f.set_maximum(max_value)
            f.set_value(min_value)

            i = self._get_visible_index(f)
            if i is not None:
                self.widgets[i].update_max()
        except KeyError:
            pass

    def update_progress(self, id_, val):
        """ Update file progress. """
        try:
            f = self.files[id_]
            f.set_value(val)

            i = self._get_visible_index(f)
            if i is not None:
                self.widgets[i].update_value()

            if self._position_changed(f):
                self._update_bar()
        except KeyError:
            pass

    def set_failed(self, id_, message):
        """ Set failed status on the given file. """
        self.files[id_].set_failed()
        i = self._get_visible_index(self.files[id_])
        if i is not None:
            self.widgets[i].update_all_refs()
            self.widgets[i].set_failed_status(message)

    def set_pending(self, id_):
        """ Set pending status on the given file. """
        try:
            self.files[id_].set_pending()
            i = self._get_visible_index(self.files[id_])
            if i is not None:
                self.widgets[i].update_all_refs()
        except KeyError:
            pass

    def remove_file(self, id_):
        """ Remove file from the container. """
        del_file = self.files.pop(id_)

        i = self._get_visible_index(del_file)
        if i is not None:
            self.widgets[i].file_ref = None

        self._update_bar()


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

    def set_pending(self):
        """ Set infinite pending value. """
        self.set_value(0)
        self.set_maximum(0)

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

    WIDTH = 140

    def __init__(self, parent):
        super().__init__(parent)
        self.file_ref = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(self.WIDTH)
        self.setProperty("failed", False)

        wgt = QWidget(self)
        layout = QHBoxLayout(wgt)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.progress_bar = QProgressBar(wgt)
        self.progress_bar.setTextVisible(False)

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
            self.set_failed_status("Processing failed!")
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

    def set_failed_status(self, message):
        """ Apply 'failed' style. """
        self.setProperty("failed", "true")
        self.style().unpolish(self.label)
        self.style().unpolish(self.progress_bar)
        self.style().polish(self.label)
        self.style().polish(self.progress_bar)

        self.del_btn.show()
        self.setToolTip(message)

    def send_remove_me(self):
        """ Give signal to status bar to remove this widget. """
        self.remove.emit(self.file_ref.id_)
