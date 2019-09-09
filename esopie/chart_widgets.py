from PySide2.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QFrame, \
    QSizePolicy, QGridLayout, \
    QAction, QActionGroup, QMenu, QApplication
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView, QWebEngineSettings
import pandas as pd
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, QItemSelectionModel, QRegExp, QUrl, QObject, \
    Slot, Signal

from PySide2 import QtWebChannel

import pickle
from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor
from functools import partial


class Postman(QObject):
    def __init__(self):
        super().__init__()

    @Slot()
    def call_from_js(self):
        print("Called from JS!")


class MyWebView(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        settings = QWebEngineSettings.JavascriptCanAccessClipboard
        self.settings().setAttribute(settings, True)
        self.setAcceptDrops(True)

        self.postman = Postman()
        channel = QtWebChannel.QWebChannel(self)

        self.page().setWebChannel(channel)
        channel.registerObject("postman", self.postman)

        self.url = "http://127.0.0.1:8080/"
        self.load(QUrl(self.url))

