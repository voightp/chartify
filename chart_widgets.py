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




class MyWebView(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)

        self.url = "http://127.0.0.1:8050/"
        self.load(self.url)
