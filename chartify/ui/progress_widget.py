import contextlib

from PySide2.QtCore import Signal, Qt
from PySide2.QtWidgets import (
    QFrame,
    QWidget,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QSizePolicy,
    QPushButton,
    QHBoxLayout,
)

from chartify.utils.utils import refresh_css


class ProgressContainer(QWidget):
    """

    A container to hold all progress widgets.

    All the currently processed files are stored as 'masks'.
    Masks data is being updated using signals mechanism from
    application controller.

    """

    MAX_VISIBLE_JOBS = 5
    CHILD_SPACING = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.CHILD_SPACING)
        layout.setAlignment(Qt.AlignLeft)

        widgets = []
        for i in range(self.MAX_VISIBLE_JOBS):
            wgt = ProgressWidget(self)
            wgt.remove.connect(self.remove_file)
            wgt.setVisible(False)
            widgets.append(wgt)
            self.layout().addWidget(wgt)

        self.widgets = widgets
        self.files = {}
        self.locked = []

    @property
    def sorted_files(self):
        """ Sort widgets by value (descending order). """
        all_files = list(self.files.values())

        # remove already locked files
        files = list(filter(lambda x: x not in self.locked, all_files))

        # locked files take precedent
        sorted_files = self.locked + sorted(files, key=lambda x: x.rel_value, reverse=True)

        return sorted_files

    @property
    def visible_files(self):
        """ Get currently visible files. """
        wgts = self.visible_widgets
        return [wgt.file_ref for wgt in wgts]

    @property
    def visible_widgets(self):
        """ Get currently visible widgets. """
        return list(filter(lambda x: x.file_ref, self.widgets))

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
            vals = [v.rel_value for v in self.visible_files if not isinstance(v, SummaryFile)]
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
        self.files[id_] = ProgressFile(id_, name)
        self._update_bar()

    def set_range(self, id_, value, max_value):
        """ Set up maximum progress value. """
        with contextlib.suppress(KeyError):
            f = self.files[id_]
            f.maximum = max_value
            f.value = value

            i = self._get_visible_index(f)
            if i is not None:
                self.widgets[i].update_max()

    def update_progress(self, id_, value):
        """ Update file progress. """
        with contextlib.suppress(KeyError):
            f = self.files[id_]
            f.value = value

            i = self._get_visible_index(f)
            if i is not None:
                self.widgets[i].update_value()

            if self._position_changed(f):
                self._update_bar()

    def set_failed(self, id_, message):
        """ Set failed status on the given file. """
        file = self.files[id_]
        file.set_failed()
        i = self._get_visible_index(file)

        if file not in self.locked:
            # let failed files be always visible
            self.locked.append(file)

        if i is not None:
            self.widgets[i].update_all_values()
            self.widgets[i].set_failed_status(message)

    def set_pending(self, id_):
        """ Set pending status on the given file. """
        file = self.files[id_]
        file.set_pending()

        if file not in self.locked:
            # pending files become locked so their position does not change
            # condition is in place to avoid multiple references when calling
            # set_pending multiple times
            self.locked.append(file)

        i = self._get_visible_index(self.files[id_])
        if i is not None:
            self.widgets[i].update_all_values()

    def remove_file(self, id_):
        """ Remove file from the container. """
        del_file = self.files.pop(id_)

        with contextlib.suppress(ValueError):
            self.locked.remove(del_file)

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
        self.maximum = 0
        self.value = 0
        self.failed = False

    @property
    def rel_value(self) -> float:
        """ Get current progress value (as percentage). """
        try:
            val = self.value / self.maximum * 100
        except ZeroDivisionError:
            val = -1
        return val

    def set_pending(self) -> None:
        """ Set infinite pending value. """
        self.value = 0
        self.maximum = 0

    def set_failed(self) -> None:
        """ Set failed values. """
        self.failed = True
        self.value = 999
        self.maximum = 999


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

    def update_label(self, n) -> None:
        """ Update number of pending jobs. """
        self.label = "processing {} files...".format(n)


class ProgressWidget(QFrame):
    """
    A widget to display current eso file
    processing progress.

    """

    remove = Signal(ProgressFile)

    WIDTH = 160

    def __init__(self, parent):
        super().__init__(parent)
        self.file_ref = None

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(self.WIDTH)
        self.setProperty("failed", False)

        wgt = QWidget(self)
        layout = QVBoxLayout(wgt)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self.progress_bar = QProgressBar(wgt)
        self.progress_bar.setTextVisible(False)

        self.file_btn = QPushButton(wgt)
        self.file_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.file_btn.setFixedSize(18, 18)
        self.file_btn.clicked.connect(self.send_remove_me)

        self.label = QLabel(wgt)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        self.main_layout.addWidget(self.file_btn)
        self.main_layout.addWidget(wgt)

    def set_file_ref(self, file):
        """ Update widget properties. """
        self.file_ref = file
        self.update_all_values()

        if file.failed:
            self.set_failed_status("Processing failed!")
        elif self.property("failed"):
            # widget has been in 'failed' state, reapply standard appearance
            self.set_normal_status()

    def update_all_values(self):
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
        self.setToolTip("")
        refresh_css(self.label, self.progress_bar, self.file_btn)

    def set_failed_status(self, message):
        """ Apply 'failed' style. """
        self.setProperty("failed", "true")
        self.setToolTip(message)
        refresh_css(self.label, self.progress_bar, self.file_btn)

    def send_remove_me(self):
        """ Give signal to status bar to remove this widget. """
        self.remove.emit(self.file_ref.id_)
