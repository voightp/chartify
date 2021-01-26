import contextlib
from itertools import zip_longest
from typing import List, Optional

from PySide2.QtCore import Signal, Qt
from PySide2.QtWidgets import (
    QFrame,
    QWidget,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QSizePolicy,
    QHBoxLayout,
)

from chartify.ui.widgets.buttons import StatusButton
from chartify.ui.widgets.widget_functions import refresh_css


class ProgressFile:
    """ Helper to store file progress details.

    Attributes
    ----------
    id_ : str
        File identifier.
    label : str
        Text displayed on the widget.
    file_path : str
        File path of the processed file.
    maximum : int
        Maximum progress set on progress bar.
    value: int
        Current progress value.
    _failed : bool, default False
        Checks if processing failed.
    _widget : ProgressWidget
        Widget displaying the file.
    _status : str
        Report current processing stage.

    """

    def __init__(self, id_: str, label: str, file_path: str):
        self.id_ = id_
        self.label = label
        self.file_path = file_path
        self._maximum = 0
        self._value = 0
        self._failed = False
        self._status = ""
        self._widget = None

    def __repr__(self):
        return (
            f"Class: '{self.__class__.__name__}'"
            f"id: '{self.id_}'"
            f"label : '{self.label}'"
            f"file_path : '{self.file_path}'"
            f"maximum : '{self.maximum}'"
            f"value : '{self.value}'"
            f"failed : '{self.failed}'"
            f"status : '{self.status}'"
        )

    @property
    def maximum(self):
        return self._maximum

    @maximum.setter
    def maximum(self, maximum: int) -> None:
        self._maximum = maximum
        if self.widget:
            self.widget.update_maximum()

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        self._value = value
        if self.widget:
            self.widget.update_value()

    @property
    def failed(self) -> bool:
        return self._failed

    @failed.setter
    def failed(self, failed: bool) -> None:
        if failed:
            self.maximum = 999
            self.value = 999
        self._failed = failed
        if self.widget:
            self.widget.set_enabled()
            self.widget.update_style()

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, status: str) -> None:
        self._status = status
        if self.widget:
            self.widget.update_status()

    @property
    def widget(self) -> "ProgressWidget":
        return self._widget

    @widget.setter
    def widget(self, widget: "ProgressWidget"):
        self._widget = widget
        if widget:
            self._widget.update_all_attributes()

    def set_pending(self) -> None:
        """ Set infinite pending value. """
        self.maximum = 0
        self.value = 0


class SummaryWidget(QFrame):
    """ A special type of widget to report remaining number of jobs."""

    WIDTH = 160

    def __init__(self, parent):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(1)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(self.WIDTH)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)

        self.label = QLabel(self)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.progress_bar)

    def update_label(self, n: int) -> None:
        """ Update number of pending jobs. """
        if n >= 1:
            self.label.setText(f"+ {n} files...")
        else:
            self.label.setText("")


class ProgressWidget(QFrame):
    """ A widget to display current eso file processing progress.

    Attributes
    ----------
    _file_ref : ProgressFile
        Currently assigned file reference.

    Notes
    -----
    Widget is only visible when file reference is set.

    """

    remove = Signal(ProgressFile)

    WIDTH = 160

    def __init__(self, parent):
        super().__init__(parent)
        self._file_ref = None
        self.setVisible(False)

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

        self.file_btn = StatusButton(wgt)
        self.file_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # self.file_btn.setFixedSize(18, 18)
        self.file_btn.clicked.connect(self.send_remove_me)
        self.file_btn.setEnabled(False)

        self.label = QLabel(wgt)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        self.main_layout.addWidget(self.file_btn)
        self.main_layout.addWidget(wgt)

    @property
    def file_ref(self) -> ProgressFile:
        return self._file_ref

    @file_ref.setter
    def file_ref(self, file: Optional[ProgressFile]) -> None:
        self._file_ref = file
        if file:
            file.widget = self  # cross reference
            self.setVisible(True)
        else:
            self.setVisible(False)

    @refresh_css
    def update_style(self) -> None:
        """ Update style according to the 'failed' state. """
        if self.property("failed") != self.file_ref.failed:
            self.setProperty("failed", self.file_ref.failed)

    def update_status(self) -> None:
        """ Update button tooltip. """
        self.file_btn.status = f"File: {self.file_ref.file_path}\n{self.file_ref.status}"

    def update_label(self) -> None:
        """ Update widget label. """
        self.label.setText(self.file_ref.label)

    def update_maximum(self) -> None:
        """ Update progress bar maximum value. """
        self.progress_bar.setMaximum(self.file_ref.maximum)

    def update_value(self) -> None:
        """ Update progress bar current value. """
        self.progress_bar.setValue(self.file_ref.value)

    def set_enabled(self) -> None:
        """ Control button state. """
        self.file_btn.setEnabled(self.file_ref.failed)

    def update_all_attributes(self) -> None:
        """ Refresh all attributes. """
        self.update_label()
        self.update_maximum()
        self.update_value()
        self.update_status()
        self.update_style()
        self.set_enabled()

    def send_remove_me(self) -> None:
        """ Give signal to status bar to remove file reference. """
        self.remove.emit(self.file_ref.id_)


