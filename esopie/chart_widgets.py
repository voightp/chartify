from PySide2.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QFrame, \
    QSizePolicy, QGridLayout, \
    QAction, QActionGroup, QMenu, QApplication
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView, QWebEngineSettings
import pandas as pd
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, QItemSelectionModel, QRegExp, QUrl, QObject, \
    Slot, Signal, Property, QJsonValue, QJsonArray

from PySide2 import QtWebChannel
import json
import pickle
from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import json
from esopie.charts import Chart
from esopie.chart_settings import get_item


class Postman(QObject):
    appearanceUpdated = Signal(bool, "QVariantMap", "QVariantMap")
    chartUpdated = Signal(str, "QVariantMap", "QVariantMap", "QVariantList")
    componentAdded = Signal(str, "QVariantMap", "QVariantMap")

    def __init__(self, app, palette):
        super().__init__()
        self.components = {}
        self.items = {}
        self.app = app
        self.counter = 0
        self.palette = palette

    def set_appearance(self, flat, palette):
        if palette != self.palette:
            update_dct = {}
            colors = palette.get_all_colors()

            for id_, component in self.components.items():
                dct = component.set_layout_colors(palette)
                update_dct[id_] = {"layout": dct}

            self.palette = palette
            self.appearanceUpdated.emit(flat, colors, update_dct)

    @Slot()
    def onConnectionInitialized(self):
        # TODO handle 'Flat' assignment
        self.appearanceUpdated.emit(True, self.palette.get_all_colors(), {})

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

        chart = Chart(chart_id, item_id, self.palette, chart_type)
        item = get_item(frame_id, "chart")

        self.components[item_id] = chart
        self.items[item_id] = item

        self.componentAdded.emit(item_id,
                                 item,
                                 chart.figure)

    @Slot(str, QJsonValue)
    def onChartLayoutChange(self, item_id, layout):
        layout = layout.toObject()
        chart = self.components[item_id]
        chart.layout = layout

    def add_chart_data(self, item_id, df):
        print("add_chart_data", item_id)
        chart = self.components[item_id]
        update_dct = chart.process_data(df)
        # print(json.dumps(update_dct, indent=4))

        self.chartUpdated.emit(item_id, update_dct, {}, [])

    @Slot(str)
    def onTraceDrop(self, item_id):
        callback = partial(self.add_chart_data, item_id)
        self.app.get_results(callback=callback,
                             include_interval=True,
                             include_id=True)

    @Slot(str, str)
    def updateChartType(self, item_id, chart_type):
        print(f"PY updateChartType {chart_type}")
        chart = self.components[item_id]
        update_dct, remove_dct = chart.update_chart_type(chart_type)

        # remove all traces to clean up non-used attributes
        all_ids = chart.get_all_ids()
        print(json.dumps(update_dct, indent=4))
        self.chartUpdated.emit(item_id, update_dct, remove_dct, all_ids)

    @Slot(str, str)
    def onTraceHover(self, item_id, trace_id):
        pass

    @Slot(str, str)
    def onTraceClick(self, item_id, trace_id):
        chart = self.components[item_id]
        update_dct = chart.handle_trace_selected(trace_id)

        self.chartUpdated.emit(item_id, update_dct, {}, [])

    @Slot(str)
    def deleteSelectedTraces(self, item_id):
        chart = self.components[item_id]
        ids, update_dct, remove_dct = chart.delete_selected_traces()

        self.chartUpdated.emit(item_id, update_dct, remove_dct, ids)


class MyPage(QWebEnginePage):
    def __init__(self):
        super().__init__()

    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"JS >> {source} {line} {msg}")


class MyWebView(QWebEngineView):
    def __init__(self, parent, palette):
        super().__init__(parent)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)

        page = MyPage()
        self.setPage(page)

        self.postman = Postman(parent, palette)
        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("postman", self.postman)

        self.page().setWebChannel(self.channel)

        self.url = "http://127.0.0.1:8080/"
        self.load(QUrl(self.url))
