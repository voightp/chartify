from PySide2.QtWidgets import (QWidget, QHBoxLayout, QToolButton, QLabel,
                               QSpacerItem, QSizePolicy, QFrame, )
from PySide2.QtCore import Signal, QTimer

from chartify.view.misc_widgets import LineEdit


class ViewTools(QFrame):
    """
    A class to represent an application toolbar.

    """
    structureChanged = Signal()
    textFiltered = Signal(str)
    expandRequested = Signal()
    collapseRequested = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("viewTools")

        self.tree_view_btn = QToolButton(self)
        self.tree_view_btn.setObjectName("treeButton")

        self.collapse_all_btn = QToolButton(self)
        self.collapse_all_btn.setObjectName("collapseButton")

        self.expand_all_btn = QToolButton(self)
        self.expand_all_btn.setObjectName("expandButton")

        self.filter_icon = QLabel(self)
        self.filter_icon.setObjectName("filterIcon")

        self.filter_line_edit = LineEdit(self)

        # ~~~~ Timer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Timer to delay firing of the 'text_edited' event
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.request_filter)

        # ~~~~ Filter action ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.textEdited.connect(self.text_edited)
        self.expand_all_btn.clicked.connect(self.expandRequested.emit)
        self.collapse_all_btn.clicked.connect(self.collapseRequested.emit)
        self.tree_view_btn.toggled.connect(self.tree_btn_toggled)

        self.set_up_view_tools()

    def tree_requested(self):
        """ Check if tree structure is requested. """
        return self.tree_view_btn.isChecked()

    def get_filter_str(self):
        """ Get current filter string. """
        return self.filter_line_edit.text()

    def set_up_view_tools(self):
        """ Create tools, settings and search line for the view. """
        view_tools_layout = QHBoxLayout(self)
        view_tools_layout.setSpacing(6)
        view_tools_layout.setContentsMargins(0, 0, 0, 0)

        btn_widget = QWidget(self)
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(0)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_layout.addWidget(self.expand_all_btn)
        btn_layout.addWidget(self.collapse_all_btn)
        btn_layout.addWidget(self.tree_view_btn)

        # ~~~~ Line edit ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.setPlaceholderText("filter...")
        self.filter_line_edit.setSizePolicy(QSizePolicy.Fixed,
                                            QSizePolicy.Fixed)
        self.filter_line_edit.setFixedWidth(160)

        # ~~~~ Set up tree button  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tree_view_btn.setCheckable(True)
        self.tree_view_btn.setChecked(True)
        self.collapse_all_btn.setEnabled(True)
        self.expand_all_btn.setEnabled(True)

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        view_tools_layout.addWidget(self.filter_icon)
        view_tools_layout.addWidget(self.filter_line_edit)
        view_tools_layout.addItem(spacer)
        view_tools_layout.addWidget(btn_widget)

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
        filter_string = self.filter_line_edit.text()
        self.textFiltered.emit(filter_string)