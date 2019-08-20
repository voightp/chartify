import sys
import os
import ctypes
import loky
import psutil
import copy

from PySide2.QtWidgets import (QWidget, QSplitter, QHBoxLayout, QVBoxLayout,
                               QToolButton, QAction, QFileDialog, QSizePolicy,
                               QApplication, QMenu, QFrame, QMainWindow)
from PySide2.QtCore import (QSize, Qt, QThreadPool, QCoreApplication, QSettings,
                            QPoint, QUrl)
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PySide2.QtGui import QIcon, QPixmap, QFontDatabase, QKeySequence

from esopie.eso_file_header import FileHeader
from esopie.icons import Pixmap, text_to_pixmap
from esopie.progress_widget import StatusBar, ProgressContainer
from esopie.misc_widgets import (DropFrame, TabWidget, MulInputDialog,
                                 ConfirmationDialog)
from esopie.buttons import MenuButton
from esopie.toolbar import Toolbar
from esopie.view_tools import ViewTools
from esopie.css_theme import CssTheme, Palette
from functools import partial

from eso_reader.eso_file import EsoFile, get_results, IncompleteFile
from eso_reader.building_eso_file import BuildingEsoFile
from eso_reader.mini_classes import Variable
from eso_reader.convertor import verify_units

from queue import Queue
from multiprocessing import Manager, cpu_count
from esopie.view_widget import View
from random import randint
from esopie.threads import (EsoFileWatcher, GuiMonitor, ResultsFetcher,
                            IterWorker)


def create_pool():
    """ Create a new process pool. """
    n_cores = cpu_count()
    workers = (n_cores - 1) if n_cores > 1 else 1
    return loky.get_reusable_executor(max_workers=workers)


def kill_pool():
    """ Shutdown the process pool. """
    loky.get_reusable_executor().shutdown(wait=False, kill_workers=True)


def generate_ids(used_ids, n=1, max_id=99999):
    """ Create a list with unique ids. """
    ids = []
    while True:
        id_ = randint(1, max_id)
        if id_ not in used_ids and id_ not in ids:
            ids.append(id_)
            if len(ids) == n:
                break
    return ids


def create_unique_name(name, check_list):
    """ Create a unique name to avoid duplicates. """

    def add_num():
        return f"{name} ({i})"

    new_name = name
    i = 0

    # add unique number if the file name is not unique
    while new_name in check_list:
        i += 1
        new_name = add_num()

    return new_name


def kill_child_processes(parent_pid):
    """ Terminate all running child processes. """
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for p in children:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            continue


def load_file(path, monitor=None, suppress_errors=False):
    """ Process eso file. """
    std_file = EsoFile(path, monitor=monitor, suppress_errors=suppress_errors)
    tot_file = BuildingEsoFile(std_file)
    monitor.building_totals_finished()
    return std_file, tot_file


def wait_for_results(id_, monitor, queue, future):
    """ Put loaded file into the queue and clean up the pool. """
    try:
        std_file, tot_file = future.result()
        queue.put((id_, std_file, tot_file))

    except IncompleteFile:
        print("File '{}' is not complete -"
              " processing failed.".format(monitor.path))
        monitor.processing_failed("Processing failed!")

    except BrokenPipeError:
        print("The application is being closed - "
              "catching broken pipe.")

    except loky.process_executor.BrokenProcessPool:
        print("The application is being closed - "
              "catching broken process pool executor.")


