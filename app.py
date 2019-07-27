from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QWidget, QTabWidget, QTreeView, QSplitter, QHBoxLayout, QVBoxLayout, \
    QGridLayout, \
    QToolButton, QSizePolicy, QLayout, QLabel, QGroupBox, QRadioButton, QToolBar, QMenuBar, QAction, \
    QFileDialog, \
    QDialog, QProgressBar, QFormLayout, QAbstractItemView, QSlider, QSpacerItem, QSizePolicy, \
    QLineEdit, QComboBox, \
    QMdiArea, QHeaderView, QTableView, QApplication, QScrollArea, QStatusBar, QMenu, QFrame, QTextEdit, QPushButton
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, \
    QItemSelectionModel, QRegExp, QUrl, QTimer, QFile
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView, QWebEngineSettings
from PySide2.QtGui import QKeySequence, QIcon, QPixmap, QFontDatabase, QFont, QColor
from eso_file_header import FileHeader
from icons import Pixmap, text_to_pixmap
from progress_widget import StatusBar, ProgressContainer
from widgets import LineEdit, DropFrame, TabWidget

from buttons import TitledButton, IntervalButton, ToggleButton, MenuButton
from functools import partial
import traceback
import sys
import os
import ctypes
import loky
import psutil

from eso_reader.constants import TS, D, H, M, A, RP
from eso_reader.eso_file import EsoFile, get_results, IncompleteFile
from eso_reader.building_eso_file import BuildingEsoFile
from eso_reader.mini_classes import Variable
import eso_reader.misc_os as misc_os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from queue import Queue
from multiprocessing import Manager, cpu_count, Pipe, Process
from view_widget import View
from chart_widgets import MyWebView
from random import randint
from threads import PipeEcho, MonitorThread, EsoFileWatcher, GuiMonitor

HEIGHT_THRESHOLD = 650

DEFAULTS = {
    "units_system": "SI",
    "energy_units": "kWh",
    "power_units": "kW",
    "tree_view": True,
}

si_energy_units = ["Wh", "kWh", "MWh", "J", "MJ", "GJ"]
si_power_units = ["W", "kW", "MW"]

