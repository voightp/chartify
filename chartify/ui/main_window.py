import contextlib
import ctypes
from functools import partial
from pathlib import Path
from typing import Union, Optional, Tuple, List

from PySide2.QtCore import QSize, Qt, QCoreApplication, Signal
from PySide2.QtGui import QIcon, QKeySequence, QColor
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtWidgets import (
    QWidget,
    QSplitter,
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QAction,
    QFileDialog,
    QSizePolicy,
    QFrame,
    QMainWindow,
    QStatusBar,
    QMenu,
)
from esofile_reader.convertor import is_rate_or_energy
from esofile_reader.storages.pqt_storage import ParquetStorage

from chartify.settings import Settings
from chartify.ui.buttons import MenuButton
from chartify.ui.dialogs import ConfirmationDialog, SingleInputDialog, DoubleInputDialog
from chartify.ui.misc_widgets import DropFrame, TabWidget
from chartify.ui.progress_widget import ProgressContainer
from chartify.ui.simpleview import SimpleView
from chartify.ui.toolbar import Toolbar
from chartify.ui.treeview import TreeView
from chartify.ui.treeview_tools import ViewTools
from chartify.utils.css_theme import Palette, CssTheme
from chartify.utils.icon_painter import Pixmap, filled_circle_pixmap
from chartify.utils.utils import VariableData


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QMainWindow):
    """ Main application instance. """

    QCoreApplication.setOrganizationName("chartify")
    QCoreApplication.setOrganizationDomain("chartify.foo")
    QCoreApplication.setApplicationName("chartify")

    paletteUpdated = Signal()
    viewUpdateRequested = Signal(int)
    tabChanged = Signal(int)
    selectionChanged = Signal(list)
    fileProcessingRequested = Signal(list)
    fileRenameRequested = Signal(int)
    variableRenameRequested = Signal(int, VariableData)
    variableRemoveRequested = Signal(int, list)
    variableAggregateRequested = Signal(int, list, str, str, str)
    fileRemoveRequested = Signal(int)
    appCloseRequested = Signal()

    _CLOSE_FLAG = False

    def __init__(self):
        super(MainWindow, self).__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setWindowTitle("chartify")
        self.setFocusPolicy(Qt.StrongFocus)
        self.resize(Settings.SIZE)
        self.move(Settings.POSITION)

        # ~~~~ Main Window widgets ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.central_wgt = QWidget(self)
        self.central_layout = QHBoxLayout(self.central_wgt)
        self.setCentralWidget(self.central_wgt)
        self.central_splitter = QSplitter(self.central_wgt)
        self.central_splitter.setOrientation(Qt.Horizontal)
        self.central_layout.addWidget(self.central_splitter)

        # ~~~~ Left hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt = DropFrame(self.central_splitter)
        self.left_main_wgt.setObjectName("leftMainWgt")
        self.left_main_layout = QHBoxLayout(self.left_main_wgt)
        self.central_splitter.addWidget(self.left_main_wgt)

        # ~~~~ Left hand Tools Widget ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar = Toolbar(self.left_main_wgt)
        self.left_main_layout.addWidget(self.toolbar)

        # ~~~~ Left hand View widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_wgt = QFrame(self.left_main_wgt)
        self.view_wgt.setObjectName("viewWidget")
        self.view_layout = QVBoxLayout(self.view_wgt)
        if Settings.MIRRORED:
            self.left_main_layout.insertWidget(0, self.view_wgt)
        else:
            self.left_main_layout.addWidget(self.view_wgt)

        # ~~~~ Left hand Tab widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt = TabWidget(self.view_wgt)
        self.view_layout.addWidget(self.tab_wgt)

        # ~~~~ Left hand Tab Tools  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt = ViewTools(self.view_wgt)
        self.view_layout.addWidget(self.view_tools_wgt)

        # ~~~~ Right hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.right_main_wgt = QWidget(self.central_splitter)
        self.right_main_layout = QHBoxLayout(self.right_main_wgt)
        if Settings.MIRRORED:
            self.central_splitter.insertWidget(0, self.right_main_wgt)
        else:
            self.central_splitter.addWidget(self.right_main_wgt)

        # ~~~~ Right hand Chart Area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.main_chart_widget = QFrame(self.right_main_wgt)
        self.main_chart_layout = QHBoxLayout(self.main_chart_widget)
        self.right_main_layout.addWidget(self.main_chart_widget)

        self.web_view = QWebEngineView(self)
        self.main_chart_layout.addWidget(self.web_view)

        # ~~~~ Status bar ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.status_bar = QStatusBar(self)
        self.status_bar.setFixedHeight(20)
        self.setStatusBar(self.status_bar)

        self.progress_cont = ProgressContainer(self.status_bar)
        self.status_bar.addWidget(self.progress_cont)

        # ~~~~ Palettes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.palettes = Palette.parse_palettes(Settings.PALETTE_PATH)
        Settings.PALETTE = self.palettes[Settings.PALETTE_NAME]

        # ~~~~ Scheme button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        actions = []
        def_act = None
        for name, colors in self.palettes.items():
            act = QAction(name, self)
            act.triggered.connect(partial(self.on_scheme_changed, name))
            c1 = QColor(*colors.get_color("SECONDARY_COLOR", as_tuple=True))
            c2 = QColor(*colors.get_color("BACKGROUND_COLOR", as_tuple=True))
            act.setIcon(
                filled_circle_pixmap(
                    QSize(60, 60), c1, c2=c2, border_color=QColor(255, 255, 255)
                )
            )
            actions.append(act)
            if name == Settings.PALETTE_NAME:
                def_act = act

        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions(actions)

        self.scheme_btn = QToolButton(self)
        self.scheme_btn.setPopupMode(QToolButton.InstantPopup)
        self.scheme_btn.setDefaultAction(def_act)
        self.scheme_btn.setMenu(menu)
        self.scheme_btn.setObjectName("schemeButton")
        menu.triggered.connect(lambda act: self.scheme_btn.setIcon(act.icon()))

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

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act = QAction("Load file | files", self)
        self.load_file_act.setShortcut(QKeySequence("Ctrl+L"))

        self.close_all_act = QAction("Close all", self)

        self.remove_variables_act = QAction("Delete", self)

        self.sum_variables_act = QAction("Sum", self)
        self.sum_variables_act.setShortcut(QKeySequence("Ctrl+T"))

        self.avg_variables_act = QAction("Mean", self)
        self.avg_variables_act.setShortcut(QKeySequence("Ctrl+M"))

        self.collapse_all_act = QAction("Collapse All", self)
        self.collapse_all_act.setShortcut(QKeySequence("Ctrl+Shift+E"))

        self.expand_all_act = QAction("Expand All", self)
        self.expand_all_act.setShortcut(QKeySequence("Ctrl+E"))

        self.tree_act = QAction("Tree", self)
        self.tree_act.setShortcut(QKeySequence("Ctrl+T"))

        self.save_act = QAction("Save", self)
        self.save_act.setShortcut(QKeySequence("Ctrl+S"))

        self.save_as_act = QAction("Save as", self)
        self.save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))

        # add actions to main window to allow shortcuts
        self.addActions(
            [
                self.remove_variables_act,
                self.sum_variables_act,
                self.avg_variables_act,
                self.collapse_all_act,
                self.expand_all_act,
                self.tree_act,
            ]
        )

        # disable actions as these will be activated on selection
        self.close_all_act.setEnabled(False)
        self.remove_variables_act.setEnabled(False)

        self.load_file_btn = MenuButton("Load file | files", self)
        self.load_file_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions([self.load_file_act, self.close_all_act])
        self.load_file_btn.setMenu(menu)

        self.save_btn = MenuButton("Tools", self)
        self.save_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.addActions([self.save_act, self.save_as_act])
        self.save_btn.setMenu(menu)

        self.about_btn = MenuButton("About", self)
        self.about_btn.setIconSize(Settings.ICON_SMALL_SIZE)

        self.load_file_btn.setObjectName("fileButton")
        self.save_btn.setObjectName("saveButton")
        self.about_btn.setObjectName("aboutButton")

        self.mini_menu_layout.addWidget(self.load_file_btn)
        self.mini_menu_layout.addWidget(self.save_btn)
        self.mini_menu_layout.addWidget(self.about_btn)

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.set_up_base_ui()

        # ~~~~ Set up app appearance ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.css = ""
        self.load_icons()
        self.load_css()

        # ~~~~ Tree view appearance ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_settings = {
            "simpleview": {"widths": {"fixed": 70}, "header": ("key", "units"),},
            "treeview": {
                "widths": {"interactive": 200, "fixed": 70},
                "header": ("type", "key", "units"),
                "expanded": set(),
            },
        }

        # ~~~~ Connect main ui user actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.connect_ui_signals()

    @property
    def current_view(self) -> Union[SimpleView, TreeView]:
        """ Currently selected outputs file. """
        return self.tab_wgt.currentWidget()

    @property
    def all_views(self):
        """ All tabs content. """
        return [self.tab_wgt.widget(i) for i in range(self.tab_wgt.count())]

    def closeEvent(self, event):
        """ Shutdown all the background stuff. """
        # it's needed to terminate threads in controller
        # and close app programmatically
        self.appCloseRequested.emit()
        if self._CLOSE_FLAG:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:
            if not self.tab_wgt.is_empty():
                self.current_view.deselect_all_variables()
        elif event.key() == Qt.Key_Delete:
            if self.hasFocus():
                self.remove_variables()

    def load_icons(self):
        """ Load application icons. """
        # this sets toolbar icon on win 7
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("foo")

        c1 = Settings.PALETTE.get_color("PRIMARY_TEXT_COLOR", as_tuple=True)
        c2 = Settings.PALETTE.get_color("SECONDARY_TEXT_COLOR", as_tuple=True)

        r = Settings.ICONS_PATH
        self.setWindowIcon(Pixmap(Path(r, "smile.png"), 255, 255, 255))

        self.load_file_btn.setIcon(QIcon(Pixmap(Path(r, "file.png"), *c1)))
        self.save_btn.setIcon(QIcon(Pixmap(Path(r, "save.png"), *c1)))
        self.about_btn.setIcon(QIcon(Pixmap(Path(r, "help.png"), *c1)))
        self.close_all_act.setIcon(QIcon(Pixmap(Path(r, "remove.png"), *c1)))
        self.load_file_act.setIcon(QIcon(Pixmap(Path(r, "add_file.png"), *c1)))

        self.tab_wgt.drop_btn.setIcon(Pixmap(Path(r, "drop_file.png"), *c1))
        self.tab_wgt.drop_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.tab_wgt.drop_btn.setIconSize(QSize(50, 50))

        self.toolbar.totals_btn.set_icons(
            Pixmap(Path(r, "building.png"), *c1),
            Pixmap(Path(r, "building.png"), *c1, a=0.5),
            Pixmap(Path(r, "building.png"), *c2),
            Pixmap(Path(r, "building.png"), *c2, a=0.5),
        )

        self.toolbar.all_files_btn.set_icons(
            Pixmap(Path(r, "all_files.png"), *c1),
            Pixmap(Path(r, "all_files.png"), *c1, a=0.5),
            Pixmap(Path(r, "all_files.png"), *c2),
            Pixmap(Path(r, "all_files.png"), *c2, a=0.5),
        )

        self.toolbar.sum_btn.set_icons(
            Pixmap(Path(r, "sigma.png"), *c1), Pixmap(Path(r, "sigma.png"), *c1, a=0.5)
        )
        self.toolbar.mean_btn.set_icons(
            Pixmap(Path(r, "mean.png"), *c1), Pixmap(Path(r, "mean.png"), *c1, a=0.5)
        )

        self.toolbar.remove_btn.set_icons(
            Pixmap(Path(r, "remove.png"), *c1), Pixmap(Path(r, "remove.png"), *c1, a=0.5)
        )

    def set_up_base_ui(self):
        """ Set up appearance of main widgets. """
        self.central_layout.setSpacing(0)
        self.central_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Main left side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        left_side_policy = QSizePolicy()
        left_side_policy.setHorizontalPolicy(QSizePolicy.Minimum)
        left_side_policy.setHorizontalStretch(0)
        self.left_main_wgt.setSizePolicy(left_side_policy)
        self.left_main_layout.setSpacing(2)
        self.left_main_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_wgt.setMinimumWidth(400)

        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.setSpacing(0)

        # ~~~~ Main right side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        right_side_policy = QSizePolicy()
        right_side_policy.setHorizontalPolicy(QSizePolicy.Expanding)
        right_side_policy.setHorizontalStretch(1)
        self.right_main_wgt.setSizePolicy(right_side_policy)
        self.right_main_layout.setSpacing(0)
        self.right_main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.main_chart_widget.setMinimumWidth(600)

        # split values are stored as strings in registry
        self.central_splitter.setSizes([int(s) for s in Settings.SPLIT])

    def load_css(self) -> None:
        """ Update application appearance. """
        self.css = CssTheme(Settings.CSS_PATH)
        self.css.populate_content(Settings.PALETTE)

        # css needs to be cleared to repaint the window properly
        self.setStyleSheet("")
        self.setStyleSheet(self.css.content)

    def mirror_layout(self):
        """ Mirror the layout. """
        self.left_main_layout.addItem(self.left_main_layout.takeAt(0))
        self.central_splitter.insertWidget(0, self.central_splitter.widget(1))
        Settings.MIRRORED = not Settings.MIRRORED
        Settings.SPLIT = self.central_splitter.sizes()

    def on_scheme_changed(self, name):
        """ Update the application palette. """
        if name != Settings.PALETTE_NAME:
            Settings.PALETTE = self.palettes[name]
            Settings.PALETTE_NAME = name
            self.load_css()
            self.load_icons()
            self.paletteUpdated.emit()

    def add_new_tab(self, id_, name, simpleview=False):
        """ Add file on the UI. """
        # create an empty 'View' widget - the data will be
        # automatically populated on 'onTabChanged' signal
        if simpleview:
            view = SimpleView(id_)
        else:
            view = TreeView(id_)
            view.treeNodeChanged.connect(self.on_settings_changed)

        # connect shared signals
        view.selectionCleared.connect(self.on_selection_cleared)
        view.selectionPopulated.connect(self.on_selection_populated)
        view.viewSettingsChanged.connect(self.on_view_settings_changed)
        view.itemDoubleClicked.connect(self.variableRenameRequested.emit)

        # add the new view into tab widget
        self.tab_wgt.add_tab(view, name)

        # enable all eso file results btn if there's multiple files
        if self.tab_wgt.count() > 1:
            self.toolbar.all_files_btn.setEnabled(True)
            self.close_all_act.setEnabled(True)

        # enable all eso file results btn if it's suitable
        if not self.tab_wgt.is_empty():
            self.toolbar.totals_btn.setEnabled(True)

    def build_treeview(self, variables_df, selected=None, scroll_to=None):
        """ Create a new view when any of related settings change """
        conditions = (
            Settings.TREE_VIEW != self.current_view.is_tree,
            Settings.TABLE_NAME != self.current_view.interval,
            Settings.RATE_TO_ENERGY != self.current_view.rate_to_energy,
            Settings.ENERGY_UNITS != self.current_view.energy_units,
            Settings.POWER_UNITS != self.current_view.power_units,
        )
        view_settings = self.view_settings[self.current_view.class_type]
        if self.current_view and (any(conditions) or self.current_view.next_update_forced):
            self.current_view.populate_view(
                variables_df=variables_df,
                interval=Settings.TABLE_NAME,
                is_tree=Settings.TREE_VIEW,
                rate_to_energy=Settings.RATE_TO_ENERGY,
                units_system=Settings.UNITS_SYSTEM,
                energy_units=Settings.ENERGY_UNITS,
                power_units=Settings.POWER_UNITS,
                header=view_settings["header"],
            )
        # update visual appearance of the view to be consistent
        # with previously displayed View
        self.current_view.update_view_appearance(**view_settings)

        filter_tup = self.view_tools_wgt.get_filter_tuple()
        if any(filter_tup) or filter_tup != self.current_view.model().filter_tuple:
            self.current_view.filter_view(filter_tup)

        # clear selections to avoid having visually
        # selected items from previous selection
        self.current_view.deselect_all_variables()
        if selected:
            self.current_view.select_variables(selected)

        if scroll_to:
            self.current_view.scroll_to(scroll_to, view_settings["header"][0])

    def on_selection_populated(self, variables):
        """ Store current selection in main app. """
        self.remove_variables_act.setEnabled(True)
        self.toolbar.remove_btn.setEnabled(True)

        # check if variables can be aggregated
        if len(variables) > 1:
            units = [var.units for var in variables]
            if len(set(units)) == 1 or (
                is_rate_or_energy(units) and self.toolbar.rate_energy_btn.isEnabled()
            ):
                self.toolbar.sum_btn.setEnabled(True)
                self.toolbar.mean_btn.setEnabled(True)
        else:
            self.toolbar.sum_btn.setEnabled(False)
            self.toolbar.mean_btn.setEnabled(False)

        self.selectionChanged.emit(variables)

    def on_selection_cleared(self):
        """ Handle behaviour when no variables are selected. """
        self.remove_variables_act.setEnabled(False)
        self.toolbar.sum_btn.setEnabled(False)
        self.toolbar.mean_btn.setEnabled(False)
        self.toolbar.remove_btn.setEnabled(False)
        self.selectionChanged.emit([])

    def filter_treeview(self, filter_tup):
        """ Filter current view. """
        if not self.tab_wgt.is_empty():
            self.current_view.filter_view(filter_tup)

    def expand_all(self):
        """ Expand all tree view items. """
        if self.current_view:
            self.current_view.expandAll()

    def collapse_all(self):
        """ Collapse all tree view items. """
        if self.current_view:
            self.current_view.collapseAll()

    def on_tab_closed(self, wgt):
        """ Delete current eso file. """
        id_ = wgt.id_
        wgt.deleteLater()

        if self.tab_wgt.is_empty():
            self.toolbar.totals_btn.setEnabled(False)

        if self.tab_wgt.count() <= 1:
            self.toolbar.all_files_btn.setEnabled(False)
            self.close_all_act.setEnabled(False)

        self.fileRemoveRequested.emit(id_)

    def on_current_tab_changed(self, index: int) -> None:
        """ Update view when tabChanged event is fired. """
        if index == -1:
            # there aren't any widgets available
            self.remove_variables_act.setEnabled(False)
            self.toolbar.set_initial_layout()
            Settings.CURRENT_FILE_ID = None
        else:
            self.tabChanged.emit(self.current_view.id_)
            Settings.CURRENT_FILE_ID = self.current_view.id_

    def on_view_settings_changed(self, view_type: str, new_settings: dict):
        """ Update current ui view settings. """
        settings = self.view_settings[view_type]

        def on_expanded():
            settings["expanded"].add(value)

        def on_collapsed():
            with contextlib.suppress(KeyError):
                settings["expanded"].remove(value)

        def on_interactive():
            settings["widths"]["interactive"] = value

        def on_header():
            settings["header"] = value

        switch = {
            "expanded": on_expanded,
            "collapsed": on_collapsed,
            "interactive": on_interactive,
            "header": on_header,
        }
        for key, value in new_settings.items():
            switch[key]()

    def on_settings_changed(self):
        """ Update view when settings change. """
        if self.current_view:
            self.viewUpdateRequested.emit(self.current_view.id_)

    def on_splitter_moved(self, pos, _):
        """ Store current splitter position. """
        Settings.SPLIT = self.central_splitter.sizes()

    def save_storage_to_fs(self) -> Path:
        path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save project",
            filter=f"CFS (*{ParquetStorage.EXT})",
            dir=Settings.SAVE_PATH,
        )
        if path:
            Settings.SAVE_PATH = str(Path(path).parent)
            return Path(path)

    def load_files_from_fs(self):
        """ Select eso files from explorer and start processing. """
        file_paths, _ = QFileDialog.getOpenFileNames(
            parent=self,
            caption="Load Project / Eso File",
            filter="FILES (*.csv *.xlsx *.eso *.cfs)",
            dir=Settings.LOAD_PATH,
        )
        if file_paths:
            # store last path for future
            Settings.LOAD_PATH = str(Path(file_paths[0]).parent)
            self.fileProcessingRequested.emit(file_paths)

    def on_tab_bar_double_clicked(self, tab_index: int):
        view = self.tab_wgt.widget(tab_index)
        self.fileRenameRequested.emit(tab_index, view.id_)

    def confirm_rename_file(self, name: str, other_names: List[str]) -> Optional[str]:
        """ Rename file on a tab identified by the given index. """
        dialog = SingleInputDialog(
            self,
            title="Enter a new file name.",
            input1_name="Name",
            input1_text=name,
            input1_blocker=other_names,
        )
        res = dialog.exec_()
        if res == 1:
            name = dialog.input1_text
            index = self.tab_wgt.currentIndex()
            self.tab_wgt.setTabText(index, name)
            return name

    def remove_variables(self):
        """ Remove selected variables. """
        variables = self.current_view.get_selected_variables()

        if not variables:
            return

        all_ = self.toolbar.all_files_requested()
        nm = self.tab_wgt.tabText(self.tab_wgt.currentIndex())

        files = "all files" if all_ else f"file '{nm}'"
        text = f"Delete following variables from {files}: "

        inf_text = "\n".join([" | ".join(var[1:3]) for var in variables])
        dialog = ConfirmationDialog(self, text, det_text=inf_text)

        if dialog.exec_() == 1:
            for v in self.all_views if all_ else [self.current_view]:
                v.set_next_update_forced()
            self.variableRemoveRequested.emit(self.current_view.id_, variables)

    def confirm_rename_variable(
        self, variable_name: str, key_name: str
    ) -> Optional[Tuple[str, str]]:
        """ Rename given variable. """
        dialog = DoubleInputDialog(
            self,
            title="Rename variable:",
            input1_name="Variable name",
            input1_text=variable_name,
            input2_name="Key name",
            input2_text=key_name,
        )
        if dialog.exec_() == 1:
            return dialog.input1_text, dialog.input2_text

    def aggregate_variables(self, func):
        """ Aggregate variables using given function. """
        variables = self.current_view.get_selected_variables()

        if not variables:
            return

        variable_name = "Custom Variable"
        key_name = "Custom Key"

        # let variable name be the same as all names are identical
        if all(map(lambda x: x.variable == variables[0].variable, variables)):
            variable_name = variables[0].variable
        # let key name be the same as all names are identical
        if all(map(lambda x: x.key == variables[0].key, variables)):
            key_name = variables[0].key

        dialog = DoubleInputDialog(
            self,
            title="Enter details of the new variable:",
            input1_name="Variable name",
            input1_text=variable_name,
            input2_name="Key name",
            input2_text=key_name,
        )
        res = dialog.exec()

        if res == 1:
            variable_name = dialog.input1_text
            key_name = dialog.input2_text

            for v in self.all_views if Settings.ALL_FILES else [self.current_view]:
                v.set_next_update_forced()

            self.variableAggregateRequested.emit(
                self.current_view.id_, variables, variable_name, key_name, func
            )

    def connect_ui_signals(self):
        """ Create actions which depend on user actions """
        # ~~~~ Widget Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt.fileDropped.connect(self.fileProcessingRequested.emit)
        self.central_splitter.splitterMoved.connect(self.on_splitter_moved)

        # ~~~~ Actions Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act.triggered.connect(self.load_files_from_fs)
        self.tree_act.triggered.connect(self.view_tools_wgt.tree_view_btn.toggle)
        self.collapse_all_act.triggered.connect(self.collapse_all)
        self.expand_all_act.triggered.connect(self.expand_all)
        self.remove_variables_act.triggered.connect(self.remove_variables)
        self.sum_variables_act.triggered.connect(partial(self.aggregate_variables, "sum"))
        self.avg_variables_act.triggered.connect(partial(self.aggregate_variables, "mean"))

        # ~~~~ View Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt.textFiltered.connect(self.filter_treeview)
        self.view_tools_wgt.expandRequested.connect(self.expand_all)
        self.view_tools_wgt.collapseRequested.connect(self.collapse_all)
        self.view_tools_wgt.structureChanged.connect(self.on_settings_changed)

        # ~~~~ Tab Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.tabClosed.connect(self.on_tab_closed)
        self.tab_wgt.currentChanged.connect(self.on_current_tab_changed)
        self.tab_wgt.tabBarDoubleClicked.connect(self.on_tab_bar_double_clicked)
        self.tab_wgt.drop_btn.clicked.connect(self.load_files_from_fs)

        # ~~~~ Toolbar Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar.settingsUpdated.connect(self.on_settings_changed)
        self.toolbar.sum_btn.connect_action(self.sum_variables_act)
        self.toolbar.mean_btn.connect_action(self.avg_variables_act)
        self.toolbar.remove_btn.connect_action(self.remove_variables_act)
