import sys
import os
import ctypes
import loky
import psutil

from PySide2.QtWidgets import (QWidget, QSplitter, QHBoxLayout, QVBoxLayout, QGridLayout, QToolButton, QLabel,
                               QGroupBox, QAction, QFileDialog, QSpacerItem, QSizePolicy, QApplication, QMenu, QFrame,
                               QMainWindow)
from PySide2.QtCore import QSize, Qt, QThreadPool, Signal, QTimer
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PySide2.QtGui import QIcon, QPixmap, QFontDatabase, QFont, QColor

from esopie.eso_file_header import FileHeader
from esopie.icons import Pixmap, text_to_pixmap
from esopie.progress_widget import StatusBar, ProgressContainer
from esopie.widgets import LineEdit, DropFrame, TabWidget
from esopie.buttons import TitledButton, ToolsButton, ToggleButton, MenuButton
from functools import partial

from eso_reader.constants import TS, D, H, M, A, RP
from eso_reader.eso_file import EsoFile, get_results, IncompleteFile
from eso_reader.building_eso_file import BuildingEsoFile
from eso_reader.mini_classes import Variable

from queue import Queue
from multiprocessing import Manager, cpu_count
from esopie.view_widget import View
from random import randint
from esopie.threads import EsoFileWatcher, GuiMonitor, ResultsFetcher


class ViewTools(QFrame):
    """
    A class to represent an application toolbar.

    """
    settingsChanged = Signal()

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
        self.filter_icon.setPixmap(QPixmap("../icons/filter_list_white.png"))
        self.filter_line_edit = LineEdit(self)

        # ~~~~ Timer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Timer to delay firing of the 'text_edited' event
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._filter_view)

        self.set_up_view_tools()

    def set_up_view_tools(self):
        """ Create tools, settings and search line for the view. """
        # ~~~~ Widget to hold tree view tools ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        view_tools_layout = QHBoxLayout(self)
        view_tools_layout.setSpacing(6)
        view_tools_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Widget to hold tree view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btn_widget = QWidget(self)
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(0)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Add view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btn_layout.addWidget(self.expand_all_btn)
        btn_layout.addWidget(self.collapse_all_btn)
        btn_layout.addWidget(self.tree_view_btn)

        # ~~~~ Create view search line edit ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.setPlaceholderText("filter...")
        self.filter_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.filter_line_edit.setFixedWidth(160)

        # ~~~~ Set up tree button  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tree_view_btn.setCheckable(True)
        self.tree_view_btn.setChecked(True)
        self.collapse_all_btn.setEnabled(True)
        self.expand_all_btn.setEnabled(True)

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # ~~~~ Add child widgets to treeTools layout ~~~~~~~~~~~~~~~~~~~~~~~~
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
        self.settingsChanged.emit()
