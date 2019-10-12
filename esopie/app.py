import sys
import os
import ctypes
import copy

from PySide2.QtWidgets import (QWidget, QSplitter, QHBoxLayout, QVBoxLayout,
                               QToolButton, QAction, QFileDialog, QSizePolicy,
                               QApplication, QMenu, QFrame, QMainWindow)
from PySide2.QtCore import (QSize, Qt, QThreadPool, QCoreApplication, QSettings,
                            QPoint)

from PySide2.QtGui import QIcon, QFontDatabase, QKeySequence, QColor

from esopie.eso_file_header import FileHeader
from esopie.icons import Pixmap, filled_circle_pixmap
from esopie.progress_widget import StatusBar, ProgressContainer
from esopie.misc_widgets import (DropFrame, TabWidget, MulInputDialog,
                                 ConfirmationDialog)
from esopie.buttons import MenuButton, IconMenuButton
from esopie.toolbar import Toolbar
from esopie.view_tools import ViewTools
from esopie.css_theme import CssTheme, get_palette
from esopie.chart_widgets import MyWebView

from esopie.utils.utils import generate_ids, get_str_identifier
from esopie.utils.process_utils import (create_pool, kill_child_processes,
                                        load_file, wait_for_results)

from eso_reader.eso_file import get_results
from eso_reader.convertor import verify_units

from queue import Queue
from functools import partial
from multiprocessing import Manager
from esopie.view_widget import View
from esopie.threads import (EsoFileWatcher, GuiMonitor, ResultsFetcher,
                            IterWorker)