ip_energy_units = ["Btu", "kBtu", "MBtu"]
ip_power_units = ["Btu/h", "kBtu/h", "MBtu/h", "W"]


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QtWidgets.QMainWindow):
    resized = Signal()
    background_color = {"r": 255, "g": 255, "b": 255}
    primary_color = {"r": 112, "g": 112, "b": 112}
    secondary_color = {"r": 112, "g": 112, "b": 112}

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
        self.left_main_wgt = DropFrame(self.central_splitter)
        self.left_main_wgt.setObjectName("leftMainWgt")
        self.left_main_layout = QHBoxLayout(self.left_main_wgt)
        self.central_splitter.addWidget(self.left_main_wgt)

        # ~~~~ Left hand Tools Widget ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.toolbar_wgt = QFrame(self.left_main_wgt)
        self.toolbar_wgt.setObjectName("toolbar")
        self.toolbar_layout = QVBoxLayout(self.toolbar_wgt)
        self.left_main_layout.addWidget(self.toolbar_wgt)

        # ~~~~ Left hand Tools Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.interval_btns = {}
        self.intervals_group = QGroupBox("Intervals", self.toolbar_wgt)
        self.intervals_group.setObjectName("intervalsGroup")
        self.set_up_interval_btns()
        self.toolbar_layout.addWidget(self.intervals_group)

        self.outputs_group = QGroupBox("Outputs", self.toolbar_wgt)
        self.outputs_group.setObjectName("outputsGroup")
        self.building_totals_btn = QToolButton(self.toolbar_wgt)
        self.all_eso_files_btn = QToolButton(self.toolbar_wgt)
        self.set_up_outputs_btns()
        self.toolbar_layout.addWidget(self.outputs_group)

        self.tools_group = QGroupBox("Tools", self.toolbar_wgt)
        self.tools_group.setObjectName("toolsGroup")
        self.export_xlsx_btn = QToolButton(self.tools_group)
        self.set_up_tools()
        self.toolbar_layout.addWidget(self.tools_group)

        self.custom_units_toggle = ToggleButton(self.toolbar_wgt)
        self.custom_units_toggle.setText("Units")
        self.custom_units_toggle.setChecked(True)
        self.toolbar_layout.addWidget(self.custom_units_toggle)

        self.units_group = QFrame(self.toolbar_wgt)
        self.units_group.setObjectName("unitsGroup")
        self.energy_units_btn = None
        self.power_units_btn = None
        self.units_system_btn = None
        self.rate_to_energy_btn = None
        self.set_up_units()
        self.toolbar_layout.addWidget(self.units_group)

        spacer = QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.toolbar_layout.addSpacerItem(spacer)

        self.settings_btn = MenuButton(Pixmap("icons/gear_black.png", **self.primary_color), "Settings",
                                       self.toolbar_wgt)
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setIconSize(QSize(40, 40))
        self.toolbar_layout.addWidget(self.settings_btn)

        # ~~~~ Left hand View widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_wgt = QFrame(self.left_main_wgt)
        self.view_wgt.setObjectName("viewWidget")
        self.view_layout = QVBoxLayout(self.view_wgt)
        self.left_main_layout.addWidget(self.view_wgt)

        # ~~~~ Left hand Tab widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt = TabWidget(self.view_wgt)
        self.view_layout.addWidget(self.tab_wgt)

        # ~~~~ Left hand Tab Tools  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt = QFrame(self.view_wgt)
        self.view_tools_wgt.setObjectName("viewTools")

        self.tree_view_btn = QToolButton(self.view_tools_wgt)
        self.tree_view_btn.setObjectName("treeButton")

        self.collapse_all_btn = QToolButton(self.view_tools_wgt)
        self.collapse_all_btn.setObjectName("collapseButton")

        self.expand_all_btn = QToolButton(self.view_tools_wgt)
        self.expand_all_btn.setObjectName("expandButton")

        self.filter_icon = QLabel(self.view_tools_wgt)
        self.filter_icon.setPixmap(QPixmap("./icons/filter_list_white.png"))
        self.filter_line_edit = LineEdit(self.view_tools_wgt)

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

        # ~~~~ Intermediate settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.stored_view_settings = {"widths": {"interactive": 200,
                                                "fixed": 70},
                                     "order": ("variable", Qt.AscendingOrder),
                                     "header": ("variable", "key", "units"),
                                     "expanded": set()}

        self._units_settings = {"units_system": "",
                                "power_units": "",
                                "energy_units": "",
                                "rate_to_energy": False}

        self.selected = None

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.file_queue = Queue()
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()

        # ~~~~ Status bar ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)

        self.progress_container = ProgressContainer(self.status_bar, self.progress_queue)
        self.status_bar.addWidget(self.progress_container)

        self.swap_btn = QToolButton(self)
        self.swap_btn.clicked.connect(self.mirror)
        self.swap_btn.setObjectName("swapButton")
        self.swap_btn.setIcon(Pixmap("./icons/swap_black.png", **self.primary_color))
        self.status_bar.addPermanentWidget(self.swap_btn)

        # ~~~~ Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # self.database = self.manager.dict() TODO simple dict might be sufficient
        self.database = {}

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TODO PASSING THE DATA TO DASH APP
        self.watcher_thread = EsoFileWatcher(self.file_queue)
        self.watcher_thread.loaded.connect(self.on_file_loaded)

        self.pool = create_pool()
        self.watcher_thread.start()

        # ~~~~ Timer ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Timer to delay firing of the 'text_edited' event
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._filter_view)

        # ~~~~ Menus ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.mini_menu = QWidget(self.toolbar_wgt)
        self.mini_menu_layout = QHBoxLayout(self.mini_menu)
        self.mini_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.mini_menu_layout.setSpacing(0)
        self.toolbar_layout.insertWidget(0, self.mini_menu)

        load_file_act = QAction(QIcon("./icons/add_file_grey.png"), "Load file | files", self)
        load_file_act.triggered.connect(self.load_files)
        close_all_act = QAction(QIcon("./icons/remove_grey.png"), "Close all files", self)
        close_all_act.triggered.connect(self.close_all_tabs)
        file_menu = QMenu(self)
        file_menu.addActions([load_file_act, close_all_act])

        icon_size = QSize(25, 25)
        load_file_btn = MenuButton(QIcon("icons/file_grey.png"), "Load file | files", self)
        load_file_btn.setIconSize(icon_size)
        load_file_btn.clicked.connect(self.load_files)
        load_file_btn.setStatusTip("Open eso file or files")
        load_file_btn.setMenu(file_menu)
        self.mini_menu_layout.addWidget(load_file_btn)

        save_all = MenuButton(QIcon("icons/save_grey.png"), "Save", self)
        save_all.setIconSize(icon_size)
        save_all.clicked.connect(lambda: print("NEEDS FUNCTION TO SAVE"))
        save_all.setStatusTip("Save current project")
        self.mini_menu_layout.addWidget(save_all)

        about = MenuButton(QIcon("icons/help_grey.png"), "Save", self)
        about.setIconSize(icon_size)
        about.clicked.connect(lambda: print("NEEDS FUNCTION TO SAVE"))
        about.setStatusTip("About")
        self.mini_menu_layout.addWidget(about)

        # TODO reload css button (temporary)
        mn = QMenu(self)
        self.settings_btn.setMenu(mn)

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
        self.chart_area.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard,
                                                True)
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
    def current_eso_file(self):
        """ A currently selected eso file. """
        return self.tab_wgt.get_current_widget()

    @property
    def all_eso_files(self):
        """ A list of all loaded eso files. """
        return self.tab_wgt.get_all_widgets()

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
        print("Monitor thread", asizeof.asizeof(self.progress_container.monitor_thread))
        print("Watcher thread", asizeof.asizeof(self.watcher_thread))

    def load_dummy(self):
        """ Load a dummy file. """
        self._load_eso_files(["tests/eplusout.eso"])

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
        self.progress_container.monitor_thread.terminate()
        self.manager.shutdown()

        kill_child_processes(os.getpid())

    def resizeEvent(self, event):
        """ Handle window behaviour when on resize. """
        self.resized.emit()
        return super(MainWindow, self).resizeEvent(event)

    def populate_current_selection(self, outputs):
        """ Store current selection in main app. """
        self.selected = outputs

        # enable export xlsx function TODO
        self.export_xlsx_btn.setEnabled(True)

    def clear_current_selection(self):
        """ Handle behaviour when no variables are selected. """
        self.selected = None

        # disable export xlsx as there are no
        # variables to be exported TODO
        self.export_xlsx_btn.setEnabled(False)

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:

            if not self.tab_wgt.is_empty():
                self.current_eso_file.clear_selection()

            self.clear_current_selection()

        elif event.key() == Qt.Key_Delete:
            return

    def all_eso_files_requested(self):
        """ Check if results from all eso files are requested. """
        btn = self.all_eso_files_btn
        return btn.isChecked() and btn.isEnabled()

    def get_selected_interval(self):
        """ Get currently selected interval buttons. """
        btns = self.interval_btns
        try:
            return next(k for k, btn in btns.items() if btn.isChecked())
        except StopIteration:
            pass

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

        self.tab_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.tab_wgt.setMinimumWidth(400)

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

    def set_initial_layout(self):
        """ Define an app layout when there isn't any file loaded. """
        self.all_eso_files_btn.setEnabled(False)
        self.building_totals_btn.setEnabled(False)

        self.disable_interval_btns()
        self.populate_intervals_group(hide_disabled=False)
        self.populate_units_group()
        self.populate_outputs_group()
        self.populate_tools_group()

    def hide_disabled(self, wgts):
        """ Hide disabled widgets from the interface. """
        enabled, disabled = self.filter_disabled(wgts)

        for wgt in disabled:
            wgt.hide()

        return enabled

    @staticmethod
    def filter_disabled(wgts):
        """ Take a list and split it to 'enabled', 'disabled' sub-lists. """
        enabled = []
        disabled = []

        for wgt in wgts:
            if wgt.isEnabled():
                enabled.append(wgt)
            else:
                disabled.append(wgt)

        return enabled, disabled

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

        # if layout.count() == 0: # TODO decide whether hide unused groups
        #     layout.parentWidget().hide()
        #
        # else:
        #     layout.parentWidget().show()

    def _populate_group(self, group, widgets, hide_disabled=False, n_cols=2):
        """ Populate given group with given widgets. """
        layout = group.layout()
        self.remove_children(layout)

        if hide_disabled:
            widgets = self.hide_disabled(widgets)
            self.show_widgets(widgets)

        self.populate_grid_layout(layout, widgets, n_cols)

    def populate_outputs_group(self):
        """ Populate outputs buttons. """
        outputs_btns = [self.building_totals_btn,
                        self.all_eso_files_btn]

        self._populate_group(self.outputs_group, outputs_btns)

    def populate_intervals_group(self, hide_disabled=True):
        """ Populate interval buttons based on a current state. """
        btns = self.interval_btns.values()
        self._populate_group(self.intervals_group, btns, hide_disabled=hide_disabled)

    def populate_tools_group(self):
        """ Populate tools group layout. """
        tools_btns = [self.export_xlsx_btn, ]
        self._populate_group(self.tools_group, tools_btns)

    def populate_units_group(self):
        """ Populate units group layout. """
        btns = [self.energy_units_btn,
                self.power_units_btn,
                self.units_system_btn,
                self.rate_to_energy_btn]

        self._populate_group(self.units_group, btns)

    def set_up_outputs_btns(self):
        """ Create interval buttons and a parent container. """
        # ~~~~ Layout to hold interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        outputs_btns_layout = QGridLayout(self.outputs_group)
        outputs_btns_layout.setSpacing(0)
        outputs_btns_layout.setContentsMargins(0, 0, 0, 0)
        outputs_btns_layout.setAlignment(Qt.AlignTop)

        self.building_totals_btn.setText("totals")
        self.building_totals_btn.setCheckable(True)
        self.building_totals_btn.setEnabled(False)
        outputs_btns_layout.addWidget(self.building_totals_btn)

        # ~~~~ Generate all eso files button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.all_eso_files_btn.setText("all files")
        self.all_eso_files_btn.setCheckable(True)
        self.all_eso_files_btn.setEnabled(False)
        outputs_btns_layout.addWidget(self.all_eso_files_btn)

        self.populate_outputs_group()

    def set_up_interval_btns(self):
        """ Create interval buttons and a parent container. """
        # ~~~~ Layout to hold interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        interval_btns_layout = QGridLayout(self.intervals_group)
        interval_btns_layout.setSpacing(0)
        interval_btns_layout.setContentsMargins(0, 0, 0, 0)
        interval_btns_layout.setAlignment(Qt.AlignTop)

        # ~~~~ Generate interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        p = self.intervals_group
        ids = {TS: "TS", H: "H", D: "D", M: "M", A: "A", RP: "RP"}
        font = QFont("Roboto", 40)
        color = QColor(112, 112, 112)

        for k, v in ids.items():
            btn = IntervalButton(k, text_to_pixmap(v, font, color), parent=p)
            btn.setIconSize(QSize(20, 20))
            self.interval_btns[k] = btn

        self.populate_intervals_group(hide_disabled=False)

    def set_up_units(self):
        """ Set up units options. . """
        # ~~~~ Layout to hold options  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_layout = QGridLayout(self.units_group)
        units_layout.setSpacing(0)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        energy_units_menu = QMenu(self)
        items = si_energy_units + ip_energy_units
        ix = items.index(DEFAULTS["energy_units"])
        self.energy_units_btn = TitledButton(self.units_group, fill_space=True,
                                             title="energy", menu=energy_units_menu,
                                             items=items, data=items, def_act_ix=ix)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        power_units_menu = QMenu(self)
        items = list(dict.fromkeys(si_power_units + ip_power_units))  # remove duplicate 'W'
        ix = items.index(DEFAULTS["power_units"])
        self.power_units_btn = TitledButton(self.units_group, fill_space=True,
                                            title="power", menu=power_units_menu,
                                            items=items, data=items, def_act_ix=ix)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_system_menu = QMenu(self)
        items = ["SI", "IP"]
        ix = items.index(DEFAULTS["units_system"])
        self.units_system_btn = TitledButton(self.units_group, fill_space=True,
                                             title="system", menu=units_system_menu,
                                             items=items, data=items, def_act_ix=ix)
        self.toggle_units(DEFAULTS["units_system"])

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_to_energy_btn = QToolButton(self.units_group)
        self.rate_to_energy_btn.setCheckable(True)
        self.rate_to_energy_btn.setObjectName("rateToEnergyBtn")
        self.rate_to_energy_btn.setText("rate to\n energy")

        self.populate_units_group()

    def set_up_tools(self):
        """ Create a general set of tools. """
        # ~~~~ Layout to hold tools settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        tools_layout = QGridLayout(self.tools_group)
        tools_layout.setSpacing(0)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setAlignment(Qt.AlignTop)

        # ~~~~ Generate export xlsx button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.export_xlsx_btn.setEnabled(False)
        self.export_xlsx_btn.setText("Save xlsx")
        self.export_xlsx_btn.setCheckable(False)

        self.populate_tools_group()

    def set_up_view_tools(self):
        """ Create tools, settings and search line for the view. """
        # ~~~~ Widget to hold tree view tools ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        view_tools_layout = QHBoxLayout(self.view_tools_wgt)
        view_tools_layout.setSpacing(6)
        view_tools_layout.setContentsMargins(0, 0, 0, 0)

        # ~~~~ Widget to hold tree view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btn_widget = QWidget(self.view_tools_wgt)
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

        is_checked = DEFAULTS["tree_view"]
        self.tree_view_btn.setChecked(is_checked)
        self.handle_col_ex_btns(is_checked)

        spacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # ~~~~ Add child widgets to treeTools layout ~~~~~~~~~~~~~~~~~~~~~~~~
        view_tools_layout.addWidget(self.filter_icon)
        view_tools_layout.addWidget(self.filter_line_edit)
        view_tools_layout.addItem(spacer)
        view_tools_layout.addWidget(btn_widget)

    def building_totals(self):
        """ Check if building totals are requested. """
        return self.building_totals_btn.isChecked()

    def is_tree(self):
        """ Check if tree structure is requested. """
        return self.tree_view_btn.isChecked()

    def handle_col_ex_btns(self, enabled):
        """ Enable / disable 'collapse all' / 'expand all' buttons. """
        self.collapse_all_btn.setEnabled(enabled)
        self.expand_all_btn.setEnabled(enabled)

    def build_view(self):
        """ Create a new model when the tab or the interval has changed. """
        # retrieve required inputs from the interface
        is_tree = self.is_tree()
        totals = self.building_totals()
        interval = self.get_selected_interval()
        units_settings = self.get_units_settings()

        eso_file_widget = self.current_eso_file
        selection = self.selected
        view_settings = self.stored_view_settings

        if not eso_file_widget:
            # do not update the view as there is no file
            return

        # update the current widget
        eso_file_widget.update_view_model(totals, is_tree, interval, view_settings,
                                          units_settings, select=selection)

        # check if some filtering is applied,
        # if yes, update the model accordingly
        if self.filter_line_edit.text():
            self._filter_view()

    def update_layout(self):
        """ Update window layout accordingly to window size. """
        # TODO Review if suitable
        # here can be a code to update toolbar layout when main window is resized
        # new_cols = 2 if self.height() < HEIGHT_THRESHOLD else 1
        # if new_cols != self.n_toolbar_cols:
        #     self.n_toolbar_cols = new_cols
        #     self.populate_intervals_group()
        #     self.populate_units_group()
        #     self.populate_settings_group()
        pass

    def interval_changed(self):
        """ Update view when an interval is changed. """
        # handle changing the state on rate_to_energy_btn
        # as this is allowed only for daily+ intervals
        if self.custom_units_toggle.isChecked():
            interval = self.get_selected_interval()
            b = interval not in [TS, H]
            self.rate_to_energy_btn.setEnabled(b)

        # create a new view
        self.build_view()

    def get_units_settings(self):
        """ Get currently selected units. """
        btn = self.rate_to_energy_btn
        rate_to_energy = btn.isEnabled() and btn.isChecked()

        units_system = self.units_system_btn.data()
        energy_units = self.energy_units_btn.data()
        power_units = self.power_units_btn.data()

        return rate_to_energy, units_system, energy_units, power_units

    def store_units_settings(self):
        """ Store intermediate units settings. """
        self._units_settings["energy_units"] = self.energy_units_btn.data()
        self._units_settings["power_units"] = self.power_units_btn.data()
        self._units_settings["units_system"] = self.units_system_btn.data()
        self._units_settings["rate_to_energy"] = self.rate_to_energy_btn.isEnabled()

    def restore_units_settings(self):
        """ Restore units settings. """
        data = self._units_settings["units_system"]
        act = self.units_system_btn.get_action(data=data)
        self.units_system_btn.update_state_internally(act)

        data = self._units_settings["energy_units"]
        act = self.energy_units_btn.get_action(data=data)
        self.energy_units_btn.update_state_internally(act)

        data = self._units_settings["power_units"]
        act = self.power_units_btn.get_action(data=data)
        self.power_units_btn.update_state_internally(act)

        self.build_view()

    def enable_units_buttons(self, enable):
        """ Enable or disable units settings buttons. """
        self.units_system_btn.setEnabled(enable)
        self.energy_units_btn.setEnabled(enable)
        self.power_units_btn.setEnabled(enable)
        self.rate_to_energy_btn.setEnabled(enable)

    def reset_units_to_default(self):
        """ Reset units to E+ default. """
        act = self.units_system_btn.get_action(data="SI")
        self.units_system_btn.update_state_internally(act)

        act = self.energy_units_btn.get_action(data="J")
        self.energy_units_btn.update_state_internally(act)

        act = self.power_units_btn.get_action(data="W")
        self.power_units_btn.update_state_internally(act)

        self.build_view()

    def units_settings_toggled(self, state):
        """ Update units settings when custom units toggled. """
        if state == 0:
            self.store_units_settings()
            self.reset_units_to_default()
            self.enable_units_buttons(False)
        else:
            self.restore_units_settings()
            self.enable_units_buttons(True)

    def toggle_units(self, units_system):
        """ Handle displaying allowed units for given units system. """
        if units_system == "IP":
            en_acts = ip_energy_units
            pw_acts = ip_power_units

        else:
            en_acts = si_energy_units
            pw_acts = si_power_units

        self.energy_units_btn.filter_visible_actions(en_acts)
        self.power_units_btn.filter_visible_actions(pw_acts)

    def units_system_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.units_system_btn.update_state(act)

        dt = act.data()
        self.toggle_units(dt)

        if changed:
            self.build_view()

    def power_units_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.power_units_btn.update_state(act)

        if changed:
            self.build_view()

    def energy_units_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.energy_units_btn.update_state(act)

        if changed:
            self.build_view()

    def rate_to_energy_toggled(self):
        """ Update view when rate_to_energy changes. """
        self.build_view()

    def tree_btn_toggled(self, checked):
        """ Update view when view type is changed. """
        self.tree_view_btn.setProperty("checked", checked)

        # collapse and expand all buttons are not relevant for plain view
        self.handle_col_ex_btns(checked)

        self.build_view()

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
        if not self.tab_wgt.is_empty():
            self.current_eso_file.filter_view(filter_string)

    def text_edited(self):
        """ Delay firing a text edited event. """
        self.timer.start(200)

    def remove_eso_file(self, wgt):
        """ Delete current eso file. """
        std_id_ = wgt.std_file_header.id_
        tot_id_ = wgt.tot_file_header.id_

        wgt.deleteLater()
        self.delete_files_from_db(std_id_, tot_id_)

        if self.tab_wgt.is_empty():
            self.building_totals_btn.setEnabled(False)

        if self.tab_wgt.count() <= 1:
            # only one file is available
            self.all_eso_files_btn.setEnabled(False)

    def disable_interval_btns(self):
        """ Disable all interval buttons. """
        for btn in self.interval_btns.values():
            btn.setHidden(False)
            btn.setChecked(False)
            btn.setEnabled(False)

    def delete_files_from_db(self, *args):
        """ Delete the eso file from the database. """
        try:
            for id_ in args:
                print("Deleting file id: '{}' from database.".format(self.database[id_]))
                del self.database[id_]

        except KeyError:
            print("Cannot delete the eso file: id '{}',\n"
                  "File was not found in database.".format(file_id))

    def _available_intervals(self):
        """ Get available intervals for the current eso file. """
        intervals = self.current_eso_file.std_file_header.available_intervals
        return intervals

    def update_interval_buttons_state(self):
        """ Deactivate interval buttons if they are not applicable. """
        available_intervals = self._available_intervals()
        selected_interval = self.get_selected_interval()
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
        if selected_interval not in available_intervals:
            btn = next(btn for btn in all_btns_dct.values() if btn.isEnabled())
            btn.setChecked(True)

    def tab_changed(self, index):
        """ Update view when tabChanged event is fired. """
        print("Tab changed {}".format(index))
        if index != -1:
            self.update_interval_buttons_state()
            self.build_view()
            self.populate_intervals_group()

        else:
            # there aren't any widgets available
            self.set_initial_layout()

    def create_ui_actions(self):
        """ Create actions which depend on user actions """
        # ~~~~ Resize window ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.resized.connect(self.update_layout)

        # ~~~~ Interval buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btns = self.interval_btns.values()
        _ = [btn.clicked.connect(self.interval_changed) for btn in btns]

        # ~~~~ Options buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.export_xlsx_btn.clicked.connect(self.export_xlsx)
        self.building_totals_btn.clicked.connect(self.switch_totals)

        # ~~~~ View Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.expand_all_btn.clicked.connect(self.expand_all)
        self.collapse_all_btn.clicked.connect(self.collapse_all)
        self.left_main_wgt.fileDropped.connect(self._load_eso_files)

        # ~~~~ Options Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.custom_units_toggle.stateChanged.connect(self.units_settings_toggled)
        self.rate_to_energy_btn.clicked.connect(self.rate_to_energy_toggled)

        # ~~~~ Settings Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tree_view_btn.clicked.connect(self.tree_btn_toggled)
        self.energy_units_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_units_btn.menu().triggered.connect(self.power_units_changed)
        self.units_system_btn.menu().triggered.connect(self.units_system_changed)

        # ~~~~ Filter action ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.textEdited.connect(self.text_edited)

        # ~~~~ Tab actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.tabClosed.connect(self.remove_eso_file)
        self.tab_wgt.currentChanged.connect(self.tab_changed)
        self.tab_wgt.fileLoadRequested.connect(self.load_files)

    def update_sections_order(self, order):
        """ Store current view header order. """
        self.stored_view_settings["header"] = order

    def update_sort_order(self, name, new_order):
        """ Store current column vertical sorting. """
        self.stored_view_settings["order"] = (name, new_order)

    def update_section_widths(self, key, width):
        """ Store current column widths. """
        self.stored_view_settings["widths"][key] = width

    def clear_expanded_set(self):
        """ Clear previously stored expanded items set. """
        self.stored_view_settings["expanded"].clear()

    def update_expanded_set(self, add=None, remove=None):
        """ Handle populating and removing items from 'expanded' set. """
        expanded_set = self.stored_view_settings["expanded"]

        if add:
            expanded_set.add(add)
        if remove:
            expanded_set.remove(remove)

    def get_current_file_id(self):
        """ Return an id of the currently selected file. """
        return self.current_eso_file.get_file_id(self.building_totals())

    def add_file_to_db(self, file_id, eso_file):
        """ Add processed eso file to the database. """
        try:
            print("Adding file: '{}', id '{}' into database.".format(eso_file.file_name, file_id))
            self.database[file_id] = eso_file

        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")

    def on_file_loaded(self, id_, std_file, tot_file):
        """ Add eso file into 'tab' widget. """
        std_id_ = f"s{id_}"
        std_file_header = FileHeader(std_id_, std_file.header_dct)
        self.add_file_to_db(std_id_, std_file)

        tot_id_ = f"t{id_}"
        tot_file_header = FileHeader(tot_id_, tot_file.header_dct)
        self.add_file_to_db(tot_id_, std_file)

        eso_file_widget = View(self, std_file_header, tot_file_header)
        self.tab_wgt.add_tab(eso_file_widget, std_file.file_name)

        # enable all eso file results btn if there's multiple files
        if self.tab_wgt.count() > 1:
            self.all_eso_files_btn.setEnabled(True)

        # enable all eso file results btn if it's suitable
        if not self.tab_wgt.is_empty():
            self.building_totals_btn.setEnabled(True)

    def all_files_ids(self):
        """ Return ids of all loaded eso files. """
        files = self.all_eso_files
        ids = [file.file_id for file in files]
        return ids

    def get_files_ids(self):
        """ Return current file id or ids for all files based on 'all files btn' state. """
        if self.all_eso_files_requested():
            return self.all_files_ids()

        file_id = self.get_current_file_id()
        return [file_id]

    def generate_variables(self, outputs):
        """ Create an output request using required 'Variable' class. """
        request_lst = []
        interval = self.get_selected_interval()
        for item in outputs:
            req = Variable(interval, *item)
            request_lst.append(req)
        return request_lst

    def current_request(self):
        """ Get a currently selected output variables information. """
        outputs = self.selected
        ids = self.get_files_ids()
        variables = None

        # add an interval information into the request
        # create 'request items' using 'Variable' namedtuple
        if outputs:
            variables = self.generate_variables(outputs)

        return ids, variables

    def _load_eso_files(self, eso_file_paths):
        """ Start eso file processing. """
        progress_queue = self.progress_queue
        file_queue = self.file_queue

        used_ids = self.database.keys()
        n = len(eso_file_paths)
        ids = generate_ids(used_ids, n=n)

        for path in eso_file_paths:
            # create a monitor to report progress on the ui
            id_ = ids.pop(0)
            monitor = GuiMonitor(path, id_, progress_queue)

            # create a new process to load eso file
            future = self.pool.submit(load_file, path, monitor=monitor, suppress_errors=False)
            future.add_done_callback(partial(wait_for_results, id_, monitor, file_queue))

    def load_files(self):
        """ Select eso files from explorer and start processing. """
        file_pths, _ = QFileDialog.getOpenFileNames(self, "Load Eso File", "", "*.eso")
        if file_pths:
            self._load_eso_files(file_pths)

    def results_df(self):
        """ Get output values for given variables. """
        ids, variables = self.current_request()
        rate_to_energy, units_system, energy, power = self.get_units_settings()
        rate_to_energy_dct = {self.get_selected_interval(): rate_to_energy}

        files = [v for k, v in self.database.items() if k in ids]
        df = get_results(files, variables, rate_units=power,
                         energy_units=energy, add_file_name="column",
                         rate_to_energy_dct=rate_to_energy_dct)

        return df

    # TODO review these when handling results
    def single_file_results(self, request):
        return get_results(self.currentEsoFileWidget.esoFile, request)

    def multiple_files_results(self, requestList):
        esoFiles = [esoFileWidget.esoFile for esoFileWidget in
                    self.esoFileWidgets]
        esoFiles.sort(key=lambda x: x.file_name)
        return get_results(esoFiles, requestList)

    def switch_totals(self):
        """ Toggle standard outputs and totals. """
        self.build_view()

    def export_xlsx(self):
        """ Export selected variables data to xlsx. """
        df = self.results_df()
        df.to_excel("C:/users/vojte/desktop/test.xlsx")

    def close_all_tabs(self):
        """ Delete all the content. """
        ids = []
        wgts = self.tab_wgt.close_all_tabs()
        for i in range(len(wgts)):
            ids.append(wgts[i].std_file_header.id_)
            ids.append(wgts[i].tot_file_header.id_)
            wgts[i].deleteLater()

        self.delete_files_from_db(*ids)
        self.set_initial_layout()


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


def load_file(path, **kwargs):
    """ Process eso file. """
    std_file = EsoFile(path, **kwargs)
    tot_file = BuildingEsoFile(std_file)
    kwargs["monitor"].building_totals_finished()
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
