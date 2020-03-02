from PySide2.QtCore import Signal, QTimer
from PySide2.QtWidgets import (QWidget, QHBoxLayout, QToolButton, QLabel,
                               QSpacerItem, QSizePolicy, QFrame, )

from chartify.view.misc_widgets import LineEdit


class ViewTools(QFrame):
    """
    A class to represent an application toolbar.

    """
    structureChanged = Signal()
    textFiltered = Signal(tuple)
    expandRequested = Signal()
    collapseRequested = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("viewTools")
        view_tools_layout = QHBoxLayout(self)
        view_tools_layout.setSpacing(6)
        view_tools_layout.setContentsMargins(0, 0, 0, 0)

        btn_widget = QWidget(self)
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(0)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Set up view buttons  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tree_view_btn = QToolButton(self)
        self.tree_view_btn.setObjectName("treeButton")
        self.tree_view_btn.setCheckable(True)
        self.tree_view_btn.setChecked(True)

        self.collapse_all_btn = QToolButton(self)
        self.collapse_all_btn.setObjectName("collapseButton")
        self.collapse_all_btn.setEnabled(True)

        self.expand_all_btn = QToolButton(self)
        self.expand_all_btn.setObjectName("expandButton")
        self.expand_all_btn.setEnabled(True)

        self.filter_icon = QLabel(self)
        self.filter_icon.setObjectName("filterIcon")

        btn_layout.addWidget(self.expand_all_btn)
        btn_layout.addWidget(self.collapse_all_btn)
        btn_layout.addWidget(self.tree_view_btn)

        # ~~~~ Line edit ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.variable_line_edit = LineEdit(self)
        self.variable_line_edit.setPlaceholderText("variable...")
        self.variable_line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.variable_line_edit.setFixedWidth(100)

        self.key_line_edit = LineEdit(self)
        self.key_line_edit.setPlaceholderText("key...")
        self.key_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.key_line_edit.setFixedWidth(100)

        self.units_line_edit = LineEdit(self)
        self.units_line_edit.setPlaceholderText("units...")
        self.units_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.units_line_edit.setFixedWidth(50)

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        view_tools_layout.addWidget(self.filter_icon)
        view_tools_layout.addWidget(self.variable_line_edit)
        view_tools_layout.addWidget(self.key_line_edit)
        view_tools_layout.addWidget(self.units_line_edit)
        view_tools_layout.addItem(spacer)
        view_tools_layout.addWidget(btn_widget)

        # ~~~~ Timer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Timer to delay firing of the 'text_edited' event
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.request_filter)

        # ~~~~ Filter actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.variable_line_edit.textEdited.connect(self.text_edited)
        self.key_line_edit.textEdited.connect(self.text_edited)
        self.units_line_edit.textEdited.connect(self.text_edited)
        self.expand_all_btn.clicked.connect(self.expandRequested.emit)
        self.collapse_all_btn.clicked.connect(self.collapseRequested.emit)
        self.tree_view_btn.toggled.connect(self.tree_btn_toggled)

    def tree_requested(self):
        """ Check if tree structure is requested. """
        return self.tree_view_btn.isChecked()

    def get_filter_tup(self):
        """ Get current filter string. """
        return (
            self.key_line_edit.text(),
            self.variable_line_edit.text(),
            self.units_line_edit.text()
        )

    def tree_btn_toggled(self, checked):
        """ Update view when view type is changed. """
        self.tree_view_btn.setProperty("checked", checked)

        # collapse and expand all buttons are not relevant for plain view
        self.collapse_all_btn.setEnabled(checked)
        self.expand_all_btn.setEnabled(checked)
        self.structureChanged.emit()

    def text_edited(self):
        """ Delay firing a text edited event. """
        self.timer.start(200)

    def request_filter(self):
        """ Apply a filter when the filter text is edited. """
        self.textFiltered.emit(self.get_filter_tup())