def install_fonts(pth, database):
    files = os.listdir(pth)
    for file in files:
        p = os.path.join(pth, file)
        database.addApplicationFont(p)


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QMainWindow):
    palette = Palette(**{
        "PRIMARY_COLOR": "#aeaeae",
        "PRIMARY_VARIANT_COLOR": None,
        "PRIMARY_TEXT_COLOR": "rgb(112,112,112)",
        "SECONDARY_COLOR": "#ff8a65",
        "SECONDARY_VARIANT_COLOR": None,
        "SECONDARY_TEXT_COLOR": "#EEEEEE",
        "BACKGROUND_COLOR": "#c2c2c2",
        "SURFACE_COLOR": "#f5f5f5",
        "ERROR_COLOR": "#b71c1c",
        "OK_COLOR": "#64DD17",
    })
    css = CssTheme(palette)

    QCoreApplication.setOrganizationName("piecompany")
    QCoreApplication.setOrganizationDomain("piecomp.foo")
    QCoreApplication.setApplicationName("piepie")

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

        self.swap_btn = QToolButton(self)
        self.swap_btn.clicked.connect(self.mirror)
        self.swap_btn.setObjectName("swapButton")

        self.status_bar.addPermanentWidget(self.swap_btn)

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

        dummy = QAction(self)
        dummy.triggered.connect(lambda: print("DUM UMD"))
        dummy.setShortcut(QKeySequence("Ctrl+L"))

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
                                        func=self.load_files_from_os,
                                        actions=acts)

        self.save_all_btn = MenuButton("Save", self,
                                       func=lambda: print("NEEDS FUNCTION TO SAVE"))

        self.about_btn = MenuButton("About", self,
                                    func=lambda: print("NEEDS FUNCTION TO ABOUT"))

        self.load_file_btn.setObjectName("fileButton")
        self.save_all_btn.setObjectName("saveButton")
        self.about_btn.setObjectName("aboutButton")

        self.mini_menu_layout.addWidget(self.load_file_btn)
        self.mini_menu_layout.addWidget(self.save_all_btn)
        self.mini_menu_layout.addWidget(self.about_btn)

        # TODO reload css button (temporary)
        mn = QMenu(self)
        self.toolbar.stngs_btn.setMenu(mn)

        css = QAction("CSS", self)
        css.triggered.connect(self.toggle_css)

        no_css = QAction("NO CSS", self)
        no_css.triggered.connect(self.turn_off_css)

        memory = QAction("MEMORY", self)
        memory.triggered.connect(self.report_sizes)  # TODO REMOVE THIS

        dummy = QAction("DUMMY", self)
        dummy.triggered.connect(self.load_dummy)  # TODO REMOVE THIS

        colors = QAction("COLORS", self)
        colors.triggered.connect(self.update_colors)  # TODO REMOVE THIS

        self.toolbar.stngs_btn.setDefaultAction(dummy)

        mn.addActions([css, no_css, memory, dummy, colors])

        # TODO create custom chart area
        # self.chart_area = QWebEngineView(self)
        # settings = QWebEngineSettings.JavascriptCanAccessClipboard
        # self.chart_area.settings().setAttribute(settings, True)
        # self.chart_area.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.chart_area.setAcceptDrops(True)
        # self.url = "http://127.0.0.1:8080/"
        # self.chart_area.load(QUrl(self.url))
        # self.main_chart_layout.addWidget(self.chart_area)

        self.dummy = QFrame(self.main_chart_widget)
        self.main_chart_layout.addWidget(self.dummy)

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_icons()
        self.set_up_base_ui()
        self.toggle_css()
        self.read_settings()

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

    def read_settings(self):
        """ Apply application settings. """
        settings = QSettings()
        self.resize(settings.value("MainWindow/size", QSize(800, 600)))
        self.move(settings.value("MainWindow/pos", QPoint(50, 50)))

    def store_settings(self):
        """ Store application settings. """
        settings = QSettings()
        settings.setValue("MainWindow/size", self.size())
        settings.setValue("MainWindow/pos", self.pos())

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
            self.remove_vars()

    def load_icons(self):
        r = "../icons/"
        c1 = self.palette.get_color("PRIMARY_TEXT_COLOR", as_tuple=True)
        c2 = self.palette.get_color("SECONDARY_TEXT_COLOR", as_tuple=True)

        myappid = 'foo'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            myappid)  # this sets toolbar icon on win 7

        self.setWindowIcon(Pixmap(r + "smile.png", 255, 255, 255))

        self.load_file_btn.setIcon(QIcon(Pixmap(r + "file.png", *c1)))
        self.save_all_btn.setIcon(QIcon(Pixmap(r + "save.png", *c1)))
        self.about_btn.setIcon(QIcon(Pixmap(r + "help.png", *c1)))
        self.close_all_act.setIcon(QIcon(Pixmap(r + "remove.png", *c1)))
        self.load_file_act.setIcon(QIcon(Pixmap(r + "add_file.png", *c1)))

        self.toolbar.totals_btn.set_icons(Pixmap(r + "building.png", *c1),
                                          Pixmap(r + "building.png", *c2))
        self.toolbar.totals_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.totals_btn.setIconSize(QSize(20, 20))

        self.toolbar.all_files_btn.set_icons(Pixmap(r + "all_files.png", *c1),
                                             Pixmap(r + "all_files.png", *c2))
        self.toolbar.all_files_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.all_files_btn.setIconSize(QSize(20, 20))

        self.tab_wgt.drop_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.tab_wgt.drop_btn.setIcon(Pixmap(r + "drop_file.png", *c1))
        self.tab_wgt.drop_btn.setIconSize(QSize(50, 50))

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

    # TODO dialog to choose colors
    def update_colors(self):
        parsed = {}
        for k, v in self.palette.colors_dct.items():
            sv = f"rgb({v[0]},{v[1]},{v[2]})"
            parsed[k] = sv

        d = MulInputDialog("choose colors", self, **parsed)
        res = d.exec_()

        if res == 0:
            return

        dct = d.get_inputs_dct()
        self.palette = Palette(**dct)
        self.toggle_css()

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

    def toggle_css(self):
        """ Turn the CSS on and off. """
        self.setStyleSheet("")
        self.css = CssTheme(self.palette)
        cont = self.css.process_csss("../styles/app_style.css")
        self.setStyleSheet(cont)

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
        try:
            for id_ in args:
                print(f"Deleting file id: '{id_}' from database.")
                del self.database[id_]

        except KeyError:
            print(f"Cannot delete the eso file: id '{id_}',"
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

        # always enable remove and export buttons
        self.toolbar.enable_tools_btns(True, exclude=["sum", "mean"])

        # handle actions availability
        self.hide_act.setEnabled(True)
        self.remove_act.setEnabled(True)

        # check if variables can be aggregated
        units = verify_units([var.units for var in outputs])
        if len(outputs) > 1 and units:
            self.toolbar.enable_tools_btns(True, exclude=["xlsx", "remove"])
        else:
            self.toolbar.enable_tools_btns(False, exclude=["xlsx", "remove"])

    def selection_cleared(self):
        """ Handle behaviour when no variables are selected. """
        self.selected = None

        # handle actions availability
        self.hide_act.setEnabled(False)
        self.remove_act.setEnabled(False)

        # disable export xlsx as there are no variables to be exported
        self.toolbar.enable_tools_btns(False)

    def create_variable(variables, interval, key, var, units):
        """ Create a unique header variable. """

        def is_unique():
            return variable not in variables

        def add_num():
            new_key = f"{key} ({i})"
            return Variable(interval, new_key, var, units)

        variable = Variable(interval, key, var, units)

        i = 0
        while not is_unique():
            i += 1
            variable = add_num()

        return variable

    def create_view_wgt(self, id_, f_name, std_header, tot_header):
        """ Create a 'View' widget and connect its actions. """
        names = self.tab_wgt.get_all_child_names()
        name = create_unique_name(f_name, names)

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

        # copy header dicts as view and file should be independent
        std_header_dct = copy.deepcopy(std_file.header_dct)
        tot_header_dct = copy.deepcopy(tot_file.header_dct)

        std_header = FileHeader(std_id, std_header_dct)
        tot_header = FileHeader(tot_id, tot_header_dct)

        file_set = {std_id: std_file,
                    tot_id: tot_file}

        self.add_set_to_db(id_, file_set)

        f_name = std_file.file_name
        wgt = self.create_view_wgt(id_, f_name, std_header, tot_header)

        # add the new view into tab widget
        self.tab_wgt.add_tab(wgt, wgt.name)

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

        # update name references
        # TODO decide if database names should be handled as well
        view.name = name
        self.tab_wgt.setTabText(tab_index, name)

    def export_xlsx(self):
        """ Export selected variables data to xlsx. """
        self.results_df()

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
        """ Hide or remove the """
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
        """ Add a new variable to the file. """
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
        self.build_view()

    def get_current_file_ids(self):
        """ Return current file id or ids based on 'all files btn' state. """
        if self.all_files_requested():
            return [f.get_file_id() for f in self.all_view_wgts]

        return [self.current_view_wgt.get_file_id()]

    def get_current_request(self):
        """ Get a currently selected output variables information. """
        return self.selected

    def results_df(self):
        """ Get output values for given variables. """
        variables = self.get_current_request()
        rate_to_energy, units_system, energy, power = self.get_units_settings()
        rate_to_energy_dct = {self.get_current_interval(): rate_to_energy}

        ids = self.get_current_file_ids()
        files = self.get_files_from_db(*ids)

        args = (get_results, files, variables)
        kwargs = ddict(rate_units=power, energy_units=energy,
                       add_file_name="column",
                       rate_to_energy_dct=rate_to_energy_dct)

        self.thread_pool.start(ResultsFetcher(*args, **kwargs))

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
        self.toolbar.meanRequested.connect(self.mean_act.trigger)
        self.toolbar.sumRequested.connect(self.sum_act.trigger)
        self.toolbar.totalsChanged.connect(self.on_totals_change)


if __name__ == "__main__":
    sys_argv = sys.argv
    app = QApplication()
    db = QFontDatabase()
    install_fonts("../resources", db)

    db.addApplicationFont("./resources/Roboto-Regular.ttf")
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
