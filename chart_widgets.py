from PySide2.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QFrame, QSizePolicy, QGridLayout, \
    QAction, QActionGroup, QMenu, QApplication
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
import pandas as pd
from plotly.offline import plot
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, QSortFilterProxyModel, \
    QModelIndex, \
    QItemSelectionModel, QRegExp, QUrl
import pickle
from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor
from functools import partial



class ChartWidget(QFrame):
    def __init__(self, parent_widget, main_app):
        super().__init__(parent_widget)
        self.setFrameShape(QFrame.Box)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setMinimumHeight(600)

        self.webView = MyWebView(self)

        self.chartLoadingBar = QProgressBar(self)
        self.chartLoadingBar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.chartLoadingBar.setFixedWidth(100)
        self.chartLoadingBar.setVisible(False)

        layout = QGridLayout()
        layout.addWidget(self.webView, 0, 0)
        layout.addWidget(self.chartLoadingBar, 0, 0)
        self.setLayout(layout)


class MyWebView(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)

        self.url = "http://127.0.0.1:8050/"
        self.load(self.url)
