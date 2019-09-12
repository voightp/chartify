from PySide2.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QFrame, \
    QSizePolicy, QGridLayout, \
    QAction, QActionGroup, QMenu, QApplication
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView, QWebEngineSettings
import pandas as pd
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, QItemSelectionModel, QRegExp, QUrl, QObject, \
    Slot, Signal, Property, QJsonValue, QJsonArray

from PySide2 import QtWebChannel

import pickle
from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import json


class Postman(QObject):
    attribute_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.m_attribute = ""

    @Slot(QJsonValue)
    def call_from_js(self, data):
        print(data)
        print("Called from JS!")

    @Slot(QJsonValue, str)
    def chartInitialized(self, figure, itemId):
        dct = figure.toObject()
        print(dct)
        print(figure)
        print("chartInitialized: " + itemId)

    @Slot(QJsonValue, str)
    def chartUpdated(self, figure, itemId):
        print("chartUpdated: " + itemId)

    @Slot(str)
    def traceDropped(self, item_id):
        print("Trace dropped on " + item_id)

    @Property(str, notify=attribute_changed)
    def attribute(self):
        return self.m_attribute

    @attribute.setter
    def set_attribute(self, attribute):
        if self.m_some_attribute == attribute:
            return
        self.m_attribute = attribute


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
