from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QWidget, QTabWidget, QTreeView, QSplitter, QHBoxLayout, QVBoxLayout, \
    QGridLayout, \
    QToolButton, QSizePolicy, QLayout, QLabel, QGroupBox, QRadioButton, QToolBar, QMenuBar, QAction, \
    QFileDialog, \
    QDialog, QProgressBar, QFormLayout, QAbstractItemView, QSlider, QSpacerItem, QSizePolicy, \
    QLineEdit, QComboBox, \
    QMdiArea, QHeaderView, QTableView, QApplication, QScrollArea, QStatusBar
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, \
    QItemSelectionModel, QRegExp, QUrl, QTimer, QFile
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView

from PySide2.QtGui import QKeySequence
from eso_file_header import EsoFileHeader

from progress_widget import MyStatusBar

from PySide2.QtGui import QStandardItemModel, QStandardItem, QFont
import numpy
import pandas as pd
from functools import partial
import traceback
import sys
import os

projects = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(projects, "eso_reader"))
sys.path.append(os.path.join(projects, "dash_app"))

# from main_dash import start_dash
from constants import TS, D, H, M, A, RP
from eso_file import EsoFile, load_eso_file, get_results
from mini_classes import Variable
import misc_os as misc_os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from queue import Queue
from multiprocessing import Manager, cpu_count, Pipe, Process
from eso_file_widget import GuiEsoFile
from chart_widgets import MyWebView
from random import randint
from threads import PipeEcho, MonitorThread, EsoFileWatcher, GuiMonitor

globalFont = QFont("Calibri")
smallFont = QFont("Calibri", 8)


