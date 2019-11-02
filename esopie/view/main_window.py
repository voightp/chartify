import ctypes

from PySide2.QtWidgets import (QWidget, QSplitter, QHBoxLayout, QVBoxLayout,
                               QToolButton, QAction, QFileDialog, QSizePolicy,
                               QFrame, QMainWindow, QStatusBar)
from PySide2.QtCore import (QSize, Qt, QCoreApplication, QSettings,
                            Signal, QObject, QUrl)

from PySide2.QtGui import QIcon, QKeySequence, QColor
from PySide2.QtWebEngineWidgets import QWebEngineView

from esopie.view.icons import Pixmap, filled_circle_pixmap
from esopie.view.progress_widget import ProgressContainer
from esopie.view.misc_widgets import (DropFrame, TabWidget, MulInputDialog)
from esopie.view.buttons import MenuButton, IconMenuButton
from esopie.view.toolbar import Toolbar
from esopie.view.view_tools import ViewTools
from esopie.view.css_theme import CssTheme, parse_palette, Palette
from esopie.settings import Settings

from eso_reader.convertor import verify_units

from functools import partial
from esopie.view.view_widget import View


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QMainWindow):
    """ Main application instance. """
    QCoreApplication.setOrganizationName("piecompany")
    QCoreApplication.setOrganizationDomain("piecomp.foo")
    QCoreApplication.setApplicationName("piepie")

    css = CssTheme(Settings.CSS_PATH)
    palette = parse_palette(Settings.PALETTE_PATH, Settings.PALETTE_NAME)

    selectionUpdated = Signal(list)
    settingsChanged = Signal()
    paletteChanged = Signal(Palette)
    fileProcessingRequested = Signal(list)
    fileRenamed = Signal(str, str, str)
    variableRenamed = Signal(str, str, str, QObject)
    tabChanged = Signal(str, list)
    tabClosed = Signal(str)

    def __init__(self):
        super(MainWindow, self).__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setWindowTitle("pie pie")
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
        self.central_splitter.addWidget(self.right_main_wgt)

        # ~~~~ Right hand Chart Area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.main_chart_widget = QFrame(self.right_main_wgt)
        self.main_chart_layout = QHBoxLayout(self.main_chart_widget)
        self.right_main_layout.addWidget(self.main_chart_widget)

        self.web_view = QWebEngineView(self)
        self.main_chart_layout.addWidget(self.web_view)

        # ~~~~ Status bar ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.status_bar = QStatusBar(self)
        self.status_bar.setFixedHeight(20)
        self.setStatusBar(self.status_bar)

        self.progress_cont = ProgressContainer(self.status_bar)
        self.status_bar.addWidget(self.progress_cont)

        self.def_scheme = QAction("default", self)
        self.def_scheme.triggered.connect(partial(self.set_palette, "default"))

        self.mono_scheme = QAction("monochrome", self)
        self.mono_scheme.triggered.connect(partial(self.set_palette, "monochrome"))

        self.dark_scheme = QAction("dark", self)
        self.dark_scheme.triggered.connect(partial(self.set_palette, "dark"))

        actions = {"default": self.def_scheme,
                   "monochrome": self.mono_scheme,
                   "dark": self.dark_scheme}

        def_act = actions[Settings.PALETTE_NAME]

        self.scheme_btn = IconMenuButton(self, list(actions.values()))
        self.scheme_btn.setDefaultAction(def_act)

        self.swap_btn = QToolButton(self)
        self.swap_btn.clicked.connect(self.mirror_layout)
        self.swap_btn.setObjectName("swapButton")

        self.status_bar.addPermanentWidget(self.swap_btn)
        self.status_bar.addPermanentWidget(self.scheme_btn)

        # ~~~~ Menus ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.mini_menu = QWidget(self.toolbar)
        self.mini_menu_layout = QHBoxLayout(self.mini_menu)
        self.mini_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.mini_menu_layout.setSpacing(0)
        self.toolbar.layout.insertWidget(0, self.mini_menu)

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act = QAction("Load file | files", self)
        self.load_file_act.setShortcut(QKeySequence("Ctrl+L"))

        self.close_all_act = QAction("Close all", self)

        self.remove_act = QAction("Delete", self)

        self.hide_act = QAction("Hide", self)
        self.hide_act.setShortcut(QKeySequence("Ctrl+H"))

        self.remove_hidden_act = QAction("Remove hidden", self)

        self.show_hidden_act = QAction("Show hidden", self)
        self.show_hidden_act.setShortcut(QKeySequence("Ctrl+Shift+H"))

        self.sum_act = QAction("Sum", self)
        self.sum_act.setShortcut(QKeySequence("Ctrl+S"))

        self.mean_act = QAction("Mean", self)
        self.mean_act.setShortcut(QKeySequence("Ctrl+M"))

        self.collapse_all_act = QAction("Collapse All", self)
        self.collapse_all_act.setShortcut(QKeySequence("Ctrl+Shift+E"))

        self.expand_all_act = QAction("Expand All", self)
        self.expand_all_act.setShortcut(QKeySequence("Ctrl+E"))

        self.tree_act = QAction("Tree", self)
        self.tree_act.setShortcut(QKeySequence("Ctrl+T"))

        # TODO SAVE FUNCTIONS REQUIRED
        self.save_act = QAction("Save", self)
        self.save_as_act = QAction("Save as", self)

        # add actions to main window to allow shortcuts
        self.addActions([self.remove_act, self.hide_act, self.show_hidden_act,
                         self.sum_act, self.mean_act, self.collapse_all_act,
                         self.expand_all_act, self.tree_act])

        # disable actions as these will be activated on selection
        self.close_all_act.setEnabled(False)
        self.remove_act.setEnabled(False)
        self.hide_act.setEnabled(False)
        self.show_hidden_act.setEnabled(False)

        acts = [self.load_file_act, self.close_all_act]
        self.load_file_btn = MenuButton("Load file | files", self,
                                        actions=acts)

        acts = [self.save_act, self.save_as_act]
        self.save_btn = MenuButton("Tools", self,
                                   actions=acts)

        self.about_btn = MenuButton("About", self)

        self.load_file_btn.setObjectName("fileButton")
        self.save_btn.setObjectName("saveButton")
        self.about_btn.setObjectName("aboutButton")

        self.mini_menu_layout.addWidget(self.load_file_btn)
        self.mini_menu_layout.addWidget(self.save_btn)
        self.mini_menu_layout.addWidget(self.about_btn)

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.set_up_base_ui()
        self.load_css()

        # ~~~~ Set up web view ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.web_view.load(QUrl(Settings.URL))
        self.web_view.setAcceptDrops(True)

        # ~~~~ Connect main ui user actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.connect_ui_signals()

    @property
    def current_view(self):
        """ A currently selected outputs file. """
        return self.tab_wgt.currentWidget()

    def closeEvent(self, event):
        """ Shutdown all the background stuff. """
        Settings.SIZE = self.size()
        Settings.POSITION = self.pos()

        Settings.write_settings()

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:

            if not self.tab_wgt.is_empty():
                self.current_view.clear_selected()

        elif event.key() == Qt.Key_Delete:
            if self.hasFocus():
                self.remove_vars()

    def load_scheme_btn_icons(self):
        """ Create scheme button icons. """
        names = ["default", "dark", "monochrome"]
        acts = [self.def_scheme, self.dark_scheme, self.mono_scheme]

        k1 = "SECONDARY_COLOR"
        k2 = "BACKGROUND_COLOR"
        size = QSize(60, 60)
        border_col = QColor(255, 255, 255)

        for name, act in zip(names, acts):
            p = parse_palette(Settings.PALETTE_PATH, name)
            c1 = QColor(*p.get_color(k1, as_tuple=True))
            c2 = QColor(*p.get_color(k2, as_tuple=True))
            act.setIcon(filled_circle_pixmap(size, c1, col2=c2,
                                             border_col=border_col))

    def load_icons(self):
        root = Settings.ICONS_PATH
        c1 = self.palette.get_color("PRIMARY_TEXT_COLOR", as_tuple=True)
        c2 = self.palette.get_color("SECONDARY_TEXT_COLOR", as_tuple=True)

        myappid = 'foo'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            myappid)  # this sets toolbar icon on win 7

        self.setWindowIcon(Pixmap(root + "smile.png", 255, 255, 255))

        self.load_file_btn.setIcon(QIcon(Pixmap(root + "file.png", *c1)))
        self.save_btn.setIcon(QIcon(Pixmap(root + "save.png", *c1)))
        self.about_btn.setIcon(QIcon(Pixmap(root + "help.png", *c1)))
        self.close_all_act.setIcon(QIcon(Pixmap(root + "remove.png", *c1)))
        self.load_file_act.setIcon(QIcon(Pixmap(root + "add_file.png", *c1)))

        self.tab_wgt.drop_btn.setIcon(Pixmap(root + "drop_file.png", *c1))
        self.tab_wgt.drop_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.tab_wgt.drop_btn.setIconSize(QSize(50, 50))

        # TODO once colors have been decided, this can be moved to scheme btn init
        self.load_scheme_btn_icons()
        self.toolbar.load_icons(root, c1, c2)

    def set_up_base_ui(self):
        """ Set up appearance of main widgets. """
        self.central_layout.setSpacing(0)
        self.central_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Main left side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        left_side_policy = QSizePolicy()
        left_side_policy.setHorizontalPolicy(QSizePolicy.Minimum)
        left_side_policy.setHorizontalStretch(0)
        self.left_main_wgt.setSizePolicy(left_side_policy)
        self.left_main_layout.setSpacing(0)
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
        self.main_chart_widget.setMinimumWidth(400)

    def mirror_layout(self):
        """ Mirror the layout. """
        self.central_splitter.insertWidget(0, self.central_splitter.widget(1))

    def set_palette(self, name):
        """ Update the application palette. """
        if name != self.palette.name:
            Settings.PALETTE_NAME = name
            self.palette = parse_palette(Settings.PALETTE_PATH, name)
            self.load_css()
            self.paletteChanged.emit(self.palette)

    def load_css(self):
        """ Turn the CSS on and off. """
        self.css.set_palette(self.palette)

        # update the application appearance
        # css needs to be cleared to repaint the window
        self.setStyleSheet("")
        self.setStyleSheet(self.css.content)
        self.load_icons()

    def add_new_tab(self, id_, name):
        """ Add file on the UI. """
        wgt = self.create_view_wgt(id_, name)

        # add the new view into tab widget
        self.tab_wgt.add_tab(wgt, name)

        # enable all eso file results btn if there's multiple files
        if self.tab_wgt.count() > 1:
            self.toolbar.all_files_btn.setEnabled(True)
            self.close_all_act.setEnabled(True)

        # enable all eso file results btn if it's suitable
        if not self.tab_wgt.is_empty():
            self.toolbar.totals_btn.setEnabled(True)

    def build_view(self, variables, proxy_variables, interval, units):
        """ Create a new view when any of related settings change """
        is_tree = self.view_tools_wgt.tree_requested()
        filter_str = self.view_tools_wgt.get_filter_str()

        if not self.current_view:
            return

        self.current_view.update_model(variables, proxy_variables, is_tree,
                                       interval, units, filter_str=filter_str)

    def on_selection_populated(self, outputs):
        """ Store current selection in main app. """
        out_str = [" | ".join(var) for var in outputs]
        print("STORING!\n\t{}".format("\n\t".join(out_str)))

        # handle actions availability
        self.hide_act.setEnabled(True)
        self.remove_act.setEnabled(True)

        # check if variables can be aggregated
        units = verify_units([var.units for var in outputs])

        if len(outputs) > 1 and units:
            self.toolbar.set_tools_btns_enabled("sum", "mean", "remove")
        else:
            self.toolbar.set_tools_btns_enabled("sum", "mean", "remove",
                                                enabled=False)

        # store current selection in the model
        self.selectionUpdated.emit(outputs)

    def on_selection_cleared(self):
        """ Handle behaviour when no variables are selected. """
        # handle actions availability
        self.hide_act.setEnabled(False)
        self.remove_act.setEnabled(False)

        # switch to show hidden action, handle visibility based on child action
        self.toolbar.hide_btn.set_primary_state()
        self.toolbar.hide_btn.setEnabled(self.show_hidden_act.isEnabled())

        # disable export xlsx as there are no variables to be exported
        self.toolbar.set_tools_btns_enabled("sum", "mean",
                                            "remove", enabled=False)
        self.selectionUpdated.emit([])

    def create_view_wgt(self, id_, name):
        """ Create a 'View' widget and connect its actions. """
        # create an empty 'View' widget - the data will be
        # automatically populated on 'onTabChanged' signal
        wgt = View(id_, name)
        wgt.selectionCleared.connect(self.on_selection_cleared)
        wgt.selectionPopulated.connect(self.on_selection_populated)
        wgt.treeNodeChanged.connect(self.build_view)
        wgt.itemDoubleClicked.connect(self.rename_variable)
        wgt.context_menu_actions = [self.remove_act,
                                    self.hide_act,
                                    self.show_hidden_act]
        return wgt

    def filter_view(self, filter_string):
        """ Filter current view. """
        if not self.tab_wgt.is_empty():
            self.current_view.filter_view(filter_string)

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

        self.tabClosed.emit(id_)

    def on_tab_changed(self, index):
        """ Update view when tabChanged event is fired. """
        if index == -1:
            # there aren't any widgets available
            self.on_selection_cleared()
            self.toolbar.set_initial_layout()
        else:
            self.tabChanged.emit(self.current_view.id_,
                                 self.current_view.settings["header"])

    def load_files_from_os(self):
        """ Select eso files from explorer and start processing. """
        settings = QSettings()
        pth = settings.value("loadPath", "")
        file_pths, _ = QFileDialog.getOpenFileNames(self, "Load Eso File",
                                                    pth, "*.eso")
        if file_pths:
            # store last path for future
            settings.setValue("loadPath", file_pths[0])
            self.fileProcessingRequested.emit(file_pths)

    def rename_file(self, tab_index):
        """ Rename file on a tab identified by the given index. """
        view = self.tab_wgt.widget(tab_index)
        orig_name = view.name

        check_list = self.tab_wgt.get_all_child_names()[:]
        check_list.remove(orig_name)

        d = MulInputDialog("Enter a new file name.", self,
                           check_list=check_list, name=orig_name)
        res = d.exec_()

        if res == 0:
            return

        name = d.get_input("name")
        totals_name = f"{name} - totals"
        view.name = name

        self.tab_wgt.setTabText(tab_index, name)
        self.fileRenamed.emit(view.id_, name, totals_name)

    def rename_variable(self, var):
        """ Rename given variable. """
        # retrieve variable name from ui
        view = self.tab_wgt.widget(tab_index)
        msg = "Rename variable: "
        kwargs = {"variable name": var.variable,
                  "key name": var.key}

        dialog = MulInputDialog(msg, self, **kwargs)

        res = dialog.exec_()

        if res == 0:
            return

        var_nm = dialog.get_inputs_dct()["variable name"]
        key_nm = dialog.get_inputs_dct()["key name"]

        self.variableRenamed.emit(view.id_, var_nm, key_nm, var)

    def connect_ui_signals(self):
        """ Create actions which depend on user actions """
        # ~~~~ Widget Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt.fileDropped.connect(self.fileProcessingRequested.emit)

        # ~~~~ Actions Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act.triggered.connect(self.load_files_from_os)
        self.tree_act.triggered.connect(self.view_tools_wgt.tree_view_btn.toggle)
        self.collapse_all_act.triggered.connect(self.collapse_all)
        self.expand_all_act.triggered.connect(self.expand_all)

        # ~~~~ View Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt.textFiltered.connect(self.filter_view)
        self.view_tools_wgt.expandRequested.connect(self.expand_all)
        self.view_tools_wgt.collapseRequested.connect(self.collapse_all)
        self.view_tools_wgt.structureChanged.connect(self.settingsChanged.emit)

        # ~~~~ Tab Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.tabClosed.connect(self.on_tab_closed)
        self.tab_wgt.currentChanged.connect(self.on_tab_changed)
        self.tab_wgt.tabBarDoubleClicked.connect(self.rename_file)
        self.tab_wgt.drop_btn.clicked.connect(self.load_files_from_os)

        # ~~~~ Toolbar Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar.settingsUpdated.connect(self.settingsChanged.emit)
        self.toolbar.sum_btn.connect_action(self.sum_act)
        self.toolbar.mean_btn.connect_action(self.mean_act)
        self.toolbar.remove_btn.connect_action(self.remove_act)
