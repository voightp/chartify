from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QWidget, QTabWidget, QTreeView, QSplitter, QHBoxLayout, QVBoxLayout, \
    QGridLayout, \
    QToolButton, QSizePolicy, QLayout, QLabel, QGroupBox, QRadioButton, QToolBar, QMenuBar, QAction, \
    QFileDialog, \
    QDialog, QProgressBar, QFormLayout, QAbstractItemView, QSlider, QSpacerItem, QSizePolicy, \
    QLineEdit, QComboBox, \
    QMdiArea, QHeaderView, QTableView, QApplication, QScrollArea, QStatusBar, QMenu, QFrame
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, \
    QItemSelectionModel, QRegExp, QUrl, QTimer, QFile
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView, QWebEngineSettings
from PySide2.QtGui import QKeySequence, QIcon, QPixmap, QFontDatabase
from eso_file_header import EsoFileHeader
from icons import Pixmap
from progress_widget import MyStatusBar

from buttons import TitledButton, IntervalButton
from functools import partial
import traceback
import sys
import os
import ctypes
import loky

from eso_reader.constants import TS, D, H, M, A, RP
from eso_reader.eso_file import EsoFile, load_eso_file, get_results
from eso_reader.mini_classes import Variable
import eso_reader.misc_os as misc_os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from queue import Queue
from multiprocessing import Manager, cpu_count, Pipe, Process
from eso_file_widget import GuiEsoFile
from chart_widgets import MyWebView
from random import randint
from threads import PipeEcho, MonitorThread, EsoFileWatcher, GuiMonitor

HEIGHT_THRESHOLD = 650
HIDE_DISABLED = True