def install_fonts(pth, database):
    files = os.listdir(pth)
    for file in files:
        p = os.path.join(pth, file)
        database.addApplicationFont(p)


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QMainWindow):
    """ Main application instance. """
    QCoreApplication.setOrganizationName("piecompany")
    QCoreApplication.setOrganizationDomain("piecomp.foo")
    QCoreApplication.setApplicationName("piepie")

    PALETTE_PATH = "../styles/palettes.json"
    CSS_PATH = "../styles/app_style.css"
    ICONS_PATH = "../icons/"

    css = CssTheme(CSS_PATH)
    palette = get_palette(PALETTE_PATH, QSettings().value("MainWindow/scheme",
                                                          "default"))

    def __init__(self):
        super(MainWindow, self).__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setWindowTitle("pie pie")
        self.setFocusPolicy(Qt.StrongFocus)

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

        # ~~~~ Intermediate settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.selected = None

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.file_queue = Queue()
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()

        # ~~~~ Status bar ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)

        self.progress_cont = ProgressContainer(self.status_bar,
                                               self.progress_queue)
        self.status_bar.addWidget(self.progress_cont)

        self.def_schm = QAction("default", self)
        self.def_schm.triggered.connect(partial(self.set_palette, "default"))

        self.mono_schm = QAction("monochrome", self)
        self.mono_schm.triggered.connect(partial(self.set_palette, "monochrome"))

        self.dark_schm = QAction("dark", self)
        self.dark_schm.triggered.connect(partial(self.set_palette, "dark"))

        actions = {"default": self.def_schm,
                   "monochrome": self.mono_schm,
                   "dark": self.dark_schm}

        def_act = actions[QSettings().value("MainWindow/scheme", "default")]

        self.scheme_btn = IconMenuButton(self, list(actions.values()))
        self.scheme_btn.setDefaultAction(def_act)

        self.swap_btn = QToolButton(self)
        self.swap_btn.clicked.connect(self.mirror)
        self.swap_btn.setObjectName("swapButton")

        self.status_bar.addPermanentWidget(self.swap_btn)
        self.status_bar.addPermanentWidget(self.scheme_btn)

        # ~~~~ Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # self.database = self.manager.dict() TODO simple dict might be sufficient
        self.database = {}

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TODO PASSING THE DATA TO DASH APP
        self.watcher = EsoFileWatcher(self.file_queue)
        self.watcher.loaded.connect(self.on_file_loaded)

        self.pool = create_pool()
        self.watcher.start()

        self.thread_pool = QThreadPool()

        # ~~~~ Menus ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.mini_menu = QWidget(self.toolbar)
        self.mini_menu_layout = QHBoxLayout(self.mini_menu)
        self.mini_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.mini_menu_layout.setSpacing(0)
        self.toolbar.layout.insertWidget(0, self.mini_menu)

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act = QAction("Load file | files", self)
        self.load_file_act.triggered.connect(self.load_files_from_os)
        self.load_file_act.setShortcut(QKeySequence("Ctrl+L"))

        self.close_all_act = QAction("Close all", self)
        self.close_all_act.triggered.connect(self.close_all_tabs)

        self.remove_act = QAction("Delete", self)
        self.remove_act.triggered.connect(self.remove_vars)

        self.hide_act = QAction("Hide", self)
        self.hide_act.triggered.connect(self.hide_vars)
        self.hide_act.setShortcut(QKeySequence("Ctrl+H"))

        self.remove_hidden_act = QAction("Remove hidden", self)
        self.remove_hidden_act.triggered.connect(self.remove_hidden_vars)

        self.show_hidden_act = QAction("Show hidden", self)
        self.show_hidden_act.triggered.connect(self.show_hidden_vars)
        self.show_hidden_act.setShortcut(QKeySequence("Ctrl+Shift+H"))

        self.sum_act = QAction("Sum", self)
        self.sum_act.triggered.connect(partial(self.add_var, "sum"))
        self.sum_act.setShortcut(QKeySequence("Ctrl+S"))

        self.mean_act = QAction("Mean", self)
        self.mean_act.triggered.connect(partial(self.add_var, "mean"))
        self.mean_act.setShortcut(QKeySequence("Ctrl+M"))

        self.collapse_all_act = QAction("Collapse All", self)
        self.collapse_all_act.triggered.connect(self.collapse_all)
        self.collapse_all_act.setShortcut(QKeySequence("Ctrl+Shift+E"))

        self.expand_all_act = QAction("Expand All", self)
        self.expand_all_act.triggered.connect(self.expand_all)
        self.expand_all_act.setShortcut(QKeySequence("Ctrl+E"))

        self.tree_act = QAction("Tree", self)
        self.tree_act.triggered.connect(self.view_tools_wgt.tree_view_btn.toggle)
        self.tree_act.setShortcut(QKeySequence("Ctrl+T"))

        # TODO SAVE FUNCTIONS REQUITED
        self.save_act = QAction("Save", self)
        self.save_act.triggered.connect(lambda x: print("SAVE ACT!"))

        self.save_as_act = QAction("Save as", self)
        self.save_as_act.triggered.connect(lambda x: print("SAVE AS ACT!"))

        # add actions to main window to allow shortcuts
        self.addActions([self.remove_act, self.hide_act, self.show_hidden_act,
                         self.sum_act, self.mean_act, self.collapse_all_act,
                         self.expand_all_act, self.tree_act])

        # disable actions as these will be activated on selection
        self.close_all_act.setEnabled(False)
        self.remove_act.setEnabled(False)
        self.hide_act.setEnabled(False)
        self.show_hidden_act.setEnabled(False)

        self.connect_ui_actions()

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

        # TODO reload css button (temporary)
        mn = QMenu(self)
        self.toolbar.stngs_btn.setMenu(mn)

        css = QAction("CSS", self)
        css.triggered.connect(self.load_css)

        no_css = QAction("NO CSS", self)
        no_css.triggered.connect(self.turn_off_css)

        memory = QAction("MEMORY", self)
        memory.triggered.connect(self.report_sizes)  # TODO REMOVE THIS

        dummy = QAction("DUMMY", self)
        dummy.triggered.connect(self.load_dummy)  # TODO REMOVE THIS

        self.toolbar.stngs_btn.setDefaultAction(dummy)

        mn.addActions([css, no_css, memory, dummy])

        self.chart_area = MyWebView(self, self.palette)
        self.main_chart_layout.addWidget(self.chart_area)

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.set_up_base_ui()
        self.load_css()
        self.load_settings()

    @property
    def current_view_wgt(self):
        """ A currently selected eso file. """
        return self.tab_wgt.get_current_widget()

    @property
    def current_view_wgts(self):
        """ A currently selected eso file. """
        all_ = self.all_files_requested()
        return self.all_view_wgts if all_ else [self.current_view_wgt]

    @property
    def all_other_view_wgts(self):
        """ A currently selected eso file. """
        all_ = self.current_view_wgts
        all_.remove(self.current_view_wgt)
        return all_

    @property
    def all_view_wgts(self):
        """ A list of all loaded eso files. """
        return self.tab_wgt.get_all_children()

    def load_settings(self):
        """ Apply application settings. """
        settings = QSettings()
        self.resize(settings.value("MainWindow/size", QSize(800, 600)))
        self.move(settings.value("MainWindow/pos", QPoint(50, 50)))

    def store_settings(self):
        """ Store application settings. """
        settings = QSettings()
        settings.setValue("MainWindow/size", self.size())
        settings.setValue("MainWindow/pos", self.pos())
        settings.setValue("MainWindow/scheme", self.palette.name)

        self.toolbar.store_settings()

    def closeEvent(self, event):
        """ Shutdown all the background stuff. """
        self.store_settings()

        self.watcher.terminate()
        self.progress_cont.monitor.terminate()
        self.manager.shutdown()

        kill_child_processes(os.getpid())

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:

            if not self.tab_wgt.is_empty():
                self.current_view_wgt.clear_selected()

        elif event.key() == Qt.Key_Delete:
            if self.hasFocus():
                self.remove_vars()

    def load_scheme_btn_icons(self):
        """ Create scheme button icons. """
        names = ["default", "dark", "monochrome"]
        acts = [self.def_schm, self.dark_schm, self.mono_schm]

        k1 = "SECONDARY_COLOR"
        k2 = "BACKGROUND_COLOR"
        size = QSize(60, 60)
        border_col = QColor(255, 255, 255)

        for name, act in zip(names, acts):
            p = get_palette(self.PALETTE_PATH, name)
            c1 = QColor(*p.get_color(k1, as_tuple=True))
            c2 = QColor(*p.get_color(k2, as_tuple=True))
            act.setIcon(filled_circle_pixmap(size, c1, col2=c2,
                                             border_col=border_col))

    def load_icons(self):
        root = self.ICONS_PATH
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

    # TODO debug to find memory leaks
    def report_sizes(self):
        from pympler import asizeof
        from pympler import summary
        from pympler import muppy
        import threading
        import multiprocessing
        print("Active threads", threading.active_count())
        print("Active processes", multiprocessing.active_children())
        all_objects = muppy.get_objects()
        sum1 = summary.summarize(all_objects)
        summary.print_(sum1)
        print("DB size", asizeof.asizeof(self.database))
        print("Executor size", asizeof.asizeof(self.pool))
        print("Monitor thread",
              asizeof.asizeof(self.progress_cont.monitor))
        print("Watcher thread", asizeof.asizeof(self.watcher))

    def load_dummy(self):
        """ Load a dummy file. """
        self.load_files(["../tests/eplusout.eso"])

    def mirror(self):
        """ Mirror the layout. """
        wgt = self.central_splitter.widget(1)
        self.central_splitter.insertWidget(0, wgt)

    def turn_off_css(self):
        """ Turn the CSS on and off. """
        self.setStyleSheet("")

    def set_palette(self, name):
        """ Update the application palette. """
        if name != self.palette.name:
            self.palette = get_palette(self.PALETTE_PATH, name)

            # notify web view to update chart layout colors
            flat = name in ["default", "dark"]

            self.chart_area.postman.set_appearance(flat, self.palette)
            self.load_css()

    def load_css(self):
        """ Turn the CSS on and off. """
        self.css.set_palette(self.palette)

        # update the application appearance
        # note that css needs to be cleared to repaint the window
        self.setStyleSheet("")
        self.setStyleSheet(self.css.content)
        self.load_icons()

    def get_current_interval(self):
        """ Get currently selected interval buttons. """
        return self.toolbar.get_selected_interval()

    def get_units_settings(self):
        """ Get current units settings. """
        return self.toolbar.get_units_settings()

    def all_files_requested(self):
        """ Check if results from all eso files are requested. """
        return self.toolbar.all_files_requested()

    def get_filter_str(self):
        """ Get current filter string. """
        return self.view_tools_wgt.get_filter_str()

    def tree_requested(self):
        """ Check if tree structure is requested. """
        return self.view_tools_wgt.tree_requested()

    def build_view(self):
        """ Create a new model when the tab or the interval has changed. """
        is_tree = self.tree_requested()
        interval = self.get_current_interval()
        units_settings = self.get_units_settings()
        filter_str = self.get_filter_str()

        view = self.current_view_wgt
        selection = self.selected

        if not view:
            return

        view.update_model(is_tree, interval, units_settings,
                          select=selection, filter_str=filter_str)

    def get_used_ids_from_db(self):
        """ Get a list of already used set ids. """
        return self.database.keys()

    def delete_sets_from_db(self, *args):
        """ Delete the eso file from the database. """
        for id_ in args:
            try:
                print(f"Deleting file id: '{id_}' from database.")
                del self.database[id_]
            except KeyError:
                print(f"Cannot delete eso file: id '{id_}',"
                      f"\nFile was not found in database.")

    def rename_file_in_db(self, id_, f_name, totals_f_name):
        """ Rename file in the databases. """
        try:
            f_set = self.database[id_]
            f_set[f"s{id_}"].rename(f_name)
            f_set[f"t{id_}"].rename(totals_f_name)
        except KeyError:
            print(f"Cannot rename eso file: id '{id_}',"
                  f"\nFile was not found in database.")

    def get_files_from_db(self, *args):
        """ Fetch eso files from the database. """
        files = []

        for set_id, file_dct in self.database.items():
            try:
                f = next(f for f_id, f in file_dct.items() if f_id in args)
                files.append(f)
            except StopIteration:
                pass

        if len(args) != len(files):
            diff = set(args).difference(set(files))
            diff_str = ", ".join(list(diff))
            print(f"Cannot find '{diff_str}' files in db!")

        return files

    def add_set_to_db(self, id_, file_set):
        """ Add processed eso file to the database. """
        try:
            self.database[id_] = file_set
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")

    def close_all_tabs(self):
        """ Delete all the content. """
        ids = []
        wgts = self.tab_wgt.close_all_tabs()
        for i in range(len(wgts)):
            ids.append(wgts[i].id_)
            wgts[i].deleteLater()

        self.delete_sets_from_db(*ids)
        self.toolbar.set_initial_layout()

    def items_selected(self, outputs):
        """ Store current selection in main app. """
        out_str = [" | ".join(var) for var in outputs]
        print("STORING!\n\t{}".format("\n\t".join(out_str)))

        # store current selection in the main app
        self.selected = outputs

        # switch to hide action
        self.toolbar.hide_btn.set_secondary_state()

        # always enable remove and export buttons
        self.toolbar.set_tools_btns_enabled("remove", "hide")

        # handle actions availability
        self.hide_act.setEnabled(True)
        self.remove_act.setEnabled(True)

        # check if variables can be aggregated
        units = verify_units([var.units for var in outputs])

        if len(outputs) > 1 and units:
            self.toolbar.set_tools_btns_enabled("sum", "mean")
        else:
            self.toolbar.set_tools_btns_enabled("sum", "mean", enabled=False)

    def selection_cleared(self):
        """ Handle behaviour when no variables are selected. """
        self.selected = None

        # handle actions availability
        self.hide_act.setEnabled(False)
        self.remove_act.setEnabled(False)

        # switch to show hidden action, handle visibility
        # based on child action
        self.toolbar.hide_btn.set_primary_state()
        self.toolbar.hide_btn.setEnabled(self.show_hidden_act.isEnabled())

        # disable export xlsx as there are no variables to be exported
        self.toolbar.set_tools_btns_enabled("sum", "mean",
                                            "remove", enabled=False)

    def create_view_wgt(self, id_, name, std_header, tot_header):
        """ Create a 'View' widget and connect its actions. """
        wgt = View(id_, name, std_header, tot_header)

        # connect view actions
        wgt.selectionCleared.connect(self.selection_cleared)
        wgt.selectionPopulated.connect(self.items_selected)
        wgt.updateView.connect(self.build_view)
        wgt.itemDoubleClicked.connect(self.rename_variable)
        wgt.context_menu_actions = [self.remove_act,
                                    self.hide_act,
                                    self.show_hidden_act]

        return wgt

    def on_file_loaded(self, id_, std_file, tot_file):
        """ Add eso file into 'tab' widget. """
        std_id = f"s{id_}"
        tot_id = f"t{id_}"

        # create unique file name
        names = self.tab_wgt.get_all_child_names()
        name = get_str_identifier(std_file.file_name, names)

        std_file.rename(name)
        tot_file.rename(f"{name} - totals")

        # copy header dicts as view and file should be independent
        std_header_dct = copy.deepcopy(std_file.header_dct)
        tot_header_dct = copy.deepcopy(tot_file.header_dct)

        std_header = FileHeader(std_id, std_header_dct)
        tot_header = FileHeader(tot_id, tot_header_dct)

        file_set = {std_id: std_file,
                    tot_id: tot_file}

        self.add_set_to_db(id_, file_set)

        wgt = self.create_view_wgt(id_, name, std_header, tot_header)

        # add the new view into tab widget
        self.tab_wgt.add_tab(wgt, name)

        # enable all eso file results btn if there's multiple files
        if self.tab_wgt.count() > 1:
            self.toolbar.all_files_btn.setEnabled(True)
            self.close_all_act.setEnabled(True)

        # enable all eso file results btn if it's suitable
        if not self.tab_wgt.is_empty():
            self.toolbar.totals_btn.setEnabled(True)

    def filter_view(self, filter_string):
        """ Filter current view. """
        if not self.tab_wgt.is_empty():
            self.current_view_wgt.filter_view(filter_string)

    def expand_all(self):
        """ Expand all tree view items. """
        if self.current_view_wgt:
            self.current_view_wgt.expandAll()

    def collapse_all(self):
        """ Collapse all tree view items. """
        if self.current_view_wgt:
            self.current_view_wgt.collapseAll()

    def remove_eso_file(self, wgt):
        """ Delete current eso file. """
        id_ = wgt.id_

        wgt.deleteLater()
        self.delete_sets_from_db(id_)

        if self.tab_wgt.is_empty():
            self.toolbar.totals_btn.setEnabled(False)

        if self.tab_wgt.count() <= 1:
            self.toolbar.all_files_btn.setEnabled(False)
            self.close_all_act.setEnabled(False)

    def on_tab_changed(self, index):
        """ Update view when tabChanged event is fired. """
        if index != -1:
            # update interval buttons state
            intervals = self.current_view_wgt.get_available_intervals()
            self.toolbar.update_intervals_state(intervals)
            # update the view
            self.build_view()
            # hide or show interval buttons based on availability
            self.toolbar.populate_intervals_group()
        else:
            # there aren't any widgets available
            self.selection_cleared()
            self.toolbar.set_initial_layout()

    def load_files(self, eso_file_paths):
        """ Start eso file processing. """
        progress_queue = self.progress_queue
        file_queue = self.file_queue

        used_ids = self.get_used_ids_from_db()
        n = len(eso_file_paths)
        ids = generate_ids(used_ids, n=n)

        for path in eso_file_paths:
            # create a monitor to report progress on the ui
            id_ = ids.pop(0)
            monitor = GuiMonitor(path, id_, progress_queue)

            # create a new process to load eso file
            future = self.pool.submit(load_file, path, monitor=monitor,
                                      suppress_errors=False)

            func = partial(wait_for_results, id_, monitor, file_queue)
            future.add_done_callback(func)

    def load_files_from_os(self):
        """ Select eso files from explorer and start processing. """
        settings = QSettings()
        pth = settings.value("loadPath", "")
        file_pths, _ = QFileDialog.getOpenFileNames(self, "Load Eso File",
                                                    pth, "*.eso")
        if file_pths:
            self.load_files(file_pths)
            settings.setValue("loadPath", file_pths[0])

    def rename_file(self, tab_index):
        """ Rename file on a tab identified by the given index. """
        view = self.tab_wgt.widget(tab_index)
        orig_name = view.name

        # create a list of names which won't be acceptable
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
        rename_file_in_db(view.id_, name, totals_name)

        self.tab_wgt.setTabText(tab_index, name)

    def export_xlsx(self):
        """ Export selected variables data to xlsx. """
        self.get_results()

        # file_pth, _ = QFileDialog.getSaveFileName(self, "Save variable to .xlsx", "", "*.xlsx")
        # if file_pth:
        #     import time
        #     s = time.perf_counter()
        #     df = self.results_df()
        #     e = time.perf_counter()
        #     print("Fetching results: {}".format((e-s)))
        #     s = time.perf_counter()
        #     # df.to_excel(file_pth)
        #     e = time.perf_counter()
        #     print("Printing file: {}".format((e - s)))

    def on_totals_change(self, change):
        """ Switch current views to 'totals' and back. """
        View.totals = change  # update class variable to request totals
        self.build_view()

    def apply_async(self, func, *args, **kwargs):
        """ A wrapper to apply functions to current views. """
        # apply function to the current widget
        view = self.current_view_wgt
        val = func(view, *args, **kwargs)

        # apply function to all other widgets asynchronously
        others = self.all_other_view_wgts
        if others:
            w = IterWorker(func, others, *args, **kwargs)
            self.thread_pool.start(w)

        return val

    def rename_variable(self, variable):
        """ Rename given variable. """
        # retrieve variable name from ui
        msg = "Rename variable: "
        res = self.get_var_name([variable], msg)  # TODO maybe customize?

        if res:
            var_nm, key_nm = res
            var = self.apply_async(self.rename_var, var_nm,
                                   key_nm, variable)
            self.selected = [var]
            self.build_view()
            self.current_view_wgt.scroll_to(var)

    def dump_vars(self, view, variables, remove=False):
        """ Hide or remove selected variables. """
        file_id = view.get_file_id()
        file = self.get_files_from_db(file_id)[0]

        groups = file.find_pairs(variables)

        if not groups:
            return

        if remove:
            view.remove_header_variables(groups)
            file.remove_outputs(variables)
        else:
            view.hide_header_variables(groups)

        view.set_next_update_forced()

    def show_hidden_vars(self):
        """ Show previously hidden variables. """
        for view in self.current_view_wgts:
            view.show_hidden_header_variables()
            view.set_next_update_forced()

        self.show_hidden_act.setEnabled(False)
        self.toolbar.hide_btn.setEnabled(False)

        self.build_view()

    def remove_hidden_vars(self):
        """ Remove hidden variables. """
        for view in self.current_view_wgts:
            view.remove_hidden_header_variables()

    def rename_var(self, view, var_nm, key_nm, variable):
        """ Rename given 'Variable'. """
        file_id = view.get_file_id()
        file = self.get_files_from_db(file_id)[0]

        res = file.rename_variable(variable, var_nm, key_nm)
        if res:
            var_id, var = res
            # add variable will replace current variable
            view.add_header_variable(var_id, var)
            view.set_next_update_forced()

            return var

    def aggr_vars(self, view, var_nm, key_nm, variables, func):
        """ Add a new aggreagated variable to the file. """
        file_id = view.get_file_id()

        # files are always returned as list
        file = self.get_files_from_db(file_id)[0]

        res = file.aggregate_variables(variables, func,
                                       key_nm=key_nm,
                                       var_nm=var_nm,
                                       part_match=False)
        if res:
            var_id, var = res
            view.add_header_variable(var_id, var)
            view.set_next_update_forced()

            return var

    def get_var_name(self, variables, msg=""):
        """ Retrieve new variable data from the ui. """
        var_nm = "Custom Variable"
        key_nm = "Custom Key"

        if all(map(lambda x: x.variable == variables[0].variable, variables)):
            var_nm = variables[0].variable

        if all(map(lambda x: x.key == variables[0].key, variables)):
            key_nm = variables[0].key

        # retrieve custom inputs from a user
        kwargs = {"variable name": var_nm,
                  "key name": key_nm}

        dialog = MulInputDialog(msg, self, **kwargs)
        res = dialog.exec()

        if res == 0:
            return

        var_nm = dialog.get_inputs_dct()["variable name"]
        key_nm = dialog.get_inputs_dct()["key name"]

        return var_nm, key_nm

    def add_var(self, aggr_func):
        """ Create a new variable using given aggr function. """
        variables = self.get_current_request()

        # retrieve variable name from ui
        msg = "Enter details of the new variable: "
        res = self.get_var_name(variables, msg=msg)

        if res:
            var_nm, key_nm = res
            var = self.apply_async(self.aggr_vars, var_nm, key_nm,
                                   variables, aggr_func)

            self.selected = [var]
            self.build_view()
            self.current_view_wgt.scroll_to(var)

    def remove_vars(self):
        """ Remove variables from a file. """
        variables = self.get_current_request()

        if not variables:
            return

        all_ = self.all_files_requested()
        nm = self.tab_wgt.tabText(self.tab_wgt.currentIndex())

        files = "all files" if all_ else f"file '{nm}'"
        text = f"Delete following variables from {files}: "

        inf_text = "\n".join([" | ".join(var[1:3]) for var in variables])

        dialog = ConfirmationDialog(self, text, det_text=inf_text)
        res = dialog.exec_()

        if res == 0:
            return

        self.apply_async(self.dump_vars, variables, remove=True)
        self.build_view()

    def hide_vars(self):
        """ Temporarily hide variables. """
        variables = self.get_current_request()
        self.apply_async(self.dump_vars, variables)

        # allow showing variables again
        self.show_hidden_act.setEnabled(True)
        self.toolbar.hide_btn.setEnabled(True)

        self.build_view()

    def get_current_file_ids(self):
        """ Return current file id or ids based on 'all files btn' state. """
        if self.all_files_requested():
            return [f.get_file_id() for f in self.all_view_wgts]

        return [self.current_view_wgt.get_file_id()]

    def get_current_request(self):
        """ Get a currently selected output variables information. """
        return self.selected

    def get_results(self, callback=None, **kwargs):
        """ Get output values for given variables. """
        variables = self.get_current_request()
        rate_to_energy, units_system, energy, power = self.get_units_settings()
        rate_to_energy_dct = {self.get_current_interval(): rate_to_energy}

        ids = self.get_current_file_ids()
        files = self.get_files_from_db(*ids)

        args = (files, variables)
        kwargs = {"rate_units": power, "energy_units": energy,
                  "add_file_name": "column",
                  "rate_to_energy_dct": rate_to_energy_dct,
                  **kwargs}

        self.thread_pool.start(ResultsFetcher(get_results, *args,
                                              callback=callback, **kwargs))

    def connect_ui_actions(self):
        """ Create actions which depend on user actions """
        # ~~~~ View Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt.fileDropped.connect(self.load_files)
        self.view_tools_wgt.filterViewItems.connect(self.filter_view)
        self.view_tools_wgt.updateView.connect(self.build_view)
        self.view_tools_wgt.expandViewItems.connect(self.expand_all)
        self.view_tools_wgt.collapseViewItems.connect(self.collapse_all)

        # ~~~~ Tab actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.tabClosed.connect(self.remove_eso_file)
        self.tab_wgt.currentChanged.connect(self.on_tab_changed)
        self.tab_wgt.fileLoadRequested.connect(self.load_files_from_os)
        self.tab_wgt.tabRenameRequested.connect(self.rename_file)

        # ~~~~ Outputs actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar.updateView.connect(self.build_view)
        self.toolbar.totalsChanged.connect(self.on_totals_change)
        self.toolbar.sum_btn.connect_action(self.sum_act)
        self.toolbar.mean_btn.connect_action(self.mean_act)
        self.toolbar.remove_btn.connect_action(self.remove_act)

        self.toolbar.hide_btn.set_actions(self.show_hidden_act.trigger,
                                          self.hide_act.trigger)


if __name__ == "__main__":
    sys_argv = sys.argv
    app = QApplication()
    db = QFontDatabase()
    install_fonts("../resources", db)

    db.addApplicationFont("./resources/Roboto-Regular.ttf")
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
