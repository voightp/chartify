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
from esopie.charts import Chart
from esopie.chart_settings import get_item


class Postman(QObject):
    fullChartUpdated = Signal(str, "QVariantMap")
    layoutUpdated = Signal(str, "QVariantMap")
    tracesUpdated = Signal(str, "QVariantMap")
    tracesDeleted = Signal(str, "QVariantList", "QVariantMap", "QVariantMap")
    componentAdded = Signal(str, "QVariantMap", "QVariantMap")

    def __init__(self, app):
        super().__init__()
        self.components = {}
        self.items = {}
        self.app = app
        self.counter = 0

    @Slot(QJsonValue)
    def storeGridLayout(self, items):
        print("PY storeGridLayout")
        self.items = items.toObject()

    @Slot(str)
    def removeItem(self, item_id):
        print(f"PY removeItem", item_id)
        del self.components[item_id]
        try:
            del self.items[item_id]
        except KeyError:
            # the items grid information is updated by 'storeGridLayout' slot
            # therefore self.items should be already empty
            pass

    @Slot(str)
    def addTextArea(self):
        pass

    @Slot(str)
    def addNewChart(self, chart_type):
        print(f"PY addChart {chart_type}")
        i = self.counter
        item_id = f"item-{i}"
        frame_id = f"frame-{i}"
        chart_id = f"chart-{i}"

        self.counter += 1

        chart = Chart(chart_id, item_id, chart_type)
        item = get_item(frame_id, "chart")

        self.components[item_id] = chart
        self.items[item_id] = item

        self.componentAdded.emit(item_id,
                                 item,
                                 chart.figure)

    def add_chart_data(self, item_id, df):
        chart = self.components[item_id]
        update_dct = chart.process_data(df)

        if update_dct:
            self.fullChartUpdated.emit(item_id, update_dct)

    @Slot(str, QJsonValue)
    def onChartLayoutChange(self, item_id, layout):
        layout = layout.toObject()
        chart = self.components[item_id]
        chart.layout = layout

    @Slot(str)
    def onTraceDrop(self, item_id):
        callback = partial(self.add_chart_data, item_id)
        self.app.get_results(callback=callback)

    @Slot(str, str)
    def updateChartType(self, item_id, chart_type):
        print(f"PY updateChartType {chart_type}")
        chart = self.components[item_id]
        update_dct = chart.update_chart_type(chart_type)

        self.fullChartUpdated.emit(item_id, update_dct)

    @Slot(str, str)
    def onTraceHover(self, item_id, trace_id):
        pass

    @Slot(str, str)
    def onTraceClick(self, item_id, trace_id):
        chart = self.components[item_id]
        update_dct = chart.handle_trace_selected(trace_id)
        self.tracesUpdated.emit(item_id, update_dct)

    @Slot(str)
    def deleteSelectedTraces(self, item_id):
        chart = self.components[item_id]
        ids, update_dct, remove_dct = chart.delete_selected_traces()
        self.tracesDeleted.emit(item_id, ids, update_dct, remove_dct)


class MyPage(QWebEnginePage):
    def __init__(self):
        super().__init__()

    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"JS >> {source} {line} {msg}")


class MyWebView(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)

        page = MyPage()
        self.setPage(page)

        self.postman = Postman(parent)
        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("postman", self.postman)
        self.page().setWebChannel(self.channel)

        self.url = "http://127.0.0.1:8080/"
        self.load(QUrl(self.url))