from pympler import asizeof


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QtWidgets.QMainWindow):
    resized = Signal()

    def __init__(self):
        super(MainWindow, self).__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setGeometry(50, 50, 800, 600)
        self.setWindowTitle("eso pie")

        # ~~~~ Main Window widgets ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.central_wgt = QWidget(self)
        self.central_layout = QHBoxLayout(self.central_wgt)
        self.setCentralWidget(self.central_wgt)
        self.central_splitter = QSplitter(self.central_wgt)
        self.central_splitter.setOrientation(Qt.Horizontal)
        self.central_layout.addWidget(self.central_splitter)

        # ~~~~ Left hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_wgt = QWidget(self.central_splitter)
        self.left_main_layout = QHBoxLayout(self.left_main_wgt)
        self.central_splitter.addWidget(self.left_main_wgt)

        # ~~~~ Left hand Tools Widget ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar_wgt = QFrame(self.left_main_wgt, objectName="toolbar")
        self.toolbar_layout = QVBoxLayout(self.toolbar_wgt)
        self.left_main_layout.addWidget(self.toolbar_wgt)

        # ~~~~ Left hand Tools Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.n_toolbar_cols = 2 if self.height() < HEIGHT_THRESHOLD else 1
        self.interval_btns = {}
        self.intervals_group = QGroupBox("Intervals", self.toolbar_wgt)
        self.set_up_interval_btns()
        self.toolbar_layout.addWidget(self.intervals_group)

        self.options_group = QGroupBox("Options", self.toolbar_wgt)
        self.all_eso_files_btn = QToolButton(self.options_group)
        self.set_up_options()
        self.toolbar_layout.addWidget(self.options_group)

        spacer = QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.toolbar_layout.addSpacerItem(spacer)

        self.settings_group = QGroupBox("Settings", self.toolbar_wgt)
        self.set_up_settings()
        self.toolbar_layout.addWidget(self.settings_group)

        # ~~~~ Left hand View widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_wgt = QFrame(self.left_main_wgt, objectName="viewWidget")
        self.view_layout = QVBoxLayout(self.view_wgt)
        self.left_main_layout.addWidget(self.view_wgt)

        # ~~~~ Left hand Tab widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt = QTabWidget(self.view_wgt)
        self.set_up_tab_wgt()
        self.view_layout.addWidget(self.tab_wgt)

        # ~~~~ Left hand Tab Tools  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt = QGroupBox(self.view_wgt, objectName="viewTools")
        self.collapse_all_btn = QToolButton(self.view_tools_wgt, objectName="smallButton")
        self.expand_all_btn = QToolButton(self.view_tools_wgt, objectName="smallButton")
        self.filter_icon = QLabel(self.view_tools_wgt)
        self.filter_line_edit = QLineEdit(self.view_tools_wgt)
        self.set_up_view_tools()
        self.view_layout.addWidget(self.view_tools_wgt)

        # ~~~~ Right hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.right_main_wgt = QWidget(self.central_splitter)
        self.right_main_layout = QHBoxLayout(self.right_main_wgt)
        self.central_splitter.addWidget(self.right_main_wgt)

        # ~~~~ Right hand Chart Area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.main_chart_widget = QWidget(self.right_main_wgt)
        self.main_chart_layout = QHBoxLayout(self.main_chart_widget)
        self.right_main_layout.addWidget(self.main_chart_widget)

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.create_ui_actions()

        # ~~~~ Eso files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.current_view_settings = {"widths": None,
                                      "order": None,
                                      "expanded": set()}

        self.current_selection = None
        self.treeAutoExpand = True
        self.allEsoFilesResults = False

        # ~~~~ Status bar ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.status_bar = MyStatusBar(self)
        self.setStatusBar(self.status_bar)

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.file_queue = Queue()
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()

        # ~~~~ Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # self.database = self.manager.dict() TODO simple dict might be sufficient
        self.database = {}

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.monitors = []
        # TODO PASSING THE DATA TO DASH APP
        self.watcher_thread = EsoFileWatcher(self.file_queue)
        self.monitor_thread = MonitorThread(self.progress_queue)
        self.pool = self.create_pool()
        self.create_thread_actions()
        self.watcher_thread.start()
        self.monitor_thread.start()

        # ~~~~ Timer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Timer to delay firing of the 'text_edited' event
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._filter_view)

        # ~~~~ Menus ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.create_menu_actions()
        self.file_menu = self.menuBar().addMenu("&File")
        # TODO reload css button (temporary)
        css = QAction("CSS", self)
        css.triggered.connect(self.toggle_css)

        no_css = QAction("NO CSS", self)
        no_css.triggered.connect(self.turn_off_css)

        mirror = QAction("Mirror", self)
        mirror.triggered.connect(self.mirror)

        memory = QAction("Memory", self)
        memory.triggered.connect(self.report_sizes)  # TODO REMOVE THIS
        self.memory_menu = self.menuBar().addAction(memory)  # TODO REMOVE THIS

        self.show_menu = self.menuBar().addAction(css)
        self.help_menu = self.menuBar().addAction(no_css)
        self.mirror_menu = self.menuBar().addAction(mirror)
        self.file_menu.addAction(self.loadEsoFileAct)
        self.file_menu.addAction(self.loadFilesFromFolderAct)
        self.file_menu.addAction(self.closeAllTabsAct)

        self.chart_area = QWebEngineView(self)
        self.chart_area.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard,
                                                True)
        self.main_chart_layout.addWidget(self.chart_area)
        # self.chart_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chart_area.setAcceptDrops(True)

        self.url = "http://127.0.0.1:8080/"
        self.chart_area.load(self.url)

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.load_icons()
        self.set_up_base_ui()
        self.toggle_css()

    @property
    def current_eso_file(self):
        """ A currently selected eso file. """
        return self.tab_wgt.currentWidget()

    @property
    def all_eso_files(self):
        """ A list of all loaded eso files. """
        tab_widget = self.tab_wgt
        count = tab_widget.count()
        widgets = [tab_widget.widget(i) for i in range(count)]
        return widgets

    def default_settings(self):
        pass

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
        print("Monitor thread", asizeof.asizeof(self.monitor_thread))
        print("Watcher thread", asizeof.asizeof(self.watcher_thread))

    def mirror(self):
        """ Mirror the layout. """
        self.central_splitter.insertWidget(0, self.central_splitter.widget(1))

    def turn_off_css(self):
        """ Turn the CSS on and off. """
        self.setStyleSheet("")

    def toggle_css(self):
        """ Turn the CSS on and off. """
        with open("styles/app_style.css", "r") as file:
            cont = file.read()

        self.setStyleSheet(cont)

    def closeEvent(self, event):
        """ Shutdown all the background stuff. """
        self.watcher_thread.terminate()
        self.monitor_thread.terminate()
        self.manager.shutdown()

    def resizeEvent(self, event):
        """ Handle window behaviour when on resize. """
        self.resized.emit()
        return super().resizeEvent(event)

    def clear_current_selection(self):
        print("Current selection cleared!")
        self.current_selection = None

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:
            if not self.tab_widget_empty():
                self.current_eso_file.clear_selection()

            self.clear_current_selection()

        elif event.key() == Qt.Key_Delete:
            pass

    def tab_widget_empty(self):
        """ Check if there's at least one loaded file. """
        return self.tab_wgt.count() <= 0

    def all_eso_files_requested(self):
        """ Check if results from all eso files are requested. """
        btn = self.all_eso_files_btn
        return btn.isChecked() and btn.isEnabled()

    def selected_intervals(self):
        """ Get currently selected interval buttons. """
        btns = self.interval_btns
        return [k for k, btn in btns.items() if btn.isChecked()]

    def current_trace_type(self):
        """ Get currently selected trace type. """
        btns = self.trace_buttons.items()
        return next(name for name, btn in btns if btn.isChecked())

    def set_up_base_ui(self):
        """ Set up appearance of main widgets. """
        self.central_layout.setSpacing(0)
        self.central_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Main left side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        left_side_size_policy = QtWidgets.QSizePolicy()
        left_side_size_policy.setHorizontalStretch(0)
        self.left_main_wgt.setSizePolicy(left_side_size_policy)
        self.left_main_layout.setSpacing(0)
        self.left_main_layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar_wgt.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar_layout.setSpacing(0)
        self.toolbar_layout.setAlignment(Qt.AlignTop)

        self.intervals_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.settings_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.tab_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.tab_wgt.setMinimumWidth(400)
        self.tab_wgt.setTabPosition(QTabWidget.North)

        self.view_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.setSpacing(0)

        self.view_tools_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # ~~~~ Main right side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        right_side_size_policy = QtWidgets.QSizePolicy()
        right_side_size_policy.setHorizontalStretch(1)
        self.right_main_wgt.setSizePolicy(right_side_size_policy)
        self.right_main_layout.setSpacing(0)
        self.right_main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_chart_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.main_chart_widget.setMinimumWidth(400)

    def load_icons(self):
        myappid = 'foo'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)  # this sets toolbar icon on win 7

        self.setWindowIcon(QPixmap("./icons/twotone_pie_chart.png"))
        self.filter_icon.setPixmap(Pixmap("./icons/filter_list.png", r=255, g=255, b=255))
        self.expand_all_btn.setIcon(Pixmap("./icons/unfold_more.png"))
        self.collapse_all_btn.setIcon(Pixmap("./icons/unfold_less.png"))

    def set_up_tab_wgt(self):
        """ Set up appearance and behaviour of the tab widget. """
        # ~~~~ Tab widget set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.setUsesScrollButtons(True)
        self.tab_wgt.setTabsClosable(True)
        self.tab_wgt.setMovable(True)

    def set_initial_layout(self):
        """ Define an app layout when there isn't any file loaded. """
        self.disable_interval_btns()
        self.all_eso_files_btn.setEnabled(False)
        self.populate_intervals_group()
        self.populate_options_group()
        self.populate_settings_group()

    def hide_disabled(self, wgts):
        """ Hide disabled widgets from the interface. """
        enabled, disabled = self.filter_disabled(wgts)
        self.hide_widgets(disabled)

        return enabled

    @staticmethod
    def filter_disabled(wgts):
        """Take a list and split it to 'enabled', 'disabled' sub-lists. """
        enabled = []
        disabled = []

        for wgt in wgts:
            if wgt.isEnabled():
                enabled.append(wgt)
            else:
                disabled.append(wgt)

        return enabled, disabled

    @staticmethod
    def hide_widgets(wgts):
        """ Hide given widgets. """
        for wgt in wgts:
            wgt.hide()

    @staticmethod
    def show_widgets(wgts):
        """ Display given widgets. """
        for wgt in wgts:
            wgt.show()

    @staticmethod
    def remove_children(layout):
        """ Remove all children of the interface. """
        for _ in range(layout.count()):
            wgt = layout.itemAt(0).widget()
            layout.removeWidget(wgt)

    @staticmethod
    def populate_grid_layout(layout, wgts, n_cols):
        """ Place given widgets on a specified layout with 'n' columns. """
        # render only enabled buttons
        n_rows = (len(wgts) if len(wgts) % 2 == 0 else len(wgts) + 1) // n_cols
        ixs = [(x, y) for x in range(n_rows) for y in range(n_cols)]

        for btn, ix in zip(wgts, ixs):
            layout.addWidget(btn, *ix)

        if layout.count() == 0:
            layout.parentWidget().hide()

        else:
            layout.parentWidget().show()

    def populate_intervals_group(self):
        """ Populate interval buttons based on a current state. """
        layout = self.intervals_group.layout()
        interval_btns = [btn for btn in self.interval_btns.values()]
        n_cols = self.n_toolbar_cols

        self.remove_children(layout)

        if HIDE_DISABLED:
            interval_btns = self.hide_disabled(interval_btns)
            self.show_widgets(interval_btns)

        self.populate_grid_layout(layout, interval_btns, n_cols)

    def populate_settings_group(self):
        """ Populate settings group layout. """
        layout = self.settings_group.layout()
        n_cols = self.n_toolbar_cols

        settings_btns = [self.energy_units_btn,
                         self.power_units_btn,
                         self.units_system_btn,
                         self.group_by_btn]

        self.populate_grid_layout(layout, settings_btns, n_cols)

    def populate_options_group(self):
        """ Populate options group layout. """
        layout = self.options_group.layout()
        options_btns = [self.all_eso_files_btn]

        self.remove_children(layout)

        if HIDE_DISABLED:
            options_btns = self.hide_disabled(options_btns)
            self.show_widgets(options_btns)

        self.populate_grid_layout(layout,
                                  options_btns,
                                  self.n_toolbar_cols)

    def set_up_interval_btns(self):
        """ Create interval buttons and a parent container. """
        # ~~~~ Layout to hold interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        interval_btns_layout = QGridLayout(self.intervals_group)
        interval_btns_layout.setSpacing(0)
        interval_btns_layout.setContentsMargins(0, 0, 0, 0)
        interval_btns_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Generate interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ids = {TS: "Timestep", H: "Hourly", D: "Daily", M: "Monthly", A: "Annual", RP: "Runperiod"}
        p = self.intervals_group
        self.interval_btns = {k: IntervalButton(v, parent=p) for k, v in ids.items()}
        self.populate_intervals_group()

    def set_up_options(self):
        """ Create all files button. """
        # ~~~~ Layout to hold options  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        options_layout = QGridLayout(self.options_group)
        options_layout.setSpacing(0)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Generate include / exclude all files button ~~~~~~~~~~~~~~~~~
        self.all_eso_files_btn.setEnabled(False)
        self.all_eso_files_btn.setText("All")
        self.all_eso_files_btn.setCheckable(True)

        self.populate_options_group()

    def set_up_settings(self):
        """ Create Settings menus and buttons. """
        # ~~~~ Layout to hold units settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        settings_layout = QGridLayout(self.settings_group)
        settings_layout.setSpacing(0)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        energy_units_menu = QMenu(self)
        items = ["Wh", "kWh", "MWh", "J", "kJ", "GJ", "Btu", "kBtu", "MBtu"]
        self.energy_units_btn = TitledButton(self.settings_group, fill_space=True,
                                             title="energy", menu=energy_units_menu,
                                             items=items, data=items, def_act_ix=1)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        power_units_menu = QMenu(self)
        items = ["W", "kW", "MW", "Btu/h", "kBtu/h", "MBtu/h"]
        self.power_units_btn = TitledButton(self.settings_group, fill_space=True,
                                            title="power", menu=power_units_menu,
                                            items=items, data=items, def_act_ix=3)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_system_menu = QMenu(self)
        items = ["SI", "IP"]
        self.units_system_btn = TitledButton(self.settings_group, fill_space=True,
                                             title="system", menu=units_system_menu,
                                             items=items, data=items, def_act_ix=0)

        # ~~~~ Sorting set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        group_by = QMenu(self)
        items = ["-", "Key", "Variable", "Units"]
        data = ["raw", "key", "variable", "units"]
        self.group_by_btn = TitledButton(self.settings_group, fill_space=True,
                                         title="group by", menu=group_by,
                                         items=items, data=data, def_act_ix=2)

        self.populate_settings_group()

    def set_up_view_tools(self):
        """ Create tools, settings and search line for the view. """
        # ~~~~ Widget to hold tree view tools ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        view_tools_layout = QHBoxLayout(self.view_tools_wgt)
        view_tools_layout.setSpacing(0)
        view_tools_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Widget to hold tree view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btnWidget = QWidget(self.view_tools_wgt)
        btnLayout = QHBoxLayout(btnWidget)
        btnLayout.setSpacing(0)
        btnLayout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Add view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btnLayout.addWidget(self.collapse_all_btn)
        btnLayout.addWidget(self.expand_all_btn)

        # ~~~~ Create tree search line edit ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.setPlaceholderText("filter...")
        self.filter_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.filter_line_edit.setFixedWidth(160)

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # ~~~~ Add child widgets to treeTools layout ~~~~~~~~~~~~~~~~~~~~~~~~
        view_tools_layout.addWidget(self.filter_icon)
        view_tools_layout.addWidget(self.filter_line_edit)
        view_tools_layout.addItem(spacer)
        view_tools_layout.addWidget(btnWidget)

    def get_group_by_key(self):
        """ Get current view arrange key from the interface. """
        return self.group_by_btn.defaultAction().data()

    def handle_col_ex_btns(self, group_by_key):
        """ Enable / disable 'collapse all' / 'expand all' buttons. """
        if group_by_key == "raw":
            self.collapse_all_btn.setEnabled(False)
            self.expand_all_btn.setEnabled(False)

        else:
            self.collapse_all_btn.setEnabled(True)
            self.expand_all_btn.setEnabled(True)

    def update_view(self, is_fresh=False):
        """ Create a new model when the tab or the interval has changed. """
        # do not update when there isn't any file available
        if self.tab_widget_empty():
            return

        # retrieve required inputs from the interface
        group_by_key = self.get_group_by_key()
        intervals = self.selected_intervals()
        current_eso_file_widget = self.current_eso_file
        current_selection = self.current_selection
        current_view_settings = self.current_view_settings

        # update the current widget
        current_eso_file_widget.update_view_model(group_by_key,
                                                  intervals,
                                                  current_view_settings,
                                                  is_fresh=is_fresh,
                                                  current_selection=current_selection)
        # check if some filtering is applied,
        # if yes, update the model accordingly
        if self.filter_line_edit.text():
            self._filter_view()

        # based on the current view, enable or disable tree buttons
        # collapse and expand all buttons are not relevant for plain view
        self.handle_col_ex_btns(group_by_key)

    def update_layout(self):
        """ Update window layout accordingly to window size. """
        new_cols = 2 if self.height() < HEIGHT_THRESHOLD else 1
        if new_cols != self.n_toolbar_cols:
            self.n_toolbar_cols = new_cols
            self.populate_intervals_group()
            self.populate_options_group()
            self.populate_settings_group()

    def interval_changed(self):
        """ Update view when an interval is changed. """
        self.update_view()

    def get_units_system(self):
        """ Get currently set units system. """
        return self.units_system_btn.defaultAction().data()

    def get_power_units(self):
        """ Get currently set power units. """
        return self.power_units_btn.defaultAction().data()

    def get_energy_units(self):
        """ Get currently set energy units. """
        return self.energy_units_btn.defaultAction().data()

    def _update_btn_menu(self, act, btn):
        """ Handle changing actions on a 'Titled' button. """
        current_act = btn.defaultAction()
        changed = current_act != act

        if changed:
            current_act.setChecked(False)
            btn.setDefaultAction(act)
            self.update_view()

        else:
            current_act.setChecked(True)

    def units_system_changed(self, act):
        """ Update view when energy units are changed. """
        btn = self.units_system_btn
        self._update_btn_menu(act, btn)

    def power_units_changed(self, act):
        """ Update view when energy units are changed. """
        btn = self.power_units_btn
        self._update_btn_menu(act, btn)

    def energy_units_changed(self, act):
        """ Update view when energy units are changed. """
        btn = self.energy_units_btn
        self._update_btn_menu(act, btn)

    def view_key_changed(self, act):
        """ Update view when view type is changed. """
        btn = self.group_by_btn
        self._update_btn_menu(act, btn)

        # ~~~~ Disable expand / collapse all buttons ~~~~~~~~~~~~~~~~~~~~~~~~
        key = act.data()
        self.handle_col_ex_btns(key)

    def expand_all(self):
        """ Expand all tree view items. """
        if self.current_eso_file:
            self.current_eso_file.expand_all()

    def collapse_all(self):
        """ Collapse all tree view items. """
        if self.current_eso_file:
            self.current_eso_file.collapse_all()

    def _filter_view(self):
        """ Apply a filter when the filter text is edited. """
        filter_string = self.filter_line_edit.text()
        print("Filtering: {}".format(filter_string))
        if not self.tab_widget_empty():
            self.current_eso_file.filter_view(filter_string)

    def text_edited(self):
        """ Delay firing a text edited event. """
        self.timer.start(200)

    def remove_eso_file(self, index):
        """ Delete current eso file. """
        self.delete_eso_file_content(index)

        if self.tab_wgt.count() <= 1:
            # only one file is available
            self.all_eso_files_btn.setEnabled(False)
            self.populate_options_group()

    def disable_interval_btns(self):
        """ Disable all interval buttons. """
        for btn in self.interval_btns.values():
            btn.setEnabled(False)

    def delete_file_from_db(self, file_id):
        """ Delete the eso file from the database. """
        try:
            print("Deleting file: '{}' from database.".format(self.database[file_id].file_path))
            del self.database[file_id]

        except KeyError:
            print("Cannot delete the eso file: id '{}',\n"
                  "File was not found in database.".format(file_id))

    def delete_eso_file_content(self, tab_index):
        """ Delete the content of the file with given index. """
        widget = self.tab_wgt.widget(tab_index)
        file_id = widget.file_id

        # delete the eso file from database
        self.delete_file_from_db(file_id)

        # delete the widget and remove the tab
        widget.deleteLater()
        self.tab_wgt.removeTab(tab_index)

    def _available_intervals(self):
        """ Get available intervals for the current eso file. """
        eso_file = self.current_eso_file.eso_file_header
        return eso_file.available_intervals

    def _selected_intervals(self):
        """ Get currently selected interval buttons. """
        btns = self.interval_btns
        intervals = [intvl for intvl, btn in btns.items() if btn.isChecked()]
        return intervals

    def update_interval_buttons_state(self):
        """ Deactivate interval buttons if they are not applicable. """
        available_intervals = self._available_intervals()
        selected_intervals = self._selected_intervals()
        all_btns_dct = self.interval_btns

        for key, btn in all_btns_dct.items():
            if key in available_intervals:
                btn.setEnabled(True)
            else:
                # interval is not applicable for current eso file
                btn.setEnabled(False)
                btn.setChecked(False)

        # when there isn't any previously selected interval applicable,
        # the first available button is selected
        if all(map(lambda x: x not in available_intervals, selected_intervals)):
            btn = next(btn for btn in all_btns_dct.values() if btn.isEnabled())
            btn.setChecked(True)

    def tab_changed(self, index):
        """ Update view when tabChanged event is fired. """
        print("Tab changed {}".format(index))
        if not self.tab_widget_empty():
            self.update_view(is_fresh=True)
            self.update_interval_buttons_state()
            self.populate_intervals_group()

        else:
            # there aren't any widgets available
            self.set_initial_layout()

    def create_ui_actions(self):
        """ Create actions which depend on user actions """
        # ~~~~ Resize window ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.resized.connect(self.update_layout)

        # ~~~~ Interval buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        _ = [btn.clicked.connect(self.interval_changed) for btn in self.interval_btns.values()]

        # ~~~~ Tree View Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.group_by_btn.menu().triggered.connect(self.view_key_changed)
        self.energy_units_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_units_btn.menu().triggered.connect(self.power_units_changed)
        self.units_system_btn.menu().triggered.connect(self.units_system_changed)
        self.expand_all_btn.clicked.connect(self.expand_all)
        self.collapse_all_btn.clicked.connect(self.collapse_all)

        # ~~~~ Filter action ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.textEdited.connect(self.text_edited)

        # ~~~~ Tab actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.tabCloseRequested.connect(self.remove_eso_file)
        self.tab_wgt.currentChanged.connect(self.tab_changed)

    def update_sort_order(self, new_index, new_order):
        """ Store current column vertical sorting. """
        self.current_view_settings["order"] = (new_index, new_order)

    def update_section_widths(self, new_widths_dct):
        """ Store current column widths. """
        self.current_view_settings["widths"] = new_widths_dct

    def clear_expanded_set(self):
        """ Clear previously stored expanded items set. """
        self.current_view_settings["expanded"].clear()

    def update_expanded_set(self, new_expanded_item, remove=False):
        """ Handle populating and removing items from 'expanded' set. """
        expanded_set = self.current_view_settings["expanded"]

        if not remove:
            # the method is used for populating the set
            expanded_set.add(new_expanded_item)

        else:
            expanded_set.remove(new_expanded_item)

    def start_loading_file(self, monitor_id, monitor_name):
        """ Add a progress bar on the interface. """
        self.status_bar.start_loading(monitor_id, monitor_name)

    def update_progress_text(self, monitor_id, text):
        """ Update text info for a given monitor. """
        pass
        # self.status_bar.progressBars[monitor_id].setText(text)

    def set_progress_bar_max(self, monitor_id, max_value):
        """ Set maximum progress value for a given monitor. """
        self.status_bar.set_max_value(monitor_id, max_value)

    def update_bar_progress(self, monitor_id, value):
        """ Update progress value for a given monitor. """
        self.status_bar.update_progress(monitor_id, value)

    def _delete_monitor(self, monitor_id):
        monitors = self.monitors
        mon = next(monitor for monitor in monitors if monitor.id == monitor_id)
        monitors.remove(mon)

    def file_loaded(self, monitor_id):
        """ Remove a progress bar when the file is loaded. """
        self.status_bar.file_loaded(monitor_id)
        self._delete_monitor(monitor_id)

    @staticmethod
    def create_pool():
        """ Create a new proccess pool. """
        n_cores = cpu_count()
        workers = (n_cores - 1) if n_cores > 1 else 1
        return loky.get_reusable_executor(max_workers=workers)

    def current_eso_file_id(self):
        """ Return an id of the currently selected file. """
        current_file = self.current_eso_file
        return current_file.file_id

    def all_files_ids(self):
        """ Return ids of all loaded eso files. """
        files = self.all_eso_files
        ids = [file.file_id for file in files]
        return ids

    def add_file_to_db(self, file_id, eso_file):
        """ Add processed eso file to the database. """
        try:
            print("Adding file: '{}', id '{}' into database.".format(eso_file.file_name, file_id))
            self.database[file_id] = eso_file

        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")

    def add_eso_file(self, eso_file):
        """ Add eso file into 'tab' widget. """
        all_ids = self.all_files_ids()
        file_id = self.generate_id(all_ids)

        # add the file on the ui
        header_dct = eso_file.header_dct
        eso_file_header = EsoFileHeader(header_dct)
        eso_file_widget = GuiEsoFile(self, eso_file_header, file_id)
        self.tab_wgt.addTab(eso_file_widget, eso_file.file_name)

        # add the file into database
        self.add_file_to_db(file_id, eso_file)

        # enable all eso file results btn if it's suitable
        if self.tab_wgt.count() > 1:
            self.all_eso_files_btn.setEnabled(True)
            self.populate_options_group()

    def get_files_ids(self):
        """ Return current file id or ids for all files based on 'all files btn' state. """
        if self.all_eso_files_requested():
            return self.all_files_ids()

        file_id = self.current_eso_file_id()
        return [file_id]

    def current_request(self):
        """ Get a currently selected output variables information. """
        outputs = self.current_selection
        ids = self.get_files_ids()
        variables = None

        # add an interval information into the request
        # create 'request items' using 'Variable' namedtuple
        if outputs:
            variables = self.generate_variables(outputs)

        return ids, variables

    def generate_variables(self, outputs):
        """ Create an output request using required 'Variable' class. """
        request_lst = []
        for interval in self.selected_intervals():
            for item in outputs:
                req = Variable(interval, *item)
                request_lst.append(req)
        return request_lst

    def create_thread_actions(self):
        """ Create actions related to background threads. """
        self.watcher_thread.loaded.connect(self.add_eso_file)
        self.monitor_thread.initialized.connect(self.start_loading_file)
        self.monitor_thread.started.connect(self.update_progress_text)
        self.monitor_thread.progress_text_updated.connect(self.update_progress_text)
        self.monitor_thread.progress_bar_updated.connect(self.update_bar_progress)
        self.monitor_thread.preprocess_finished.connect(self.set_progress_bar_max)
        self.monitor_thread.finished.connect(self.file_loaded)

    def populate_current_selection(self, outputs):
        """ Store current selection in main app. """
        self.current_selection = outputs

    def singleFileResults(self, requestList):
        return get_results(self.currentEsoFileWidget.esoFile, requestList)

    def multipleFileResults(self, requestList):
        esoFiles = [esoFileWidget.esoFile for esoFileWidget in
                    self.esoFileWidgets]
        esoFiles.sort(key=lambda x: x.file_name)
        return get_results(esoFiles, requestList)

    def wait_for_results(self, monitor, queue, future):
        """ Put loaded file into the queue and clean up the pool. """
        try:
            eso_file = future.result()
            if eso_file:
                queue.put(eso_file)
            else:
                monitor.processing_failed("Processing failed!")

        except BrokenPipeError:
            print("The application is being closed - catching broken pipe.")

        except Exception as e:
            monitor.processing_failed("Processing failed!")
            traceback.print_exc()

    @staticmethod
    def generate_id(ids_lst, max_id=99999):
        """ Create a unique id. """
        while True:
            id = randint(1, max_id)
            if id not in ids_lst:
                return id

    def _load_eso_file(self, eso_file_paths):
        """ Start eso file processing. """
        monitor_ids = [monitor.id for monitor in self.monitors]
        queue = self.progress_queue
        file_queue = self.file_queue
        for path in eso_file_paths:
            # create a monitor to report progress on the ui
            monitor_id = self.generate_id(monitor_ids)
            monitor = GuiMonitor(path, monitor_id, queue)
            self.monitors.append(monitor)

            # create a new process to load eso file
            future = self.pool.submit(load_eso_file, path, monitor=monitor)
            future.add_done_callback(partial(self.wait_for_results, monitor, file_queue))

    def load_files(self):
        file_pths, _ = QFileDialog.getOpenFileNames(self, "Load Eso File", "", "*.eso")
        if file_pths:
            self._load_eso_file(file_pths)

    def open_folder(self):
        dirPath = QFileDialog.getExistingDirectory(self, "Open folder (includes subfolders).")
        if dirPath:
            paths = misc_os.list_files(dirPath, 3, ext="eso")
            self._load_eso_file(paths)

    # noinspection PyAttributeOutsideInit
    def create_menu_actions(self):
        """ Create top toolbar menu actions. """
        # ~~~~ Menu actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.loadEsoFileAct = QAction("&Load Eso Files", self)
        self.loadEsoFileAct.setShortcut(QKeySequence("Ctrl+L"))
        self.loadEsoFileAct.triggered.connect(self.load_files)
        self.loadEsoFileAct.setStatusTip("Select Eso file to load")

        self.loadFilesFromFolderAct = QAction("&Load Eso Files from folder", self)
        self.loadFilesFromFolderAct.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self.loadFilesFromFolderAct.triggered.connect(self.open_folder)
        self.loadFilesFromFolderAct.setStatusTip("Select folder to load eso files.")

        self.closeAllTabsAct = QAction("Close all eso files.", self)
        self.closeAllTabsAct.setShortcut(QKeySequence("Ctrl+Alt+C"))
        self.closeAllTabsAct.triggered.connect(self.close_all_tabs)
        self.closeAllTabsAct.setStatusTip("Close all open tabs.")

    def close_all_tabs(self):
        """ Delete all the content. """
        for _ in range(self.tab_wgt.count()):
            self.delete_eso_file_content(0)

        self.set_initial_layout()


def install_fonts(pth, db):
    files = os.listdir(pth)
    for file in files:
        p = os.path.join(pth, file)
        db.addApplicationFont(p)


if __name__ == "__main__":
    sys_argv = sys.argv
    app = QApplication()
    db = QFontDatabase()
    install_fonts("./resources", db)

    db.addApplicationFont("./resources/Roboto-Regular.ttf")
    mainWindow = MainWindow()
    # availableGeometry = app.desktop().availableGeometry(mainWindow)
    # mainWindow.resize(availableGeometry.width() * 4 // 5,
    #                   availableGeometry.height() * 4 // 5)
    mainWindow.show()
    sys.exit(app.exec_())
