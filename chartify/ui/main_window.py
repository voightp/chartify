import contextlib
import ctypes
import shutil
from functools import partial
from pathlib import Path
from typing import Optional, Tuple, List, Union, Set, Dict

import pandas as pd
from PySide2.QtCore import QSize, Qt, QCoreApplication, Signal, QPoint, QTimer, QModelIndex
from PySide2.QtGui import QIcon, QKeySequence, QColor
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtWidgets import (
    QWidget,
    QSplitter,
    QHBoxLayout,
    QToolButton,
    QAction,
    QFileDialog,
    QSizePolicy,
    QFrame,
    QMainWindow,
    QStatusBar,
    QMenu,
    QLabel,
    QLineEdit,
    QSpacerItem,
    QVBoxLayout,
    QStackedWidget,
)
from esofile_reader.convertor import all_rate_or_energy
from esofile_reader.df.level_names import *
from esofile_reader.pqt.parquet_storage import ParquetStorage, ParquetFile

from chartify.settings import Settings, OutputType
from chartify.ui.buttons import MenuButton
from chartify.ui.css_theme import Palette, CssParser
from chartify.ui.dialogs import ConfirmationDialog, SingleInputDialog, DoubleInputDialog
from chartify.ui.drop_frame import DropFrame
from chartify.ui.icon_painter import Pixmap, draw_filled_circle_icon
from chartify.ui.progress_widget import ProgressContainer
from chartify.ui.stacked_widget import StackedWidget
from chartify.ui.tab_widget import TabWidget
from chartify.ui.toolbar import Toolbar
from chartify.ui.treeview import TreeView, ViewMask, ViewType
from chartify.ui.treeview_model import (
    ViewModel,
    is_variable_attr_identical,
    stringify_view_variable,
    VV,
    PROXY_UNITS_LEVEL,
)


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QMainWindow):
    """ Main application instance. """

    QCoreApplication.setOrganizationName("chartify")
    QCoreApplication.setOrganizationDomain("chartify.foo")
    QCoreApplication.setApplicationName("chartify")

    paletteUpdated = Signal()
    tabChanged = Signal(int)
    treeNodeUpdated = Signal(str)
    selectionChanged = Signal(list)
    variableRenameRequested = Signal(list, VV, VV)
    variableRemoveRequested = Signal(list, list)
    aggregationRequested = Signal(list, str, list, str, str)
    fileProcessingRequested = Signal(list)
    syncFileProcessingRequested = Signal(list)
    fileRenameRequested = Signal(int, str)
    fileRemoveRequested = Signal(int)
    appCloseRequested = Signal()

    _CLOSE_FLAG = False

    def __init__(self):
        super().__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setWindowTitle("chartify")
        self.setFocusPolicy(Qt.StrongFocus)
        self.resize(QSize(*Settings.SIZE))
        self.move(QPoint(*Settings.POSITION))

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act = QAction("Load file | files", self)
        self.load_file_act.setShortcut(QKeySequence("Ctrl+L"))
        self.close_all_act = QAction("Close all", self)
        self.close_all_act.setEnabled(False)
        self.remove_variables_act = QAction("Delete", self)
        self.remove_variables_act.setEnabled(False)
        self.sum_act = QAction("Sum", self)
        self.sum_act.setShortcut(QKeySequence("Ctrl+T"))
        self.sum_act.setEnabled(False)
        self.mean_act = QAction("Mean", self)
        self.mean_act.setShortcut(QKeySequence("Ctrl+M"))
        self.mean_act.setEnabled(False)
        self.rename_variable_act = QAction("Rename", self)
        self.rename_variable_act.setEnabled(False)
        self.collapse_all_act = QAction("Collapse All", self)
        self.collapse_all_act.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.expand_all_act = QAction("Expand All", self)
        self.expand_all_act.setShortcut(QKeySequence("Ctrl+E"))
        self.tree_act = QAction("Tree", self)
        self.tree_act.setShortcut(QKeySequence("Ctrl+T"))
        self.tree_act.setCheckable(True)
        self.tree_act.setChecked(True)
        self.save_act = QAction("Save", self)
        self.save_act.setShortcut(QKeySequence("Ctrl+S"))
        self.save_as_act = QAction("Save as", self)
        self.save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))

        # add actions to main window to allow shortcuts
        self.addActions(
            [
                self.remove_variables_act,
                self.sum_act,
                self.mean_act,
                self.rename_variable_act,
                self.collapse_all_act,
                self.expand_all_act,
                self.tree_act,
            ]
        )

        # ~~~~ Main Window widgets ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.central_wgt = QWidget(self)
        self.central_layout = QHBoxLayout(self.central_wgt)
        self.central_layout.setSpacing(0)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.central_wgt)
        self.central_splitter = QSplitter(self.central_wgt)
        self.central_splitter.setOrientation(Qt.Horizontal)
        self.central_layout.addWidget(self.central_splitter)

        # ~~~~ Left hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt = DropFrame(self.central_splitter, Settings.EXTENSIONS)
        self.left_main_wgt.setObjectName("leftMainWgt")
        self.left_main_layout = QHBoxLayout(self.left_main_wgt)
        left_side_policy = QSizePolicy()
        left_side_policy.setHorizontalPolicy(QSizePolicy.Minimum)
        left_side_policy.setHorizontalStretch(0)
        self.left_main_wgt.setSizePolicy(left_side_policy)
        self.left_main_layout.setSpacing(2)
        self.left_main_layout.setContentsMargins(0, 0, 0, 0)
        self.central_splitter.addWidget(self.left_main_wgt)

        # ~~~~ Left hand Tools Widget ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar = Toolbar(self.left_main_wgt)
        self.toolbar.sum_btn.setDefaultAction(self.sum_act)
        self.toolbar.mean_btn.setDefaultAction(self.mean_act)
        self.toolbar.remove_btn.setDefaultAction(self.remove_variables_act)
        self.toolbar.rename_btn.setDefaultAction(self.rename_variable_act)
        self.toolbar.sum_btn.setDefaultAction(self.sum_act)
        self.left_main_layout.addWidget(self.toolbar)

        # ~~~~ Left hand View widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_wgt = QFrame(self.left_main_wgt)
        self.view_wgt.setObjectName("viewWidget")
        self.view_layout = QVBoxLayout(self.view_wgt)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.setSpacing(0)
        if Settings.MIRRORED:
            self.left_main_layout.insertWidget(0, self.view_wgt)
        else:
            self.left_main_layout.addWidget(self.view_wgt)

        # ~~~~ Left hand Tab widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.output_stacked_widget = QStackedWidget(self)
        self.output_stacked_widget.setMinimumWidth(400)
        self.view_layout.addWidget(self.output_stacked_widget)

        self.drop_button = QToolButton()
        self.drop_button.setObjectName("dropButton")
        self.drop_button.setText("Choose a file or drag it here...")
        self.drop_button.clicked.connect(self.load_files_from_fs)

        self.totals_button = QToolButton()
        self.totals_button.setObjectName("totalsButton")
        self.totals_button.setText("Click here to create a totals file...")
        self.totals_button.clicked.connect(self.create_totals_file())

        self.diff_button = QToolButton()
        self.diff_button.setObjectName("diffButton")
        self.diff_button.setText("Click here to create a difference file...")
        self.diff_button.clicked.connect(self.create_diff_file)

        self.standard_tab_wgt = TabWidget(self.view_wgt, self.drop_button)
        self.totals_tab_wgt = TabWidget(self.view_wgt, self.totals_button)
        self.diff_tab_wgt = TabWidget(self.view_wgt, self.diff_button)

        self.output_stacked_widget.addWidget(self.standard_tab_wgt)
        self.output_stacked_widget.addWidget(self.totals_tab_wgt)
        self.output_stacked_widget.addWidget(self.diff_tab_wgt)

        self.output_stacked_widget.setCurrentIndex(Settings.OUTPUTS_ENUM)

        # ~~~~ Left hand Tab Tools  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools = QFrame(self.view_wgt)
        self.setObjectName("viewTools")
        view_tools_layout = QHBoxLayout(self.view_tools)
        view_tools_layout.setSpacing(6)
        view_tools_layout.setContentsMargins(0, 0, 0, 0)

        btn_widget = QWidget(self.view_tools)
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(0)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Set up view buttons  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tree_view_btn = QToolButton(self.view_tools)
        self.tree_view_btn.setObjectName("treeButton")
        self.tree_view_btn.setDefaultAction(self.tree_act)

        self.collapse_all_btn = QToolButton(self.view_tools)
        self.collapse_all_btn.setObjectName("collapseButton")
        self.collapse_all_btn.setDefaultAction(self.collapse_all_act)

        self.expand_all_btn = QToolButton(self.view_tools)
        self.expand_all_btn.setObjectName("expandButton")
        self.expand_all_btn.setDefaultAction(self.expand_all_act)

        self.filter_icon = QLabel(self.view_tools)
        self.filter_icon.setObjectName("filterIcon")

        btn_layout.addWidget(self.expand_all_btn)
        btn_layout.addWidget(self.collapse_all_btn)
        btn_layout.addWidget(self.tree_view_btn)

        # ~~~~ Line edit ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.type_line_edit = QLineEdit(self.view_tools)
        self.type_line_edit.setPlaceholderText("type...")
        self.type_line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.type_line_edit.setFixedWidth(100)

        self.key_line_edit = QLineEdit(self.view_tools)
        self.key_line_edit.setPlaceholderText("key...")
        self.key_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.key_line_edit.setFixedWidth(100)

        self.units_line_edit = QLineEdit(self.view_tools)
        self.units_line_edit.setPlaceholderText("units...")
        self.units_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.units_line_edit.setFixedWidth(50)

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        view_tools_layout.addWidget(self.filter_icon)
        view_tools_layout.addWidget(self.type_line_edit)
        view_tools_layout.addWidget(self.key_line_edit)
        view_tools_layout.addWidget(self.units_line_edit)
        view_tools_layout.addItem(spacer)
        view_tools_layout.addWidget(btn_widget)
        self.view_layout.addWidget(self.view_tools)

        # ~~~~ Timer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Timer to delay firing of the 'text_edited' event
        self.timer = QTimer()
        self.timer.setSingleShot(True)

        # ~~~~ Right hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.right_main_wgt = QWidget(self.central_splitter)
        right_side_policy = QSizePolicy()
        right_side_policy.setHorizontalPolicy(QSizePolicy.Expanding)
        right_side_policy.setHorizontalStretch(1)
        self.right_main_wgt.setSizePolicy(right_side_policy)
        self.right_main_layout = QHBoxLayout(self.right_main_wgt)
        self.right_main_layout.setSpacing(0)
        self.right_main_layout.setContentsMargins(0, 0, 0, 0)
        if Settings.MIRRORED:
            self.central_splitter.insertWidget(0, self.right_main_wgt)
        else:
            self.central_splitter.addWidget(self.right_main_wgt)

        # ~~~~ Right hand Chart Area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.main_chart_widget = QFrame(self.right_main_wgt)
        self.main_chart_layout = QHBoxLayout(self.main_chart_widget)
        self.main_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.main_chart_widget.setMinimumWidth(600)
        self.right_main_layout.addWidget(self.main_chart_widget)

        self.web_view = QWebEngineView(self)
        self.main_chart_layout.addWidget(self.web_view)

        # ~~~~ Status bar ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.status_bar = QStatusBar(self)
        self.status_bar.setFixedHeight(20)
        self.setStatusBar(self.status_bar)

        self.progress_container = ProgressContainer(self.status_bar)
        self.status_bar.addWidget(self.progress_container)

        # ~~~~ Palettes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.palettes = Palette.parse_palettes(Settings.PALETTE_PATH)
        Settings.PALETTE = self.palettes[Settings.PALETTE_NAME]

        # ~~~~ Scheme button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        actions, default_action = self.create_scheme_actions()

        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions(actions)

        self.scheme_btn = QToolButton(self)
        self.scheme_btn.setPopupMode(QToolButton.InstantPopup)
        self.scheme_btn.setDefaultAction(default_action)
        self.scheme_btn.setMenu(menu)
        self.scheme_btn.setObjectName("schemeButton")
        self.scheme_btn.triggered.connect(lambda act: self.scheme_btn.setDefaultAction(act))

        # ~~~~ Swap button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.swap_btn = QToolButton(self)
        self.swap_btn.clicked.connect(self.mirror_layout)
        self.swap_btn.setObjectName("swapButton")

        self.status_bar.addPermanentWidget(self.swap_btn)
        self.status_bar.addPermanentWidget(self.scheme_btn)

        # ~~~~ Menus ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.mini_menu = QWidget(self.toolbar)
        self.mini_menu_layout = QHBoxLayout(self.mini_menu)
        self.mini_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.mini_menu_layout.setSpacing(0)
        self.toolbar.layout.insertWidget(0, self.mini_menu)

        self.load_file_btn = MenuButton("Load file | files", self)
        self.load_file_btn.setObjectName("fileButton")
        self.load_file_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions([self.load_file_act, self.close_all_act])
        self.load_file_btn.setMenu(menu)

        self.save_btn = MenuButton("Save", self)
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions([self.save_act, self.save_as_act])
        self.save_btn.setMenu(menu)

        self.about_btn = MenuButton("About", self)
        self.about_btn.setObjectName("aboutButton")
        self.about_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions([])
        self.about_btn.setMenu(menu)

        self.mini_menu_layout.addWidget(self.load_file_btn)
        self.mini_menu_layout.addWidget(self.save_btn)
        self.mini_menu_layout.addWidget(self.about_btn)

        # ~~~~ Set up app appearance ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self._temp_icons = []
        self.load_css_and_icons()
        self.central_splitter.setSizes(Settings.SPLIT)

        # ~~~~ Connect main ui user actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.connect_ui_signals()
        self.connect_tab_widget_signals()
        self.connect_view_tools_signals()
        self.connect_toolbar_signals()

    @property
    def current_tab_widget(self) -> TabWidget:
        """ Currently displayed tab widget. """
        return self.output_stacked_widget.currentWidget()

    @property
    def current_file_widget(self) -> StackedWidget:
        """ Currently chosen file stacked widget. """
        return self.current_tab_widget.currentWidget()

    @property
    def current_view(self) -> TreeView:
        """ Currently selected outputs file. """
        return self.current_file_widget.currentWidget()

    @property
    def current_model(self) -> ViewModel:
        """ Currently selected source model."""
        return self.current_view.source_model

    @property
    def tab_widgets(self) -> List[TabWidget]:
        """ All available tab widgets. """
        return [self.standard_tab_wgt, self.totals_tab_wgt, self.diff_tab_wgt]

    def update_settings(self):
        """ Save settings into class attributes. """
        Settings.SIZE = (self.width(), self.height())
        Settings.POSITION = (self.x(), self.y())
        Settings.SPLIT = self.central_splitter.sizes()
        Settings.ALL_FILES = self.toolbar.all_files_toggle.isChecked()
        Settings.ALL_TABLES = self.toolbar.all_tables_toggle.isChecked()
        Settings.ENERGY_UNITS = self.toolbar.energy_btn.data()
        Settings.RATE_UNITS = self.toolbar.rate_btn.data()
        Settings.UNITS_SYSTEM = self.toolbar.units_system_button.data()
        Settings.RATE_TO_ENERGY = self.toolbar.rate_energy_btn.isChecked()
        Settings.OUTPUTS_ENUM = self.toolbar.outputs_button_group.checkedId()
        Settings.SHOW_SOURCE_UNITS = self.toolbar.source_units_toggle.isChecked()

    def closeEvent(self, event):
        """ Shutdown all the background stuff. """
        # it's needed to terminate threads in controller
        # and close app programmatically
        self.appCloseRequested.emit()
        if self._CLOSE_FLAG:
            self.update_settings()
            # TODO enable once main window polished
            # Settings.save_settings_to_json()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:
            if not self.current_tab_widget.is_empty():
                self.current_view.deselect_all_variables()
        elif event.key() == Qt.Key_Delete:
            if self.hasFocus() and not self.current_tab_widget.is_empty():
                self.remove_variables_act.trigger()

    def create_scheme_actions(self) -> Tuple[List[QAction], QAction]:
        """ Create actions to change application color scheme. """
        actions = []
        def_act = None
        for name, colors in self.palettes.items():
            act = QAction(name, self)
            act.triggered.connect(partial(self.on_color_scheme_changed, name))
            c1 = QColor(*colors.get_color_tuple("SECONDARY_COLOR"))
            c2 = QColor(*colors.get_color_tuple("BACKGROUND_COLOR"))
            act.setIcon(
                draw_filled_circle_icon(
                    Settings.ICON_LARGE_SIZE, c1, c2=c2, border_color=QColor(255, 255, 255)
                )
            )
            actions.append(act)
            if name == Settings.PALETTE_NAME:
                def_act = act
        return actions, def_act

    def load_icons(self):
        """ Load application icons. """
        # this sets toolbar icon on win 7
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("foo")

        c1 = Settings.PALETTE.get_color_tuple("PRIMARY_TEXT_COLOR")
        c2 = Settings.PALETTE.get_color_tuple("SECONDARY_TEXT_COLOR")

        r = Settings.SOURCE_ICONS_DIR
        self.setWindowIcon(Pixmap(Path(r, "smile.png"), 255, 255, 255))

        self.load_file_btn.setIcon(QIcon(Pixmap(Path(r, "file.png"), *c1)))
        self.save_btn.setIcon(QIcon(Pixmap(Path(r, "save.png"), *c1)))
        self.about_btn.setIcon(QIcon(Pixmap(Path(r, "help.png"), *c1)))
        self.close_all_act.setIcon(QIcon(Pixmap(Path(r, "remove.png"), *c1)))
        self.load_file_act.setIcon(QIcon(Pixmap(Path(r, "add_file.png"), *c1)))

        self.drop_button.setIcon(Pixmap(Path(r, "drop_file.png"), *c1))
        self.drop_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.drop_button.setIconSize(Settings.ICON_LARGE_SIZE)

        self.totals_button.setIcon(Pixmap(Path(r, "add_file.png"), *c1))
        self.totals_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.totals_button.setIconSize(Settings.ICON_LARGE_SIZE)

        self.diff_button.setIcon(Pixmap(Path(r, "add_file.png"), *c1))
        self.diff_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.diff_button.setIconSize(Settings.ICON_LARGE_SIZE)

        enabled_off = (QIcon.Normal, QIcon.Off)
        disabled_off = (QIcon.Disabled, QIcon.Off)
        disabled_on = (QIcon.Disabled, QIcon.On)
        disabled_a = 0.6

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "sigma.png"), *c1), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "sigma.png"), *c1, a=disabled_a), *disabled_off)
        self.sum_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "mean.png"), *c1), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "mean.png"), *c1, a=disabled_a), *disabled_off)
        self.mean_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "remove.png"), *c1), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "remove.png"), *c1, a=disabled_a), *disabled_off)
        self.remove_variables_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "pen.png"), *c1), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "pen.png"), *c1, a=disabled_a), *disabled_off)
        self.rename_variable_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "plain_view.png"), *c2), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "plain_view.png"), *c2, a=disabled_a), *disabled_off)
        icon.addPixmap(Pixmap(Path(r, "tree_view.png"), *c2), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "tree_view.png"), *c2, a=disabled_a), *disabled_on)
        self.tree_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "unfold_less.png"), *c2), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "unfold_less.png"), *c2, a=disabled_a), *disabled_off)
        self.collapse_all_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "unfold_more.png"), *c2), *enabled_off)
        icon.addPixmap(Pixmap(Path(r, "unfold_more.png"), *c2, a=disabled_a), *disabled_off)
        self.expand_all_act.setIcon(icon)

    def load_css_and_icons(self) -> None:
        """ Update application appearance. """
        icons_dir = Path(Settings.APP_TEMP_DIR, "icons")
        shutil.rmtree(icons_dir, ignore_errors=True)
        icons_dir.mkdir()
        css, icon_paths = CssParser.parse_css_files(
            Settings.CSS_DIR, Settings.PALETTE, Settings.SOURCE_ICONS_DIR, icons_dir,
        )
        self._temp_icons = icon_paths
        # css needs to be cleared to repaint the window properly
        self.setStyleSheet("")
        self.setStyleSheet(css)
        self.load_icons()

    def mirror_layout(self):
        """ Mirror the layout. """
        self.left_main_layout.addItem(self.left_main_layout.takeAt(0))
        self.central_splitter.insertWidget(0, self.central_splitter.widget(1))
        Settings.MIRRORED = not Settings.MIRRORED
        Settings.SPLIT = self.central_splitter.sizes()

    def get_all_file_widgets(self) -> List[StackedWidget]:
        """ Gather all file stack widgets based on toolbar settings. """
        if self.toolbar.all_files_toggle.isChecked():
            file_widgets = self.current_tab_widget.get_all_children()
        else:
            file_widgets = [self.current_file_widget]
        return file_widgets

    def filter_models(self, view_models: List[ViewModel]) -> List[ViewModel]:
        """ Return models of the same type (SIMPLE, TREE) as the current one. """
        return [m for m in view_models if m.is_simple is self.current_model.is_simple]

    def get_all_models(self) -> List[ViewModel]:
        """ Gather models based on toolbar settings. """
        models = []
        for file_widget in self.get_all_file_widgets():
            if self.toolbar.all_tables_toggle.isChecked():
                models.extend(file_widget.all_view_models)
            else:
                table_name = self.current_file_widget.current_table_name
                with contextlib.suppress(KeyError):
                    models.append(file_widget.get_view_model(table_name))
        return self.filter_models(models)

    def get_all_other_models(self) -> List[ViewModel]:
        """ Gather models based on toolbar settings. """
        models = self.get_all_models()
        models.remove(self.current_model)
        return models

    def on_tree_node_changed(self, treeview: TreeView) -> None:
        """ Update current view on tree node column change. """
        self.update_treeview(treeview)

    def on_item_double_clicked(
        self,
        treeview: TreeView,
        row: int,
        parent_index: Optional[QModelIndex],
        old_view_variable: VV,
    ) -> None:
        """ Update variable name on view double click event. """
        old_key = old_view_variable.key
        key_blocker = set(treeview.get_items_text_for_column(KEY_LEVEL))
        key_blocker.remove(old_key)
        if treeview.source_model.is_simple:
            res = self.confirm_rename_simple_variable(old_key, key_blocker)
        else:
            old_type = old_view_variable.type
            type_blocker = set(treeview.get_items_text_for_column(TYPE_LEVEL))
            type_blocker.remove(old_type)
            res = self.confirm_rename_variable(old_key, old_type, key_blocker, type_blocker)

        if res is not None:
            key = res if treeview.view_type is ViewType.SIMPLE else res[0]
            type_ = None if treeview.view_type is ViewType.SIMPLE else res[1]
            units = old_view_variable.units
            new_view_variable = VV(key=key, type=type_, units=units)
            treeview.update_variable(row, parent_index, new_view_variable)
            if models := self.get_all_other_models():
                self.variableRenameRequested.emit(models, old_view_variable, new_view_variable)

    def on_remove_variables_triggered(self):
        """ Handle remove variable action trigger event. """
        if selected := self.current_view.get_selected_view_variable():
            if self.confirm_remove_variables(selected):
                self.current_model.delete_variables(selected)
                self.on_selection_cleared()
                if models := self.get_all_other_models():
                    self.variableRemoveRequested.emit(models, selected)

    def on_aggregation_requested(self, func: str) -> None:
        """ Handle variable aggregation action trigger event. """
        if view_variables := self.current_view.get_selected_view_variable():
            if self.current_view.view_type is ViewType.SIMPLE:
                res = self.confirm_aggregate_simple_variables(view_variables, func)
            else:
                res = self.confirm_aggregate_variables(view_variables, func)
            if res:
                if isinstance(res, tuple):
                    new_key, new_type = res
                else:
                    new_key = res
                    new_type = None
                self.current_view.aggregate_variables(view_variables, func, new_key, new_type)
                if models := self.get_all_other_models():
                    self.aggregationRequested.emit(
                        models, func, view_variables, new_key, new_type
                    )

    def fetch_results(self) -> pd.DataFrame:
        """ Retrieve results for currently selected variables. """
        if view_variables := self.current_view.get_selected_view_variable():
            models = self.get_all_models()
            frames = []
            for model in models:
                df = model.get_results(view_variables, **self.toolbar.current_units)
                if df is not None:
                    frames.append(df)
            return pd.concat(frames, axis=1, sort=False)

    def on_sum_action_triggered(self):
        """ Handle sum action trigger. """
        self.on_aggregation_requested("sum")

    def on_mean_action_triggered(self):
        """ Handle avg action trigger. """
        self.on_aggregation_requested("mean")

    def on_rename_action_triggered(self):
        """ Handle rename action trigger. """
        selected = self.current_view.get_selected_view_variable()
        selection = self.current_model.get_matching_selection(selected)
        self.on_item_double_clicked(
            self.current_view,
            selection.indexes()[0].row(),
            selection.indexes()[0].parent(),
            selected[0],
        )

    def add_file_widget(self, file: ParquetFile):
        """ Add processed file to tab widget corresponding to data type. """
        tab_widgets_switch = {
            ParquetFile.TOTALS: self.totals_tab_wgt,
            ParquetFile.DIFF: self.diff_tab_wgt,
        }
        output_type_switch = {
            ParquetFile.TOTALS: OutputType.TOTALS,
            ParquetFile.DIFF: OutputType.DIFFERENCE,
        }

        tab_widget = tab_widgets_switch.get(file.file_type, self.standard_tab_wgt)
        output_type = output_type_switch.get(file.file_type, OutputType.STANDARD)
        file_widget = StackedWidget(tab_widget)
        for name in file.table_names:
            model = ViewModel(name, file)
            view = TreeView(model, output_type)
            view.selectionCleared.connect(self.on_selection_cleared)
            view.selectionPopulated.connect(self.on_selection_populated)
            view.treeNodeChanged.connect(self.on_tree_node_changed)
            view.itemDoubleClicked.connect(self.on_item_double_clicked)
            file_widget.addWidget(view)
        tab_widget.addTab(file_widget, file.file_name)

    def expand_all(self):
        """ Expand all tree view items. """
        if not self.current_tab_widget.is_empty():
            self.current_view.expandAll()

    def collapse_all(self):
        """ Collapse all tree view items. """
        if not self.current_tab_widget.is_empty():
            self.current_view.collapseAll()

    def save_storage_to_fs(self) -> Optional[Path]:
        """ Get file path of the """
        path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save project",
            filter=f"CFS (*{ParquetStorage.EXT})",
            dir=str(Settings.SAVE_PATH) if Settings.SAVE_PATH else None,
        )
        if path:
            path = Path(path)
            Settings.SAVE_PATH = path.parent
            return path

    def load_files_from_paths_synchronously(self, paths: List[Union[str, Path]]):
        """ Load results from given paths synchronously.  """
        Settings.LOAD_PATH = Path(paths[0]).parent
        self.syncFileProcessingRequested.emit(paths)

    def load_files_from_paths(self, paths: List[Path]):
        """ Load results from given paths using multiprocessing.  """
        Settings.LOAD_PATH = paths[0].parent
        self.fileProcessingRequested.emit(paths)

    def create_totals_file(self):
        # TODO implement new dialog
        pass

    def create_diff_file(self):
        # TODO implement new dialog
        pass

    def load_files_from_fs(self):
        """ Let user select files to processed from filesystem. """
        dir_ = str(Settings.LOAD_PATH) if Settings.LOAD_PATH else None
        extensions_str = " ".join(["*" + ext for ext in Settings.EXTENSIONS])
        file_paths, _ = QFileDialog.getOpenFileNames(
            parent=self,
            caption="Load Project / Eso File",
            filter=f"FILES ({extensions_str})",
            dir=dir_,
        )
        if file_paths:
            self.load_files_from_paths([Path(p) for p in file_paths])

    def on_color_scheme_changed(self, name: str):
        """ Update the application palette. """
        if name != Settings.PALETTE_NAME:
            Settings.PALETTE = self.palettes[name]
            Settings.PALETTE_NAME = name
            self.load_css_and_icons()
            self.paletteUpdated.emit()

    def connect_ui_signals(self):
        """ Create actions which depend on user actions """
        # ~~~~ Widget Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt.fileDropped.connect(self.fileProcessingRequested.emit)

        # ~~~~ Actions Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act.triggered.connect(self.load_files_from_fs)
        self.tree_act.toggled.connect(self.on_tree_act_checked)
        self.collapse_all_act.triggered.connect(self.collapse_all)
        self.expand_all_act.triggered.connect(self.expand_all)
        self.remove_variables_act.triggered.connect(self.on_remove_variables_triggered)
        self.rename_variable_act.triggered.connect(self.on_rename_action_triggered)
        self.sum_act.triggered.connect(self.on_sum_action_triggered)
        self.mean_act.triggered.connect(self.on_mean_action_triggered)

    def show_source_units(self) -> bool:
        """ Check if source units should be visible. """
        return self.toolbar.source_units_toggle.isChecked()

    def get_filter_dict(self) -> Dict[str, str]:
        """ Retrieve filter inputs from ui, text uses lower. """
        pairs = zip(
            [KEY_LEVEL, TYPE_LEVEL, PROXY_UNITS_LEVEL],
            [
                self.key_line_edit.text(),
                self.type_line_edit.text(),
                self.units_line_edit.text(),
            ],
        )
        return {key: text.lower() for key, text in pairs if text.strip()}

    def on_output_type_change_requested(self, index: int) -> None:
        """ Show tab widget corresponding to the given radio button. """
        self.output_stacked_widget.setCurrentIndex(index)
        if self.current_tab_widget.is_empty():
            self.enable_actions_for_empty_layout()
        else:
            self.enable_actions_for_file_widget(self.current_file_widget)
            self.update_treeview(self.current_view)

    def enable_actions_for_empty_layout(self):
        """ Enable or disable actions as it suits for an empty layout. """
        self.close_all_act.setEnabled(False)

        self.toolbar.enable_rate_to_energy(True)
        self.toolbar.update_table_buttons(table_indexes={}, selected="")

        self.tree_act.setEnabled(True)
        self.expand_all_act.setEnabled(True)
        self.collapse_all_act.setEnabled(True)
        self.toolbar.enable_rate_to_energy(True)

        self.remove_variables_act.setEnabled(False)
        self.sum_act.setEnabled(False)
        self.mean_act.setEnabled(False)

    def enable_selection_actions(self, view_variables: List[VV]):
        """  Update toolbar actions to match current selection. """
        self.remove_variables_act.setEnabled(False)
        self.rename_variable_act.setEnabled(False)
        self.sum_act.setEnabled(False)
        self.mean_act.setEnabled(False)
        if view_variables:
            self.remove_variables_act.setEnabled(True)
            if len(view_variables) == 1:
                self.rename_variable_act.setEnabled(True)
            elif len(view_variables) > 1:
                units = [var.units for var in view_variables]
                if len(set(units)) == 1 or (
                    all_rate_or_energy(units) and self.current_model.allow_rate_to_energy
                ):
                    self.sum_act.setEnabled(True)
                    self.mean_act.setEnabled(True)

    def enable_actions_for_view(self, view: TreeView) -> None:
        """ Enable or disable actions related to given view. """
        allow_tree = not view.source_model.is_simple
        self.tree_act.setEnabled(allow_tree)
        self.expand_all_act.setEnabled(allow_tree)
        self.collapse_all_act.setEnabled(allow_tree)
        self.toolbar.enable_rate_to_energy(view.source_model.allow_rate_to_energy)
        self.enable_selection_actions(view.selected_view_variable)

    def enable_actions_for_file_widget(self, file_widget: StackedWidget) -> None:
        """ Enable or disable actions related to given file. """
        self.close_all_act.setEnabled(True)
        self.toolbar.update_table_buttons(
            file_widget.name_indexes, file_widget.current_table_name
        )
        self.enable_actions_for_view(file_widget.current_treeview)

    def on_tab_changed(
        self,
        tab_widget: TabWidget,
        previous_file_widget: StackedWidget,
        file_widget: StackedWidget,
    ) -> None:
        """ Handle ui tab change. """
        if tab_widget is self.current_tab_widget:
            if file_widget is None:
                self.enable_actions_for_empty_layout()
            else:
                if previous_file_widget is None:
                    ref_treeview = None
                else:
                    ref_treeview = previous_file_widget.current_treeview
                next_treeview = file_widget.get_next_treeview(previous_file_widget)

                if next_treeview is not file_widget.current_treeview:
                    file_widget.set_treeview(next_treeview)
                self.enable_actions_for_file_widget(file_widget)
                self.update_treeview(next_treeview, ref_treeview)

    def on_table_change_requested(self, index_or_name: Union[int, str]):
        """ Change table on a current file widget. """
        if isinstance(index_or_name, int):
            next_treeview = self.current_file_widget.widget(index_or_name)
        else:
            next_treeview = self.current_file_widget.get_treeview(index_or_name)
        ref_treeview = self.current_file_widget.currentWidget()
        self.enable_actions_for_view(next_treeview)
        self.current_file_widget.set_treeview(next_treeview)
        self.update_treeview(next_treeview, ref_treeview)

    def on_selection_populated(self, view_variables: List[VV]):
        """ Update ui actions related to given selection. """
        self.enable_selection_actions(view_variables)
        self.selectionChanged.emit(view_variables)

    def on_selection_cleared(self):
        """ Update ui actions after clearing selection. """
        self.enable_selection_actions([])
        self.selectionChanged.emit([])

    def get_all_tab_names(self):
        """ Fetch all tab names from all tab widgets. """
        names = []
        for tab_widget in self.tab_widgets:
            for i in range(tab_widget.count()):
                names.append(tab_widget.tabText(i))
        return names

    def on_tab_bar_double_clicked(self, tab_widget: TabWidget, tab_index: int):
        """ Rename file associated with given tab. """
        name = tab_widget.tabText(tab_index)
        names = set(self.get_all_tab_names())
        names.remove(name)
        new_name = self.confirm_rename_file(name, names)
        if new_name is not None and new_name != name:
            id_ = tab_widget.widget(tab_index).file_id
            tab_widget.setTabText(tab_index, new_name)
            self.fileRenameRequested.emit(id_, new_name)

    def on_tab_close_requested(self, tab_widget: TabWidget, tab_index: int):
        """ Delete file associated with given tab. """
        treeview = tab_widget.widget(tab_index).current_treeview
        name = tab_widget.tabText(tab_index)
        if self.confirm_delete_file(name):
            if treeview is self.current_view:
                self.current_tab_widget.set_next_tab_before_delete(tab_index)
            tab_widget.removeTab(tab_index)
            treeview.deleteLater()
            self.fileRemoveRequested.emit(treeview.id_)

    def connect_tab_widget_signals(self):
        """ Connect signals emitted by tab widgets. """
        for tab_widget in self.tab_widgets:
            tab_widget.closeTabRequested.connect(self.on_tab_close_requested)
            tab_widget.currentTabChanged.connect(self.on_tab_changed)
            tab_widget.tabRenameRequested.connect(self.on_tab_bar_double_clicked)

    def on_source_units_toggled(self, checked: bool):
        """ Hide or show source units column as requested. """
        if not self.current_tab_widget.is_empty():
            self.current_view.hide_section(UNITS_LEVEL, not checked)

    def on_units_changed(self) -> None:
        """ Update units on current view to correspond with toolbar settings. """
        if not self.current_tab_widget.is_empty():
            self.current_view.update_units(**self.toolbar.current_units)

    def on_custom_units_toggled(self) -> None:
        """ Update rate to energy button state on custom units toggle. """
        if self.current_tab_widget.is_empty() or self.current_view.allow_rate_to_energy:
            self.toolbar.enable_rate_to_energy(True)
        else:
            self.toolbar.rate_energy_btn.setEnabled(False)

    def connect_toolbar_signals(self):
        """ Connect signals emitted by toolbar buttons. """
        self.toolbar.tableChangeRequested.connect(self.on_table_change_requested)
        self.toolbar.outputTypeChangeRequested.connect(self.on_output_type_change_requested)
        self.toolbar.customUnitsToggled.connect(self.on_custom_units_toggled)
        self.toolbar.unitsChanged.connect(self.on_units_changed)
        self.toolbar.source_units_toggle.stateChanged.connect(self.on_source_units_toggled)

    def update_treeview(self, treeview: TreeView, ref_treeview: TreeView = None) -> None:
        with ViewMask(
            treeview=treeview,
            ref_treeview=ref_treeview,
            filter_dict=self.get_filter_dict(),
            show_source_units=self.show_source_units(),
        ) as mask:
            mask.update_treeview(
                treeview,
                is_tree=self.tree_act.isChecked(),
                units_kwargs=self.toolbar.current_units,
            )

    def on_tree_act_checked(self, checked: bool):
        """ Update view when view type changes. """
        self.collapse_all_act.setEnabled(checked)
        self.expand_all_act.setEnabled(checked)
        if self.current_view is not None:
            self.update_treeview(self.current_view)

    def on_text_edited(self):
        """ Delay firing a text edited event. """
        self.timer.start(200)

    def on_filter_timeout(self):
        """ Apply a filter when the filter text is edited. """
        if not self.current_tab_widget.is_empty():
            self.current_view.filter_view(self.get_filter_dict())

    def connect_view_tools_signals(self):
        """ Connect signals emitted by filtering buttons. """
        self.type_line_edit.textEdited.connect(self.on_text_edited)
        self.key_line_edit.textEdited.connect(self.on_text_edited)
        self.units_line_edit.textEdited.connect(self.on_text_edited)
        self.timer.timeout.connect(self.on_filter_timeout)

    def confirm_rename_file(self, name: str, other_names: Set[str]) -> Optional[str]:
        """ Execute a dialog requesting new file name. """
        dialog = SingleInputDialog(
            self,
            title="Enter a new file name.",
            input1_name="Name",
            input1_text=name,
            input1_blocker=other_names,
        )
        if dialog.exec_() == 1:
            return dialog.input1_text

    def get_files_and_tables_text(self) -> str:
        """ Get text to to inform which tables and files will be modified. . """
        table_name = self.current_file_widget.current_table_name
        file_name = self.current_tab_widget.name
        all_files = self.toolbar.all_files_toggle.isChecked()
        all_tables = self.toolbar.all_tables_toggle.isChecked()
        if all_files and all_tables:
            text = "all files and all tables"
        elif all_files:
            text = f"table '{table_name}', all files"
        elif all_tables:
            text = f"all tables, file '{file_name}'"
        else:
            text = f"table '{table_name}', file '{file_name}'"
        return text

    def confirm_remove_variables(self, view_variables: List[VV],) -> bool:
        """ Confirm removing of selected variables. """
        title = f"Delete following variables from {self.get_files_and_tables_text()}: "
        inf_text = "\n".join([stringify_view_variable(var) for var in view_variables])
        dialog = ConfirmationDialog(self, title, det_text=inf_text)
        return dialog.exec_() == 1

    def confirm_rename_simple_variable(self, key: str, blocker: Set[str]) -> Optional[str]:
        """ Confirm rename of given simple variable. """
        title = f"Rename variable for {self.get_files_and_tables_text()}:"
        dialog = SingleInputDialog(
            self, title=title, input1_name="Key", input1_text=key, input1_blocker=blocker,
        )
        if dialog.exec_() == 1:
            return dialog.input1_text

    def confirm_rename_variable(
        self, key: str, type_: str, key_blocker: Set[str], type_blocker: Set[str]
    ) -> Optional[Tuple[str, str]]:
        """ Confirm rename of given variable. """
        title = f"Rename variable for {self.get_files_and_tables_text()}:"
        dialog = DoubleInputDialog(
            self,
            title=title,
            input1_name="Key",
            input1_text=key,
            input1_blocker=key_blocker,
            input2_name="Type",
            input2_text=type_,
            input2_blocker=type_blocker,
        )
        if dialog.exec_() == 1:
            return dialog.input1_text, dialog.input2_text

    def confirm_aggregate_simple_variables(
        self, view_variables: List[VV], func_name: str
    ) -> Optional[str]:
        """ Confirm aggregation of given simple variables. """
        if is_variable_attr_identical(view_variables, KEY_LEVEL):
            key = f"{view_variables[0].key} - {func_name}"
        else:
            key = f"Custom Key - {func_name}"

        title = (
            f"Calculate {func_name} from selected "
            f"variables for {self.get_files_and_tables_text()}:"
        )
        dialog = SingleInputDialog(self, title=title, input1_name="Key", input1_text=key,)
        if dialog.exec_() == 1:
            return dialog.input1_text

    def confirm_aggregate_variables(
        self, view_variables: List[VV], func_name: str
    ) -> Optional[Tuple[str, str]]:
        """ Confirm aggregation of given variables. """
        if is_variable_attr_identical(view_variables, KEY_LEVEL):
            key = f"{view_variables[0].key} - {func_name}"
        else:
            key = f"Custom Key - {func_name}"

        if is_variable_attr_identical(view_variables, TYPE_LEVEL):
            type_ = view_variables[0].type
        else:
            type_ = "Custom Type"

        title = (
            f"Calculate {func_name} from selected "
            f"variables for {self.get_files_and_tables_text()}:"
        )
        dialog = DoubleInputDialog(
            self,
            title=title,
            input1_name="Key",
            input1_text=key,
            input2_name="Type",
            input2_text=type_,
        )
        if dialog.exec_() == 1:
            return dialog.input1_text, dialog.input2_text

    def confirm_delete_file(self, name: str):
        """ Confirm delete file. """
        dialog = ConfirmationDialog(self, f"Delete file {name}?")
        return dialog.exec_() == 1
