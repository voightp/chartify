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
                            QPoint)
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PySide2.QtGui import QIcon, QPixmap, QFontDatabase, QKeySequence

from esopie.eso_file_header import FileHeader
from esopie.icons import Pixmap, text_to_pixmap
from esopie.progress_widget import StatusBar, ProgressContainer
from esopie.misc_widgets import DropFrame, TabWidget, MulInputDialog, ConfirmationDialog
from esopie.buttons import MenuButton
from esopie.toolbar import Toolbar
from esopie.view_tools import ViewTools
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
        id = randint(1, max_id)
        if id not in used_ids and id not in ids:
            ids.append(id)
            if len(ids) == n:
                break
    return ids


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


def act_factory(text, parent, func=None, icon_pth=None, shortcut=None):
    """ Wrapper to generate an action. """
    act = QAction(text, parent)

    if icon_pth:
        act.setIcon(QIcon(icon_pth))

    if func:
        act.triggered.connect(func)

    if shortcut:
        act.setShortcut(QKeySequence(shortcut))

    return act


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QMainWindow):
    # todo create color schemes
    background_color = {"r": 255, "g": 255, "b": 255}
    primary_color = {"r": 112, "g": 112, "b": 112}
    secondary_color = {"r": 112, "g": 112, "b": 112}

    QCoreApplication.setOrganizationName("piecompany")
    QCoreApplication.setOrganizationDomain("piecomp.foo")
    QCoreApplication.setApplicationName("piepie")

    def __init__(self):
        super(MainWindow, self).__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setWindowTitle("pie pie")
        self.read_settings()

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
        self.main_chart_widget = QWidget(self.right_main_wgt)
        self.main_chart_layout = QHBoxLayout(self.main_chart_widget)
        self.right_main_layout.addWidget(self.main_chart_widget)

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.connect_ui_actions()
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

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

        pix = Pixmap("../icons/swap_black.png", **self.primary_color)
        self.swap_btn.setIcon(pix)
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

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_file_act = act_factory("Load file | files", self,
                                         func=self.load_files_from_os,
                                         icon_pth="../icons/add_file_grey.png",
                                         shortcut="Ctrl+L")

        self.close_all_act = act_factory("Close all", self,
                                         self.close_all_tabs,
                                         icon_pth="../icons/remove_grey.png")

        self.remove_act = act_factory("Delete", self,
                                      func=self.remove_vars)

        self.hide_act = act_factory("Hide", self,
                                    func=self.hide_vars)

        self.remove_hidden_act = act_factory("Remove hidden", self,
                                             func=self.remove_hidden_vars)

        self.show_hidden_act = act_factory("Show hidden", self,
                                           func=self.show_hidden_vars)
        # disable actions as these will be activated on selection
        self.close_all_act.setEnabled(False)
        self.remove_act.setEnabled(False)
        self.hide_act.setEnabled(False)
        self.show_hidden_act.setEnabled(False)

        sz = QSize(25, 25)
        acts = [self.load_file_act, self.close_all_act]
        load_file_btn = MenuButton(QIcon("../icons/file_grey.png"),
                                   "Load file | files", self,
                                   sz, self.load_files_from_os, acts)

        self.mini_menu_layout.addWidget(load_file_btn)

        save_all = MenuButton(QIcon("../icons/save_grey.png"),
                              "Save", self, sz,
                              lambda: print("NEEDS FUNCTION TO SAVE"))

        self.mini_menu_layout.addWidget(save_all)

        about_btn = MenuButton(QIcon("../icons/help_grey.png"),
                               "Save", self, sz,
                               lambda: print("NEEDS FUNCTION TO ABOUT"))

        self.mini_menu_layout.addWidget(about_btn)

        # TODO reload css button (temporary)
        mn = QMenu(self)
        self.toolbar.stngs_btn.setMenu(mn)

        css = QAction("C", self)
        css.triggered.connect(self.toggle_css)

        no_css = QAction("N C", self)
        no_css.triggered.connect(self.turn_off_css)

        memory = QAction("M", self)
        memory.triggered.connect(self.report_sizes)  # TODO REMOVE THIS

        dummy = QAction("D", self)
        dummy.triggered.connect(self.load_dummy)  # TODO REMOVE THIS

        mn.addActions([css, no_css, memory, dummy])

        self.chart_area = QWebEngineView(self)
        # TODO create custom chart area
        settings = QWebEngineSettings.JavascriptCanAccessClipboard
        self.chart_area.settings().setAttribute(settings, True)

        self.main_chart_layout.addWidget(self.chart_area)
        # self.chart_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chart_area.setAcceptDrops(True)

        self.url = "http://127.0.0.1:8080/"
        # self.chart_area.load(QUrl(self.url))

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_icons()
        self.set_up_base_ui()
        self.toggle_css()

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
        return self.tab_wgt.get_all_widgets()

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

        # TODO handle loosing focus to chart area

    def contextMenuEvent(self, event):
        """ Manage context menu. """
        actions = [self.remove_act,
                   self.hide_act,
                   self.show_hidden_act]

        # available = [a for a in actions if a.isEnabled()] TODO decide if hide

        menu = QMenu(self)
        menu.setObjectName("contextMenu")
        menu.addActions(actions)

        menu.exec_(self.mapToGlobal(event.pos()))

    def load_icons(self):
        myappid = 'foo'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            myappid)  # this sets toolbar icon on win 7

        self.setWindowIcon(QPixmap("../icons/twotone_pie_chart.png"))

    def set_up_base_ui(self):
        """ Set up appearance of main widgets. """
        self.central_layout.setSpacing(0)
        self.central_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Main left side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        left_side_size_policy = QSizePolicy()
        left_side_size_policy.setHorizontalStretch(0)
        self.left_main_wgt.setSizePolicy(left_side_size_policy)
        self.left_main_layout.setSpacing(0)
        self.left_main_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.tab_wgt.setMinimumWidth(400)

        self.view_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.setSpacing(0)

        self.view_tools_wgt.setSizePolicy(QSizePolicy.Minimum,
                                          QSizePolicy.Fixed)

        # ~~~~ Main right side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        right_side_size_policy = QSizePolicy()
        right_side_size_policy.setHorizontalStretch(1)
        self.right_main_wgt.setSizePolicy(right_side_size_policy)
        self.right_main_layout.setSpacing(0)
        self.right_main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_chart_widget.setSizePolicy(QSizePolicy.Expanding,
                                             QSizePolicy.Expanding)
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

    def toggle_css(self):
        """ Turn the CSS on and off. """
        with open("../styles/app_style.css", "r") as file:
            cont = file.read()

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
            print(f"Cannot delete the eso file: id '{file_id}',"
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

    def create_view_wgt(self, id_, std_file_header, tot_file_header):
        """ Create a 'View' widget and connect its actions. """
        wgt = View(id_, std_file_header, tot_file_header)

        wgt.selectionCleared.connect(self.selection_cleared)
        wgt.selectionPopulated.connect(self.items_selected)
        wgt.updateView.connect(self.build_view)

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

        wgt = self.create_view_wgt(id_, std_header, tot_header)
        self.tab_wgt.add_tab(wgt, std_file.file_name)

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

    def add_new_var(self, view, variables, func):
        """ Add a new variable to the file. """
        var_nm = "Custom Variable"
        key_nm = "Custom Key"

        if all(map(lambda x: x.variable == variables[0].variable, variables)):
            var_nm = variables[0].variable

        if all(map(lambda x: x.key == variables[0].key, variables)):
            key_nm = variables[0].key

        # retrieve custom inputs from a user
        kwargs = {"variable name": var_nm,
                  "key name": key_nm}

        dialog = MulInputDialog(self, **kwargs)
        res = dialog.exec()

        if res == 0:
            return

        var_nm = dialog.get_inputs_dct()["variable name"]
        key_nm = dialog.get_inputs_dct()["key name"]

        file_id = view.get_file_id()

        # files are always returned as list
        file = self.get_files_from_db(file_id)[0]

        var_id = file.aggregate_variables(variables, func,
                                          key_name=key_nm,
                                          variable_name=var_nm,
                                          part_match=False)
        if var_id:
            # vars are always returned as list
            var = file.get_variables_by_id(var_id)[0]
            view.add_header_variable(var_id, var)
            view.set_next_update_forced()

    def on_totals_change(self, change):
        """ Switch current views to 'totals' and back. """
        View.totals = change  # update class variable to request totals
        self.build_view()

    def apply_tools_func(self, func, *args, **kwargs):
        """ A wrapper to apply functions to current views. """
        # apply function to the current widget
        view = self.current_view_wgt
        func(view, *args, **kwargs)

        # apply function to all other widgets asynchronously
        others = self.all_other_view_wgts
        if others:
            w = IterWorker(func, others, *args, **kwargs)
            self.thread_pool.start(w)

        self.build_view()

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

    def add_mean_var(self):
        """ Create a new 'mean' variable. """
        variables = self.get_current_request()
        self.apply_tools_func(self.add_new_var, variables, "mean")

    def add_summed_var(self):
        """ Create a new 'summed' variable. """
        variables = self.get_current_request()
        self.apply_tools_func(self.add_new_var, variables, "sum")

    def remove_vars(self):
        """ Remove variables from a file. """
        variables = self.get_current_request()

        if not variables:
            return

        all_ = self.all_files_requested()
        nm = self.tab_wgt.tabText(self.tab_wgt.currentIndex())

        files = "all files" if all_ else f"file '{nm}'"
        text = f"Following variables will be deleted from {files}. "

        inf_text = "\n".join([" | ".join(var) for var in variables])

        dialog = ConfirmationDialog(self, text, det_text=inf_text)
        res = dialog.exec_()

        if res == 0:
            return

        self.apply_tools_func(self.dump_vars, variables, remove=True)

    def hide_vars(self):
        """ Temporarily hide variables. """
        variables = self.get_current_request()
        self.apply_tools_func(self.dump_vars, variables)

        # allow showing variables again
        self.show_hidden_act.setEnabled(True)

    def get_current_file_ids(self):
        """ Return current file id or ids based on 'all files btn' state. """
        if self.all_files_requested():
            return [f.get_file_id() for f in self.all_view_wgts]

        return [self.current_view_wgt.get_file_id()]

    def get_current_request(self):
        """ Get a currently selected output variables information. """
        outputs = self.selected
        interval = self.get_current_interval()
        variables = None

        if outputs:
            variables = [Variable(interval, *item) for item in outputs]

        return variables

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

        # ~~~~ Outputs actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar.updateView.connect(self.build_view)
        self.toolbar.meanRequested.connect(self.add_mean_var)
        self.toolbar.sumRequested.connect(self.add_summed_var)
        self.toolbar.totalsChanged.connect(self.on_totals_change)


if __name__ == "__main__":
    sys_argv = sys.argv
    app = QApplication()
    db = QFontDatabase()
    install_fonts("../resources", db)

    db.addApplicationFont("./resources/Roboto-Regular.ttf")
    mainWindow = MainWindow()
    # availableGeometry = app.desktop().availableGeometry(mainWindow)
    # mainWindow.resize(availableGeometry.width() * 4 // 5,
    #                   availableGeometry.height() * 4 // 5)
    mainWindow.show()
    sys.exit(app.exec_())