# noinspection PyPep8Naming,PyUnresolvedReferences
class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        # ~~~~ Main Window setup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.setGeometry(50, 50, 800, 600)
        self.setWindowTitle("EsoPie")
        self.setFont = globalFont
        # TODO CSS not used at the moment
        # with open("styles/app_style.css", "r") as file:
        #     cont = file.read()
        # self.setStyleSheet(cont)

        # ~~~~ Main Window widgets ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.central_layout = QHBoxLayout()
        self.central_wgt = QWidget(self)
        self.central_wgt.setLayout(self.central_layout)
        self.setCentralWidget(self.central_wgt)
        self.central_splitter = QSplitter(self.central_wgt)
        self.central_splitter.setOrientation(Qt.Horizontal)
        self.central_layout.addWidget(self.central_splitter)

        # ~~~~ Left hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.left_main_layout = QHBoxLayout()
        self.left_main_wgt = QWidget(self.central_splitter)
        self.left_main_wgt.setLayout(self.left_main_layout)
        self.central_splitter.addWidget(self.left_main_wgt)

        # ~~~~ Left hand Tools Widget ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.outputs_tools_layout = QVBoxLayout()
        self.outputs_tools_wgt = QWidget(self.left_main_wgt)
        self.outputs_tools_wgt.setLayout(self.outputs_tools_layout)
        self.left_main_layout.addWidget(self.outputs_tools_wgt)

        # ~~~~ Left hand Tools Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.exclusive_intervals = True
        self.interval_btns = {}
        self.interval_btns_group = QGroupBox("Intervals")
        self.all_eso_files_btn = QToolButton()
        self.set_up_interval_btns()
        self.outputs_tools_layout.addWidget(self.interval_btns_group, Qt.AlignTop)

        self.units_tools_group = QGroupBox("Units", self.outputs_tools_wgt)
        self.energy_units_c_box = QComboBox()
        self.power_units_c_box = QComboBox()
        self.si_radio_btn = QRadioButton("SI")
        self.ip_radio_btn = QRadioButton("IP")
        self.set_up_units_tools()
        self.outputs_tools_layout.addWidget(self.units_tools_group, Qt.AlignTop)

        # ~~~~ Left hand Tree View widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_layout = QVBoxLayout()
        self.view_wgt = QWidget()
        self.view_wgt.setLayout(self.view_layout)
        self.left_main_layout.addWidget(self.view_wgt)

        # ~~~~ Left hand Tab widget  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt = QTabWidget()
        self.set_up_tab_wgt()
        self.view_layout.addWidget(self.tab_wgt)

        # ~~~~ Left hand Tab Tools  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt = QWidget()
        self.collapse_all_btn = QToolButton()
        self.expand_all_btn = QToolButton()
        self.filter_line_edit = QLineEdit()
        self.tree_arrange_combo_box = QComboBox()
        self.set_up_view_tools()
        self.view_layout.addWidget(self.view_tools_wgt)

        # ~~~~ Right hand area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.right_main_wgt = QWidget(self.central_splitter)
        self.right_main_layout = QHBoxLayout()
        self.right_main_wgt.setLayout(self.right_main_layout)
        self.central_splitter.addWidget(self.right_main_wgt)

        # ~~~~ Right hand Tools widget ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.chart_tools_layout = QVBoxLayout()
        self.chart_tools_wgt = QWidget(self.right_main_wgt)
        self.chart_tools_wgt.setLayout(self.chart_tools_layout)
        # self.right_main_layout.addWidget(self.chart_tools_wgt, Qt.AlignTop)

        # ~~~~ Right hand Tools Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.chart_settings_btn_layout = QVBoxLayout()
        self.chart_settings_btn_group = QGroupBox("Chart Tools")
        self.chart_settings_btn_group.setLayout(self.chart_settings_btn_layout)
        self.chart_tools_layout.addWidget(self.chart_settings_btn_group, Qt.AlignTop)
        self.add_chart_btn = QToolButton()
        self.save_xlsx_btn = QToolButton()
        self.show_legend_btn = QToolButton()
        self.show_range_slider_btn = QToolButton()
        self.set_up_chart_settings_tools()

        self.chart_traces_btns_layout = QVBoxLayout()
        self.chart_traces_btns_group = QGroupBox("Traces")
        self.chart_traces_btns_group.setLayout(self.chart_traces_btns_layout)
        self.chart_tools_layout.addWidget(self.chart_traces_btns_group, Qt.AlignTop)
        self.trace_buttons = {}
        self.set_up_char_traces_tools()

        # ~~~~ Right hand Chart Scroll Area ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.right_main_scroll_area = QScrollArea()
        self.right_main_scroll_area.setWidgetResizable(True)
        self.right_main_layout.addWidget(self.right_main_scroll_area)

        self.main_chart_widget = QWidget(self.right_main_scroll_area)
        self.main_chart_layout = QGridLayout()
        self.main_chart_widget.setLayout(self.main_chart_layout)
        self.right_main_scroll_area.setWidget(self.main_chart_widget)

        # ~~~~ Set up main widgets and layouts ~~~~~~~~~~~~~~~~~~~~~~~~~
        self.set_up_base_ui()

        # ~~~~ Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.create_ui_actions()

        # ~~~~ Eso files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.futures = []
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
        self.database = self.manager.dict()

        # ~~~~ Dash app ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        app_conn, dash_conn = Pipe()
        # self.dsh = Process(target=start_dash, args=(dash_conn, self.database))
        # self.dsh.start()
        self.app_conn = app_conn

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.monitors = []
        # TODO
        # self.pipe_watcher_thread = PipeEcho(self.app_conn)
        self.watcher_thread = EsoFileWatcher(self.file_queue)
        self.monitor_thread = MonitorThread(self.progress_queue)
        self.pool = self.create_pool()
        self.create_thread_actions()
        # self.pipe_watcher_thread.start()
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
        self.show_menu = self.menuBar().addMenu("&Show")
        self.help_menu = self.menuBar().addMenu("&Help")
        self.file_menu.addAction(self.loadEsoFileAct)
        self.file_menu.addAction(self.loadFilesFromFolderAct)
        self.file_menu.addAction(self.closeAllTabsAct)

        self.chart_area = QWebEngineView(self)
        # self.chart_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chart_area.setAcceptDrops(True)

        self.url = "http://127.0.0.1:8050/"
        self.chart_area.load(self.url)
        self.main_chart_layout.addWidget(self.chart_area)

    @property
    def chart_settings(self):
        return dict(
            type=self.current_trace_type(),
            intervals=self.selected_intervals(),
            all_eso_files=self.all_eso_files_btn.isChecked(),
            show_legend=self.show_legend_btn.isChecked(),
            show_range_slider=self.show_range_slider_btn.isChecked(),
            eso_file_widgets=self.all_eso_files,
            current_eso_file_widget=self.current_eso_file
        )

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

    def closeEvent(self, event):
        """ Shutdown all background stuff. """
        self.dsh.terminate()
        self.pipe_watcher_thread.terminate()
        self.watcher_thread.terminate()
        self.monitor_thread.terminate()
        self.pool.shutdown(wait=False)
        self.manager.shutdown()

    def clear_current_selection(self):
        print("Current selection cleared!")
        self.save_xlsx_btn.setEnabled(False)
        self.current_selection = None

    def keyPressEvent(self, event):
        """ Manage keyboard events. """
        if event.key() == Qt.Key_Escape:
            if self.tab_widget_not_empty():
                self.current_eso_file.clear_selection()
            self.clear_current_selection()

    def tab_widget_not_empty(self):
        """ Check if there's at least one loaded file. """
        return self.tab_wgt.count() > 0

    def all_eso_files_requested(self):
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
        # ~~~~ Main left side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.central_layout.setSpacing(0)
        self.central_layout.setContentsMargins(0, 0, 0, 0)

        leftSideSizePolicy = QtWidgets.QSizePolicy()
        leftSideSizePolicy.setHorizontalStretch(0)
        self.left_main_wgt.setSizePolicy(leftSideSizePolicy)
        self.left_main_layout.setSpacing(0)
        self.left_main_layout.setContentsMargins(0, 0, 0, 0)

        self.outputs_tools_wgt.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.outputs_tools_wgt.setFixedWidth(90)
        self.outputs_tools_layout.setContentsMargins(0, 0, 0, 0)
        self.outputs_tools_layout.setSpacing(0)
        self.outputs_tools_layout.setAlignment(Qt.AlignTop)

        self.view_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.setSpacing(0)

        # ~~~~ Main right side ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        rightSideSizePolicy = QtWidgets.QSizePolicy()
        rightSideSizePolicy.setHorizontalStretch(1)
        self.right_main_wgt.setSizePolicy(rightSideSizePolicy)
        self.right_main_layout.setSpacing(0)
        self.right_main_layout.setContentsMargins(0, 0, 0, 0)
        self.right_main_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.chart_tools_wgt.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.chart_tools_wgt.setFixedWidth(90)
        self.chart_tools_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_tools_layout.setSpacing(0)
        self.chart_tools_layout.setAlignment(Qt.AlignTop)

        self.main_chart_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.main_chart_widget.setMinimumWidth(800)

    def set_up_tab_wgt(self):
        """ Set up appearance and behaviour of the tab widget. """
        # ~~~~ Tab widget set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.tab_wgt.setContentsMargins(3, 3, 3, 3)
        self.tab_wgt.setMinimumWidth(400)
        self.tab_wgt.setTabPosition(QTabWidget.North)
        self.tab_wgt.setUsesScrollButtons(True)
        self.tab_wgt.setTabsClosable(True)
        self.tab_wgt.setMovable(True)

    def set_up_interval_btns(self):
        """ Create interval buttons and a parent container. """
        # ~~~~ Widget to hold interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.interval_btns_group.setSizePolicy(QSizePolicy.Minimum,
                                               QSizePolicy.Fixed)
        self.interval_btns_group.setFixedHeight(200)
        interval_btns_layout = QGridLayout()
        interval_btns_layout.setSpacing(6)
        interval_btns_layout.setContentsMargins(6, 6, 6, 6)
        self.interval_btns_group.setLayout(interval_btns_layout)

        # ~~~~ Generate interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ixs = [(i, j) for i in range(3) for j in range(2)]
        keys = [(TS, "TS"), (H, "H"), (D, "D"), (M, "M"), (A, "A"), (RP, "RP")]
        for key, ix in zip(keys, ixs):
            const, text = key
            btn = QToolButton()
            btn.setEnabled(False)
            btn.setMinimumSize(QSize(36, 36))
            btn.setText(text)
            btn.setCheckable(True)
            btn.setAutoExclusive(self.exclusive_intervals)
            self.interval_btns[const] = btn
            interval_btns_layout.addWidget(self.interval_btns[const], *ix)

        # ~~~~ Generate include / exclude all files button ~~~~~~~~~~~~~~~
        self.all_eso_files_btn.setEnabled(False)
        self.all_eso_files_btn.setMinimumSize(QSize(78, 36))
        self.all_eso_files_btn.setText("All files")
        self.all_eso_files_btn.setCheckable(True)
        interval_btns_layout.addWidget(self.all_eso_files_btn, 3, 0, 1, 2)

    def set_up_chart_settings_tools(self):
        """ Create chart settings buttons and a parent container. """
        # ~~~~ Widget to hold chart buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.chart_settings_btn_group.setSizePolicy(QSizePolicy.Minimum,
                                                    QSizePolicy.Fixed)
        self.chart_settings_btn_group.setFixedHeight(120)
        self.chart_settings_btn_layout.setContentsMargins(6, 6, 6, 6)
        self.chart_settings_btn_layout.setSpacing(6)

        btn_wgt = QWidget()
        btn_layout = QGridLayout()
        btn_layout.setSpacing(6)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_wgt.setLayout(btn_layout)
        self.chart_settings_btn_layout.addWidget(btn_wgt)

        # ~~~~ Create chart buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.save_xlsx_btn.setText("xlsx")
        self.save_xlsx_btn.setMinimumSize(QSize(36, 36))
        self.save_xlsx_btn.setEnabled(False)
        btn_layout.addWidget(self.save_xlsx_btn, 0, 0)

        self.add_chart_btn.setText("Add")
        self.add_chart_btn.setMinimumSize(QSize(36, 36))
        btn_layout.addWidget(self.add_chart_btn, 0, 1)

        self.show_legend_btn.setText("Leg")
        self.show_legend_btn.setMinimumSize(QSize(36, 36))
        self.show_legend_btn.setCheckable(True)
        btn_layout.addWidget(self.show_legend_btn, 1, 0)

        self.show_range_slider_btn.setText("Rng")
        self.show_range_slider_btn.setMinimumSize(QSize(36, 36))
        self.show_range_slider_btn.setCheckable(True)
        btn_layout.addWidget(self.show_range_slider_btn, 1, 1)

    def set_up_char_traces_tools(self):
        """ Create 'trace' settings buttons and a parent container. """
        # ~~~~ Widget to hold chart buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.chart_traces_btns_group.setSizePolicy(QSizePolicy.Minimum,
                                                   QSizePolicy.Fixed)
        self.chart_traces_btns_group.setFixedHeight(120)
        self.chart_traces_btns_layout.setContentsMargins(6, 6, 6, 6)
        self.chart_traces_btns_layout.setSpacing(6)

        btn_wgt = QWidget()
        btn_layout = QGridLayout()
        btn_layout.setSpacing(6)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_wgt.setLayout(btn_layout)
        self.chart_traces_btns_layout.addWidget(btn_wgt)

        line_trace_btn = QToolButton(btn_wgt)
        line_trace_btn.setText("Line")
        line_trace_btn.setMinimumSize(QSize(36, 36))
        line_trace_btn.setCheckable(True)
        line_trace_btn.setChecked(True)
        line_trace_btn.setAutoExclusive(True)
        self.trace_buttons["line"] = line_trace_btn
        btn_layout.addWidget(self.trace_buttons["line"], 0, 0)

        bar_trace_btn = QToolButton(btn_wgt)
        bar_trace_btn.setText("Bar")
        bar_trace_btn.setMinimumSize(QSize(36, 36))
        bar_trace_btn.setCheckable(True)
        bar_trace_btn.setAutoExclusive(True)
        self.trace_buttons["bar"] = bar_trace_btn
        btn_layout.addWidget(self.trace_buttons["bar"], 0, 1)

        bub_trace_btn = QToolButton(btn_wgt)
        bub_trace_btn.setText("Bub")
        bub_trace_btn.setMinimumSize(QSize(36, 36))
        bub_trace_btn.setCheckable(True)
        bub_trace_btn.setAutoExclusive(True)
        self.trace_buttons["bubble"] = bub_trace_btn
        btn_layout.addWidget(self.trace_buttons["bubble"], 1, 1)

    def set_up_view_tools(self):
        """ Create tools, settings and search line for the view. """
        # ~~~~ Widget to hold tree view tools ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.view_tools_wgt.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.view_tools_wgt.setFixedHeight(50)
        treeViewToolsLayout = QHBoxLayout()
        treeViewToolsLayout.setSpacing(12)
        treeViewToolsLayout.setContentsMargins(6, 6, 6, 6)
        self.view_tools_wgt.setLayout(treeViewToolsLayout)

        # ~~~~ Widget to hold tree view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btnWidget = QWidget()
        btnLayout = QHBoxLayout()
        btnWidget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btnWidget.setFixedWidth(110)
        btnLayout.setSpacing(6)
        btnLayout.setContentsMargins(0, 0, 0, 0)
        btnWidget.setLayout(btnLayout)

        # ~~~~ Create tree view buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.collapse_all_btn.setText("Collapse")
        self.collapse_all_btn.setMinimumSize(QSize(52, 36))
        btnLayout.addWidget(self.collapse_all_btn)
        self.expand_all_btn.setText("Expand")
        self.expand_all_btn.setMinimumSize(QSize(52, 36))
        btnLayout.addWidget(self.expand_all_btn)

        # ~~~~ Create tree search line edit ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.filter_line_edit.setFixedWidth(80)

        # ~~~~ Widget to hold sorting slider and text hints ~~~~~~~~~~~~~~~
        self.tree_arrange_combo_box.addItems(["None", "Key", "Variable", "Units"])
        self.tree_arrange_combo_box.setCurrentIndex(2)
        self.tree_arrange_combo_box.setFixedWidth(100)

        spacer = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # ~~~~ Disable expand / collapse all buttons ~~~~~~~~~~~~~~~~~~~~~~~~
        if not self.get_tree_arrange_key():
            self.expand_all_btn.setEnabled(False)
            self.collapse_all_btn.setEnabled(False)

        # ~~~~ Add child widgets to treeTools layout ~~~~~~~~~~~~~~~~~~~~~~~~
        treeViewToolsLayout.addWidget(self.tree_arrange_combo_box)
        treeViewToolsLayout.addWidget(self.filter_line_edit)
        treeViewToolsLayout.addItem(spacer)
        treeViewToolsLayout.addWidget(btnWidget)

        # ~~~~ Add treeTools widget to main left layout ~~~~~~~~~~~~~~~~~~~~~
        # self.treeViewLayout.addWidget(self.treeViewToolsGroup)

    def set_up_units_tools(self):
        """ Create units combo boxes and a parent container. """
        # ~~~~ Set margins and spacing for all child widgets ~~~~~~~~~~~~~~~~
        margins = (3, 3, 3, 3)
        spacing = 6

        # ~~~~ Widget to hold units settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.units_tools_group.setSizePolicy(QSizePolicy.Minimum,
                                             QSizePolicy.Fixed)
        self.units_tools_group.setFixedHeight(200)
        units_tools_layout = QGridLayout()
        units_tools_layout.setSpacing(6)
        units_tools_layout.setContentsMargins(6, 6, 6, 6)
        self.units_tools_group.setLayout(units_tools_layout)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        energy_units_wgt = QWidget()
        energy_units_layout = QVBoxLayout()
        energy_units_layout.setSpacing(spacing)
        energy_units_layout.setContentsMargins(*margins)
        energy_units_wgt.setLayout(energy_units_layout)
        l1 = QLabel("Energy Units")
        self.energy_units_c_box.addItems(
            ["Wh", "kWh", "MWh", "J", "kJ", "GJ", "Btu", "kBtu", "MBtu"])
        self.energy_units_c_box.setCurrentIndex(3)
        energy_units_layout.addWidget(l1)
        energy_units_layout.addWidget(self.energy_units_c_box)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        power_units_wgt = QWidget()
        power_units_layout = QVBoxLayout()
        power_units_layout.setSpacing(spacing)
        power_units_layout.setContentsMargins(*margins)
        power_units_wgt.setLayout(power_units_layout)
        l2 = QLabel("Power Units")
        self.power_units_c_box.addItems(
            ["W", "kW", "MW", "Btu/h", "kBtu/h", "MBtu/h"])
        self.power_units_c_box.setCurrentIndex(0)
        power_units_layout.addWidget(l2)
        power_units_layout.addWidget(self.power_units_c_box)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_system_wgt = QWidget()
        units_system_layout = QGridLayout()
        units_system_wgt.setLayout(units_system_layout)
        units_system_layout.setSpacing(spacing)
        units_system_layout.setContentsMargins(*margins)
        l3 = QLabel("Units system")
        units_system_layout.addWidget(l3, 0, 0, 1, 2)
        units_system_layout.addWidget(self.ip_radio_btn, 1, 0, 1, 1)
        units_system_layout.addWidget(self.si_radio_btn, 1, 1, 1, 1)

        # ~~~~ Add child widgets to units layout ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_tools_layout.addWidget(energy_units_wgt, 0, 0)
        units_tools_layout.addWidget(power_units_wgt, 1, 0)
        units_tools_layout.addWidget(units_system_wgt, 2, 0)

    def get_tree_arrange_key(self):
        """ Get current view arrange key from the interface. """
        dct = {0: None, 1: "key", 2: "var", 3: "units"}
        return dct[self.tree_arrange_combo_box.currentIndex()]

    def handle_col_ex_btns(self, tree_arrange_key):
        """ Enable / disable 'collapse all' / 'expand all' buttons. """
        if not tree_arrange_key:
            self.collapse_all_btn.setEnabled(False)
            self.expand_all_btn.setEnabled(False)

        else:
            self.collapse_all_btn.setEnabled(True)
            self.expand_all_btn.setEnabled(True)

    def update_view(self, is_fresh=False):
        """ Create a new model when the tab or the interval has changed. """
        # retrieve required inputs from the interface
        tree_arrange_key = self.get_tree_arrange_key()
        intervals = self.selected_intervals()
        current_eso_file_widget = self.current_eso_file
        current_selection = self.current_selection
        current_view_settings = self.current_view_settings

        # update the current widget
        current_eso_file_widget.update_view_model(tree_arrange_key,
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
        self.handle_col_ex_btns(tree_arrange_key)

    def interval_changed(self):
        """ Update view when an interval is changed. """
        if self.tab_widget_not_empty():
            self.update_view()

    def tree_arrange_key_changed(self):
        """ Update view when view type is changed. """
        if self.tab_widget_not_empty():
            self.update_view()

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
        if self.tab_widget_not_empty():
            self.current_eso_file.filter_view(filter_string)

    def text_edited(self):
        """ Delay firing a text edited event. """
        self.timer.start(200)

    def remove_eso_file(self):
        """ Delete current eso file. """
        index = self.tab_wgt.currentIndex()
        self.delete_eso_file_content(index)

    def disable_interval_btns(self):
        """ Disable all interval buttons. """
        for btn in self.interval_btns.values():
            btn.setEnabled(False)

    def delete_file_from_db(self, file_id):
        """ Delete the eso file from the database. """
        try:
            file = self.database[file_id]
            print("Deleting file: '{}' from database.".format(file.file_path))
            del file
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

        if self.tab_wgt.count() == 0:
            # there aren't any widgets available
            self.disable_interval_btns()

        if self.tab_wgt.count() <= 1:
            # only one file is available
            self.all_eso_files_btn.setEnabled(False)

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
        # a first available button is selected
        if all(map(lambda x: x not in available_intervals, selected_intervals)):
            btn = next(btn for btn in all_btns_dct.values() if btn.isEnabled())
            btn.setChecked(True)

    def tab_changed(self, index):
        """ Update view when tabChanged event is fired. """
        print("Tab changed {}".format(index))
        if self.tab_widget_not_empty():
            self.update_view(is_fresh=True)
            self.update_interval_buttons_state()

    def create_ui_actions(self):
        """ Create actions which depend on user actions """
        # ~~~~ Interval buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        _ = [btn.clicked.connect(self.interval_changed) for btn in self.interval_btns.values()]

        # ~~~~ Tree View Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tree_arrange_combo_box.currentIndexChanged.connect(self.tree_arrange_key_changed)
        self.expand_all_btn.clicked.connect(self.expand_all)
        self.collapse_all_btn.clicked.connect(self.collapse_all)

        # ~~~~ Filter action ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.filter_line_edit.textEdited.connect(self.text_edited)

        # ~~~~ Tab actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tab_wgt.tabCloseRequested.connect(self.remove_eso_file)
        self.tab_wgt.currentChanged.connect(self.tab_changed)

        # ~~~~ Chart actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.save_xlsx_btn.clicked.connect(self.saveCurrentSelectionToXlsx)

    def update_sort_order(self, new_index, new_order):
        """ Store current column vertical sorting. """
        self.current_view_settings["order"] = (new_index, new_order)

    def update_section_widths(self, new_widths_dct):
        """ Store current column widths. """
        self.current_view_settings["widths"] = new_widths_dct

    def clear_expanded_set(self):
        """ Clear previously stored expanded items set. """
        expanded_set = self.current_view_settings["expanded"]
        expanded_set.clear()

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
        self.status_bar.add_progress_bar(monitor_id, monitor_name)

    def update_progress_text(self, monitor_id, text):
        """ Update text info for a given monitor. """
        self.status_bar.progressBars[monitor_id].setText(text)

    def set_progress_bar_max(self, monitor_id, max_value):
        """ Set maximum progress value for a given monitor. """
        self.status_bar.progressBars[monitor_id].setRange(1, max_value)

    def update_bar_progress(self, monitor_id, value):
        """ Update progress value for a given monitor. """
        self.status_bar.progressBars[monitor_id].setValue(value)

    def delete_monitor(self, monitor_id):
        monitors = self.monitors
        mon = next(monitor for monitor in monitors if monitor.id == monitor_id)
        monitors.remove(mon)

    def file_loaded(self, monitor_id):
        """ Remove a progress bar when the file is loaded. """
        self.status_bar.remove_progress_bar(monitor_id)
        self.delete_monitor(monitor_id)

    @staticmethod
    def create_pool():
        """ Create a new pool. """
        n_cores = cpu_count()
        workers = (n_cores - 1) if n_cores > 1 else 1
        return ProcessPoolExecutor(max_workers=workers)

    def pool_shutdown(self):
        """ Shutdown the pool if all the futures are done. """
        if all(map(lambda x: x.done(), self.futures)):
            self.pool.shutdown(wait=False)
            self.futures.clear()
            self.pool = self.create_pool()

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
        print("Adding file: '{}' with id '{}' into database.".format(eso_file.file_name, file_id))
        self.database[file_id] = eso_file
        database[file_id] = eso_file

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

    def get_files_ids(self):
        """ Return current file id or ids for all files based on 'all files btn' state. """
        if self.all_eso_files_requested():
            return self.all_files_ids()
        file_id = self.current_eso_file_id()
        return [file_id]

    def generate_variables(self, outputs):
        """ Create an output request using required 'Variable' class. """
        request_lst = []
        for interval in self.selected_intervals():
            for item in outputs:
                req = Variable(interval, *item)
                request_lst.append(req)
        return request_lst

    def send_output(self):
        """ Send an output request with model information to the 'dash' part of the app. """
        outputs = self.current_selection
        ids = self.get_files_ids()

        # add an interval information into the request
        # create 'request items' using 'Variable' namedtuple
        variables = self.generate_variables(outputs)

        msg = {"ids": ids,
               "vars": variables}
        self.app_conn.send(msg)

    def create_thread_actions(self):
        """ Create actions related to background threads. """
        self.watcher_thread.loaded.connect(self.add_eso_file)
        self.monitor_thread.started.connect(self.start_loading_file)
        self.monitor_thread.progress_text_updated.connect(self.update_progress_text)
        self.monitor_thread.progress_bar_updated.connect(self.update_bar_progress)
        self.monitor_thread.preprocess_finished.connect(self.set_progress_bar_max)
        self.monitor_thread.finished.connect(self.file_loaded)
        # TODO
        # self.pipe_watcher_thread.output_requested.connect(self.send_output)

    def populate_current_selection(self, outputs):
        self.save_xlsx_btn.setEnabled(True)
        self.current_selection = outputs
        for item in outputs:
            print("{} : {} : [{}]".format(*item))

    def singleFileResults(self, requestList):
        return get_results(self.currentEsoFileWidget.esoFile, requestList)

    def multipleFileResults(self, requestList):
        esoFiles = [esoFileWidget.esoFile for esoFileWidget in
                    self.esoFileWidgets]
        esoFiles.sort(key=lambda x: x.file_name)
        return get_results(esoFiles, requestList)

    def saveCurrentSelectionToXlsx(self):
        path, filter = QFileDialog.getSaveFileName(self, "Save grid", "",
                                                   "*.xlsx")
        if path:
            if self.allEsoFilesResults:
                df = self.multipleFileResults(self.current_selection)
            else:
                df = self.singleFileResults(self.current_selection)
            df.to_excel(path)

    def wait_for_results(self, monitor, future):
        """ Put loaded file into the queue and clean up the pool. """
        try:
            esoFile = future.result()
            if esoFile:
                self.file_queue.put(esoFile)
            else:
                monitor.processing_failed("Processing failed!")
        except Exception as e:
            monitor.processing_failed("Processing failed!")
            traceback.print_exc()
        finally:
            self.pool_shutdown()

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
        for path in eso_file_paths:
            # create a monitor to report progress on the ui
            monitor_id = self.generate_id(monitor_ids)
            queue = self.progress_queue
            monitor = GuiMonitor(path, monitor_id, queue)
            self.monitors.append(monitor)

            # create a new process to load eso file
            future = self.pool.submit(load_eso_file, path, monitor=monitor)
            future.add_done_callback(partial(self.wait_for_results, monitor))
            self.futures.append(future)

    def openFiles(self):
        filePaths, filterExt = QFileDialog.getOpenFileNames(self,
                                                            "Load Eso File", "",
                                                            "*.eso")
        if filePaths:
            self._load_eso_file(filePaths)

    def openFolder(self):
        dirPath = QFileDialog.getExistingDirectory(self,
                                                   "Open folder (includes subfolders).")
        if dirPath:
            paths = misc_os.list_files(dirPath, 3, ext="eso")
            self._load_eso_file(paths)

    # noinspection PyAttributeOutsideInit
    def create_menu_actions(self):
        # ~~~~ Menu actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.loadEsoFileAct = QAction("&Load Eso Files", self)
        self.loadEsoFileAct.setShortcut(QKeySequence("Ctrl+L"))
        self.loadEsoFileAct.triggered.connect(self.openFiles)
        self.loadEsoFileAct.setStatusTip("Select Eso file to load")

        self.loadFilesFromFolderAct = QAction("&Load Eso Files from folder", self)
        self.loadFilesFromFolderAct.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self.loadFilesFromFolderAct.triggered.connect(self.openFolder)
        self.loadFilesFromFolderAct.setStatusTip("Select folder to load eso files.")

        self.closeAllTabsAct = QAction("Close all eso files.", self)
        self.closeAllTabsAct.setShortcut(QKeySequence("Ctrl+Alt+C"))
        self.closeAllTabsAct.triggered.connect(self.closeAllTabs)
        self.closeAllTabsAct.setStatusTip("Close all open tabs.")

    def closeAllTabs(self):
        for _ in range(self.tab_wgt.count()):
            self.delete_eso_file_content(0)


if __name__ == "__main__":
    database = Manager().dict()
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    availableGeometry = app.desktop().availableGeometry(mainWindow)
    mainWindow.resize(availableGeometry.width() * 4 // 5,
                      availableGeometry.height() * 4 // 5)
    mainWindow.show()
    sys.exit(app.exec_())