class ProgressContainer(QWidget):
    """ A container to hold all progress widgets.

    All the currently processed files are stored as 'masks'.
    Masks data is being updated using signals mechanism from
    application controller.

    Attributes
    ----------
    widgets : List of ProgressWidget
        Widgets to visually represent file information.
    files : Dict of int, ProgressFile
        Holds file reference for all processed files.

    """

    def __init__(self, parent: QWidget, vertical: bool = False, n_visible_widgets: int = 5):
        super().__init__(parent)

        layout = QVBoxLayout(self) if vertical else QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignLeft)

        widgets = []
        for i in range(n_visible_widgets):
            wgt = ProgressWidget(self)
            wgt.remove.connect(self.remove_file)
            widgets.append(wgt)
            self.layout().addWidget(wgt)
        self.widgets = widgets
        self.n_visible_widgets = n_visible_widgets

        summary = SummaryWidget(self)
        summary.setVisible(False)
        self.layout().addWidget(summary)
        self.summary = summary

        self.files = {}

    @property
    def sorted_files(self) -> List[ProgressFile]:
        """ Sort widgets by value (descending order). """
        return list(self.files.values())

    def _update_bar(self) -> None:
        """ Update progress widget order on the status bar. """
        n_files = len(self.sorted_files)
        show_summary = n_files > self.n_visible_widgets
        n_visible_files = self.n_visible_widgets - 1 if show_summary else self.n_visible_widgets
        displayed = self.sorted_files[0:n_visible_files]
        for f, w in zip_longest(displayed, self.widgets):
            if not f:
                w.file_ref = None
            elif f != w.file_ref:
                w.file_ref = f
        if show_summary:
            self.sorted_files[n_visible_files].widget = None
        self.summary.setVisible(show_summary)
        self.summary.update_label(n_files - n_visible_files)

    def add_file(self, id_: str, label: str, file_path: str) -> None:
        """ Add progress file to the container. """
        self.files[id_] = ProgressFile(id_, label, file_path)
        self._update_bar()

    def set_range(self, id_: str, value: int, max_value: int) -> None:
        """ Set up maximum progress value. """
        with contextlib.suppress(KeyError):
            f = self.files[id_]
            f.maximum = max_value
            f.value = value

    def update_progress(self, id_: str, value: int) -> None:
        """ Update file progress. """
        with contextlib.suppress(KeyError):
            f = self.files[id_]
            f.value = value

    def set_status(self, id_: str, message: str) -> None:
        """ Update file progress. """
        with contextlib.suppress(KeyError):
            self.files[id_].status = message

    def set_failed(self, id_: str, message: str = "") -> None:
        """ Set failed status on the given file. """
        with contextlib.suppress(KeyError):
            f = self.files[id_]
            f.status = message
            f.failed = True

    def set_pending(self, id_: str) -> None:
        """ Set pending status on the given file. """
        with contextlib.suppress(KeyError):
            self.files[id_].set_pending()

    def remove_file(self, id_: str) -> None:
        """ Remove file from the container. """
        self.files.pop(id_)
        self._update_bar()
