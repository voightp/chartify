import contextlib
import ctypes
import shutil
from functools import partial
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Union, Set

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
from esofile_reader.pqt.parquet_storage import ParquetStorage

from chartify.settings import Settings, OutputType
from chartify.ui.buttons import MenuButton
from chartify.ui.dialogs import ConfirmationDialog, SingleInputDialog, DoubleInputDialog
from chartify.ui.drop_frame import DropFrame
from chartify.ui.progress_widget import ProgressContainer
from chartify.ui.tab_widget import TabWidget
from chartify.ui.toolbar import Toolbar
from chartify.ui.treeview import TreeView, ViewMask, ViewType
from chartify.ui.treeview_model import (
    ViewModel,
    is_variable_attr_identical,
    stringify_view_variable,
)
from chartify.utils.css_theme import Palette, CssParser
from chartify.utils.icon_painter import Pixmap, draw_filled_circle_icon
from chartify.utils.utils import VariableData, FilterTuple


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
    variableRenameRequested = Signal(list, VariableData, VariableData)
    variableRemoveRequested = Signal(list, list)
    aggregationRequested = Signal(list, str, list, str, str)
    fileProcessingRequested = Signal(list)
    syncFileProcessingRequested = Signal(list)
    fileRenameRequested = Signal(int, int)
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
        self.tab_stacked_widget = QStackedWidget(self)
        self.tab_stacked_widget.setMinimumWidth(400)
        self.view_layout.addWidget(self.tab_stacked_widget)

        self.drop_button = QToolButton()
        self.drop_button.setObjectName("dropButton")
        self.drop_button.setText("Choose a file or drag it here!")
        self.drop_button.clicked.connect(self.load_files_from_fs)

        self.totals_button = QToolButton()
        self.totals_button.setObjectName("totalsButton")
        self.totals_button.setText("Choose a file or drag it here!")
        self.totals_button.clicked.connect(self.create_totals_file())

        self.diff_button = QToolButton()
        self.diff_button.setObjectName("diffButton")
        self.diff_button.setText("Click here to create difference file!")
        self.diff_button.clicked.connect(self.create_diff_file)

        self.standard_tab_wgt = TabWidget(self.view_wgt, self.drop_button)
        self.totals_tab_wgt = TabWidget(self.view_wgt, self.totals_button)
        self.diff_tab_wgt = TabWidget(self.view_wgt, self.diff_button)

        self.tab_stacked_widget.addWidget(self.standard_tab_wgt)
        self.tab_stacked_widget.addWidget(self.totals_tab_wgt)
        self.tab_stacked_widget.addWidget(self.diff_tab_wgt)

        self.tab_stacked_widget.setCurrentIndex(Settings.OUTPUTS_ENUM)

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
        return self.tab_stacked_widget.currentWidget()

    @property
    def current_view(self) -> TreeView:
        """ Currently selected outputs file. """
        return self.current_tab_widget.currentWidget()

    @property
    def current_model(self) -> ViewModel:
        return self.current_view.source_model

    @property
    def tab_widgets(self) -> List[TabWidget]:
        return [self.standard_tab_wgt, self.totals_tab_wgt, self.diff_tab_wgt]

    def closeEvent(self, event):
        """ Shutdown all the background stuff. """
        # it's needed to terminate threads in controller
        # and close app programmatically
        self.appCloseRequested.emit()
        if self._CLOSE_FLAG:
            Settings.SIZE = (self.width(), self.height())
            Settings.POSITION = (self.x(), self.y())
            Settings.SPLIT = self.central_splitter.sizes()
            Settings.ALL_FILES = self.toolbar.all_files_toggle.isChecked()
            Settings.ALL_TABLES = self.toolbar.all_tables_toggle.isChecked()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:
            if not self.current_tab_widget.is_empty():
                self.current_view.deselect_all_variables()
        elif event.key() == Qt.Key_Delete:
            if self.hasFocus() and self.current_view and self.current_model:
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

        self.totals_button.setIcon(Pixmap(Path(r, "drop_file.png"), *c1))
        self.totals_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.totals_button.setIconSize(Settings.ICON_LARGE_SIZE)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "sigma.png"), *c1), QIcon.Normal, QIcon.Off)
        icon.addPixmap(Pixmap(Path(r, "sigma.png"), *c1, a=0.5), QIcon.Disabled, QIcon.Off)
        self.sum_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "mean.png"), *c1), QIcon.Normal, QIcon.Off)
        icon.addPixmap(Pixmap(Path(r, "mean.png"), *c1, a=0.5), QIcon.Disabled, QIcon.Off)
        self.mean_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "remove.png"), *c1), QIcon.Normal, QIcon.Off)
        icon.addPixmap(Pixmap(Path(r, "remove.png"), *c1, a=0.5), QIcon.Disabled, QIcon.Off)
        self.remove_variables_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "plain_view.png"), *c2), QIcon.Normal, QIcon.Off)
        icon.addPixmap(Pixmap(Path(r, "plain_view.png"), *c2, a=0.5), QIcon.Disabled, QIcon.Off)
        icon.addPixmap(Pixmap(Path(r, "tree_view.png"), *c2), QIcon.Normal, QIcon.On)
        icon.addPixmap(Pixmap(Path(r, "tree_view.png"), *c2, a=0.5), QIcon.Disabled, QIcon.On)
        self.tree_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "unfold_less.png"), *c2), QIcon.Normal, QIcon.Off)
        icon.addPixmap(
            Pixmap(Path(r, "unfold_less.png"), *c2, a=0.5), QIcon.Disabled, QIcon.Off
        )
        self.collapse_all_act.setIcon(icon)

        icon = QIcon()
        icon.addPixmap(Pixmap(Path(r, "unfold_more.png"), *c2), QIcon.Normal, QIcon.Off)
        icon.addPixmap(
            Pixmap(Path(r, "unfold_more.png"), *c2, a=0.5), QIcon.Disabled, QIcon.Off
        )
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

    def get_all_treeviews(self) -> List[TreeView]:
        """ Gather all tree views based on toolbar settings. """
        if self.toolbar.all_files_toggle.isChecked():
            treeviews = self.current_tab_widget.get_all_children()
        else:
            treeviews = [self.current_view]
        return treeviews

    def filter_models(self, view_models: List[ViewModel]) -> List[ViewModel]:
        """ Return models of the same type (SIMPLE, TREE) as the current one. """
        return [m for m in view_models if m.is_simple is self.current_model.is_simple]

    def get_all_models(self) -> List[ViewModel]:
        """ Gather models based on toolbar settings. """
        models = []
        if self.toolbar.all_tables_toggle.isChecked():
            for treeview in self.get_all_treeviews():
                models.extend(self.filter_models(treeview.all_view_models))
        else:
            table_name = self.current_view.current_table_name
            with contextlib.suppress(KeyError):
                for treeview in self.get_all_treeviews():
                    models.extend(self.filter_models([treeview.models[table_name]]))
        return models

    def get_all_other_models(self) -> List[ViewModel]:
        """ Gather models based on toolbar settings. """
        models = self.get_all_models()
        models.remove(self.current_model)
        return models

    def update_model(self, treeview: TreeView) -> None:
        """ Force update current model. """
        with ViewMask(
            treeview,
            old_model=treeview.source_model,
            filter_tuple=self.get_filter_tuple(),
            show_source_units=self.show_source_units(),
        ) as mask:
            mask.update_table(self.tree_act.isChecked(), **self.toolbar.current_units)
        self.update_table_actions()

    def on_tree_node_changed(self, treeview: TreeView) -> None:
        self.update_model(treeview)

    def on_item_double_clicked(
        self,
        treeview: TreeView,
        row: int,
        parent_index: Optional[QModelIndex],
        old_variable_data: VariableData,
    ) -> None:
        old_key = old_variable_data.key
        key_blocker = set(treeview.get_current_column_data(KEY_LEVEL))
        key_blocker.remove(old_key)
        if treeview.source_model.is_simple:
            res = self.confirm_rename_simple_variable(old_key, key_blocker)
        else:
            old_type = old_variable_data.type
            type_blocker = set(treeview.get_current_column_data(TYPE_LEVEL))
            type_blocker.remove(old_type)
            res = self.confirm_rename_variable(old_key, old_type, key_blocker, type_blocker)

        if res is not None:
            key = res if treeview.view_type is ViewType.SIMPLE else res[0]
            type_ = None if treeview.view_type is ViewType.SIMPLE else res[1]
            units = old_variable_data.units
            new_variable_data = VariableData(key=key, type=type_, units=units)
            treeview.update_variable(row, parent_index, new_variable_data)
            if models := self.get_all_other_models():
                self.variableRenameRequested.emit(models, old_variable_data, new_variable_data)

    def on_remove_variables_triggered(self):
        if selected := self.current_view.get_selected_variable_data():
            if self.confirm_remove_variables(selected):
                self.current_model.delete_variables(selected)
                self.on_selection_cleared()
                if models := self.get_all_other_models():
                    self.variableRemoveRequested.emit(models, selected)

    def on_aggregation_requested(self, func: str) -> None:
        if view_variables := self.current_view.get_selected_variable_data():
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
        if view_variables := self.current_view.get_selected_variable_data():
            models = self.get_all_models()
            frames = []
            for model in models:
                df = model.get_results(view_variables, **self.toolbar.current_units)
                if df is not None:
                    frames.append(df)
            return pd.concat(frames, axis=1, sort=False)

    def on_sum_action_triggered(self):
        self.on_aggregation_requested("sum")

    def on_mean_action_triggered(self):
        self.on_aggregation_requested("mean")

    def add_treeview(
        self, id_: int, name: str, output_type: OutputType, models: Dict[str, ViewModel]
    ):
        """ Add processed data into tab widget corresponding to file type. """
        output_types = {
            OutputType.STANDARD: self.standard_tab_wgt,
            OutputType.TOTALS: self.totals_tab_wgt,
            OutputType.DIFFERENCE: self.diff_tab_wgt,
        }
        tab_widget = output_types[output_type]

        view = TreeView(id_, models, output_type)
        view.selectionCleared.connect(self.on_selection_cleared)
        view.selectionPopulated.connect(self.on_selection_populated)
        view.treeNodeChanged.connect(self.on_tree_node_changed)
        view.itemDoubleClicked.connect(self.on_item_double_clicked)
        tab_widget.addTab(view, name)

    def expand_all(self):
        """ Expand all tree view items. """
        if not self.current_tab_widget.is_empty():
            self.current_view.expandAll()

    def collapse_all(self):
        """ Collapse all tree view items. """
        if not self.current_tab_widget.is_empty():
            self.current_view.collapseAll()

    def save_storage_to_fs(self) -> Optional[Path]:
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
        """ Load results from given paths.  """
        Settings.LOAD_PATH = Path(paths[0]).parent
        self.syncFileProcessingRequested.emit(paths)

    def load_files_from_paths(self, paths: List[Path]):
        """ Load results from given paths.  """
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
        self.sum_act.triggered.connect(self.on_sum_action_triggered)
        self.mean_act.triggered.connect(self.on_mean_action_triggered)

    def show_source_units(self) -> bool:
        """ Check if source units should be visible. """
        return self.toolbar.source_units_toggle.isChecked()

    def get_filter_tuple(self):
        """ Retrieve filter inputs from ui. """
        return FilterTuple(
            key=self.key_line_edit.text(),
            type=self.type_line_edit.text(),
            proxy_units=self.units_line_edit.text(),
        )

    def on_stacked_widget_change_requested(self, index: int) -> None:
        """ Show tab widget corresponding to the given radio button. """
        Settings.OUTPUTS_ENUM = index
        self.tab_stacked_widget.setCurrentIndex(index)
        if self.current_view is not None and self.current_model is None:
            self.handle_tab_change(self.current_view)
        self.update_toolbar_actions()

    def handle_tab_change(
        self, treeview: TreeView, previous_treeview: Optional[TreeView] = None
    ) -> None:
        if (
            previous_treeview is not None
            and previous_treeview.current_table_name in treeview.table_names
        ):
            table_name = previous_treeview.current_table_name
        else:
            if treeview.current_table_name:
                table_name = treeview.current_table_name
            else:
                table_name = treeview.table_names[0]
        with ViewMask(
            treeview,
            ref_treeview=previous_treeview,
            filter_tuple=self.get_filter_tuple(),
            show_source_units=self.show_source_units(),
        ) as mask:
            mask.set_table(table_name, self.tree_act.isChecked(), **self.toolbar.current_units)

    def update_view_actions(self):
        if self.current_view is None:
            self.toolbar.rate_energy_btn.setEnabled(True)
            self.toolbar.update_table_buttons(table_names=[], selected="")
        else:
            self.toolbar.update_table_buttons(
                table_names=self.current_view.table_names, selected=self.current_model.name
            )

    def update_file_actions(self):
        if self.current_tab_widget.count() > 0:
            self.close_all_act.setEnabled(True)
        else:
            self.close_all_act.setEnabled(False)

    def update_table_actions(self):
        """ Update toolbar actions to match current table. """
        if self.current_view is None:
            self.tree_act.setEnabled(True)
            self.expand_all_act.setEnabled(True)
            self.collapse_all_act.setEnabled(True)
            self.toolbar.enable_rate_to_energy(True)
        else:
            allow_tree = not self.current_model.is_simple
            self.tree_act.setEnabled(allow_tree)
            self.expand_all_act.setEnabled(allow_tree)
            self.collapse_all_act.setEnabled(allow_tree)
            self.toolbar.enable_rate_to_energy(self.current_model.allow_rate_to_energy)
        Settings.RATE_TO_ENERGY = (
            self.toolbar.rate_energy_btn.isChecked()
            and self.toolbar.rate_energy_btn.isEnabled()
        )

    def update_selection_actions(self):
        """  Update toolbar actions to match current selection. """
        if self.current_view is not None and (
            variables := self.current_view.get_selected_variable_data()
        ):
            self.remove_variables_act.setEnabled(True)
            if len(variables) > 1:
                units = [var.units for var in variables]
                if len(set(units)) == 1 or (
                    all_rate_or_energy(units) and self.current_model.allow_rate_to_energy
                ):
                    self.sum_act.setEnabled(True)
                    self.mean_act.setEnabled(True)
            else:
                self.sum_act.setEnabled(False)
                self.mean_act.setEnabled(False)
        else:
            self.remove_variables_act.setEnabled(False)
            self.sum_act.setEnabled(False)
            self.mean_act.setEnabled(False)

    def update_toolbar_actions(self):
        self.update_file_actions()
        self.update_table_actions()
        self.update_view_actions()
        self.update_selection_actions()

    def on_tab_changed(self, tab_widget: TabWidget, previous_index: int, index: int) -> None:
        if tab_widget is self.current_tab_widget:
            if index == -1:
                Settings.CURRENT_FILE_ID = None
            else:
                current_treeview = tab_widget.widget(index)
                previous_treeview = tab_widget.widget(previous_index)
                Settings.CURRENT_FILE_ID = current_treeview.id_
                self.handle_tab_change(current_treeview, previous_treeview)
            self.update_toolbar_actions()

    def on_table_change_requested(self, table_name: str):
        """ Change table on a current model. """
        Settings.TABLE_NAME = table_name
        with ViewMask(
            self.current_view,
            old_model=self.current_view.source_model,
            filter_tuple=self.get_filter_tuple(),
            show_source_units=self.show_source_units(),
        ) as mask:
            tree = self.tree_act.isChecked()
            mask.set_table(table_name, tree, **self.toolbar.current_units)
        self.update_table_actions()
        self.update_selection_actions()

    def on_selection_populated(self, variables: List[VariableData]):
        """ Store current selection in main app. """
        self.update_selection_actions()
        self.selectionChanged.emit(variables)

    def on_selection_cleared(self):
        """ Handle behaviour when no variables are selected. """
        self.update_selection_actions()
        self.selectionChanged.emit([])

    def get_all_tab_names(self):
        names = []
        for tab_widget in self.tab_widgets:
            for i in range(tab_widget.count()):
                names.append(tab_widget.tabText(i))
        return names

    def on_tab_bar_double_clicked(self, tab_widget: TabWidget, tab_index: int):
        name = tab_widget.tabText(tab_index)
        names = set(self.get_all_tab_names())
        names.remove(name)
        new_name = self.confirm_rename_file(name, names)
        if new_name is not None:
            tab_widget.setTabText(tab_index, new_name)
            self.fileRenameRequested.emit(id_, new_name)

    def on_tab_close_requested(self, tab_widget: TabWidget, tab_index: int):
        treeview = tab_widget.widget(tab_index)
        name = tab_widget.tabText(tab_index)
        res = self.confirm_delete_file(name)
        if res:
            if treeview is self.current_view:
                self.current_tab_widget.set_next_tab()
            tab_widget.removeTab(tab_index)
            treeview.deleteLater()
            self.fileRemoveRequested.emit(treeview.id_)

    def connect_tab_widget_signals(self):
        # ~~~~ Tab Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for tab_widget in self.tab_widgets:
            tab_widget.closeTabRequested.connect(self.on_tab_close_requested)
            tab_widget.currentTabChanged.connect(self.on_tab_changed)
            tab_widget.tabRenameRequested.connect(self.on_tab_bar_double_clicked)

    def on_source_units_toggled(self, checked: bool):
        Settings.SHOW_SOURCE_UNITS = checked
        if self.current_view:
            self.current_view.hide_section(UNITS_LEVEL, not checked)

    def on_units_changed(
        self, energy_units: str, rate_units: str, units_system: str, rate_to_energy: bool
    ) -> None:
        Settings.ENERGY_UNITS = energy_units
        Settings.RATE_UNITS = rate_units
        Settings.UNITS_SYSTEM = units_system
        Settings.RATE_TO_ENERGY = rate_to_energy
        if self.current_view:
            self.current_view.update_units(**self.toolbar.current_units)

    def on_custom_units_toggled(self) -> None:
        # model could have been changed prior to custom units toggle
        # so rate to energy conversion may not be applicable
        if self.current_tab_widget.is_empty() or self.current_view.allow_rate_to_energy:
            self.toolbar.enable_rate_to_energy(True)
        else:
            self.toolbar.rate_energy_btn.setEnabled(False)

    def connect_toolbar_signals(self):
        # ~~~~ Toolbar Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar.tableChangeRequested.connect(self.on_table_change_requested)
        self.toolbar.tabWidgetChangeRequested.connect(self.on_stacked_widget_change_requested)
        self.toolbar.customUnitsToggled.connect(self.on_custom_units_toggled)
        self.toolbar.unitsChanged.connect(self.on_units_changed)
        self.toolbar.source_units_toggle.stateChanged.connect(self.on_source_units_toggled)

    def on_tree_act_checked(self, checked: bool):
        """ Update view when view type is changed. """
        self.collapse_all_act.setEnabled(checked)
        self.expand_all_act.setEnabled(checked)
        if self.current_view is not None:
            with ViewMask(
                self.current_view,
                old_model=self.current_view.source_model,
                filter_tuple=self.get_filter_tuple(),
                show_source_units=self.show_source_units(),
            ) as mask:
                mask.update_table(self.tree_act.isChecked(), **self.toolbar.current_units)

    def on_text_edited(self):
        """ Delay firing a text edited event. """
        self.timer.start(200)

    def on_filter_timeout(self):
        """ Apply a filter when the filter text is edited. """
        filter_tuple = self.get_filter_tuple()
        if self.current_view is not None:
            self.current_view.filter_view(filter_tuple)

    def connect_view_tools_signals(self):
        # ~~~~ Filter actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.type_line_edit.textEdited.connect(self.on_text_edited)
        self.key_line_edit.textEdited.connect(self.on_text_edited)
        self.units_line_edit.textEdited.connect(self.on_text_edited)
        self.timer.timeout.connect(self.on_filter_timeout)

    def confirm_rename_file(self, name: str, other_names: Set[str]) -> Optional[str]:
        """ Rename file on a tab identified by the given index. """
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
        """ Get information on function application based on current settings. """
        table_name = self.current_view.current_table_name
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

    def confirm_remove_variables(self, view_variables: List[VariableData],) -> bool:
        """ Remove selected variables. """
        title = f"Delete following variables from {self.get_files_and_tables_text()}: "
        inf_text = "\n".join([stringify_view_variable(var) for var in view_variables])
        dialog = ConfirmationDialog(self, title, det_text=inf_text)
        return dialog.exec_() == 1

    def confirm_rename_simple_variable(self, key: str, blocker: Set[str]) -> Optional[str]:
        title = f"Rename variable for {self.get_files_and_tables_text()}:"
        dialog = SingleInputDialog(
            self, title=title, input1_name="Key", input1_text=key, input1_blocker=blocker,
        )
        if dialog.exec_() == 1:
            return dialog.input1_text

    def confirm_rename_variable(
        self, key: str, type_: str, key_blocker: Set[str], type_blocker: Set[str]
    ) -> Optional[Tuple[str, str]]:
        """ Rename given variable. """
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
        self, view_variables: List[VariableData], func_name: str
    ) -> Optional[str]:
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
        self, view_variables: List[VariableData], func_name: str
    ) -> Optional[Tuple[str, str]]:
        """ Aggregate variables using given function. """
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
        """ Confirm delete file. . """
        dialog = ConfirmationDialog(self, f"Delete file {name}?")
        return dialog.exec_() == 1
