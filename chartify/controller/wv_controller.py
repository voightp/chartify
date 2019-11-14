from PySide2.QtCore import (QObject, Slot, Signal, QJsonValue, QJsonArray,
                            QUrl, QThreadPool)
from PySide2.QtWebEngineWidgets import QWebEnginePage
from PySide2 import QtWebChannel

from functools import partial
from chartify.charts.chart import Chart
from chartify.charts.chart_settings import generate_grid_item, color_generator
from chartify.utils.utils import int_generator, calculate_totals
from chartify.settings import Settings
from chartify.charts.trace import Trace
from chartify.model.model import AppModel
from chartify.controller.threads import Worker
import json

from typing import Tuple


class MyPage(QWebEnginePage):
    def __init__(self):
        super().__init__()

    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"JS >> {source} {line} {msg}")


class WVController(QObject):
    """
    A controller to provide communication between
    web view instance and core application.

    """
    appearanceUpdated = Signal("QVariantMap", "QVariantMap")
    componentUpdated = Signal(str, "QVariantMap")
    componentAdded = Signal(str, "QVariantMap", "QVariantMap")

    trace_counter = int_generator()
    item_counter = int_generator()
    color_generator = color_generator()

    def __init__(self, model: AppModel, web_view):
        super().__init__()
        self.m = model
        self.wv = web_view

        page = MyPage()
        self.wv.setPage(page)

        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self)
        self.wv.page().setWebChannel(self.channel)

        self.wv.load(QUrl(Settings.URL))
        self.wv.setAcceptDrops(True)

        self.thread_pool = QThreadPool()
        self.m.appearanceUpdateRequested.connect(self.on_appearance_updated)

    def gen_trace_id(self) -> str:
        """ Generate unique trace id. """
        while True:
            trace_id = f"trace-{next(self.trace_counter)}"
            if trace_id not in self.m.fetch_all_trace_ids():
                break
        return trace_id

    def gen_component_ids(self, name: str) -> Tuple[str, str, str]:
        """ Generate unique chart ids. """
        while True:
            i = next(self.item_counter)
            item_id = f"item-{i}"
            if item_id not in self.m.fetch_all_item_ids():
                break

        return item_id, f"frame-{i}", f"{name}-{i}",

    def plot_component(self, item_id: str) -> dict:
        """ Request UI update for given component. """
        component = self.m.components[item_id]
        palette = self.m.fetch_palette(Settings.PALETTE_NAME)

        line_color = palette.get_color("PRIMARY_TEXT_COLOR")
        grid_color = palette.get_color("PRIMARY_TEXT_COLOR", opacity=0.3)
        background_color = palette.get_color("BACKGROUND_COLOR")

        if isinstance(component, Chart):
            traces = self.m.fetch_traces(component.item_id)
            component = component.as_plotly(traces, line_color, grid_color,
                                            background_color)
        print(item_id)
        print(json.dumps(component, indent=4))

        return component

    def update_component(self, item_id: str) -> None:
        """ Request UI update for given component. """
        component = self.plot_component(item_id)
        if component:
            self.componentUpdated.emit(item_id, component)

    @Slot(str)
    def addNewChart(self, chart_type: str) -> None:
        """ Handle new 'chart' object request. """
        print(f"PY addNewChart {chart_type}")

        # create reference ids to backtrack user
        # interaction with layout elements on the UI
        item_id, frame_id, chart_id = self.gen_component_ids("chart")

        component = Chart(item_id, chart_id, chart_type)
        item = generate_grid_item(frame_id, "chart")

        self.m.components[item_id] = component
        self.m.items[item_id] = item

        plot = self.plot_component(item_id)

        if plot:
            self.componentAdded.emit(item_id, item, plot)

    @Slot(QJsonValue)
    def storeGridLayout(self, layout: QJsonValue) -> None:
        print("PY storeGridLayout")
        l = layout.toObject()
        print(json.dumps(l))
        self.m.items = l

    def on_appearance_updated(self, colors):
        components = {}
        for id_ in self.m.components.keys():
            component = self.plot_component(id_)
            components[id_] = component

        self.appearanceUpdated.emit(components, colors)

    @Slot()
    def onConnectionInitialized(self):
        pass
        # self.appearanceUpdated.emit(True, self.palette.get_all_colors(), {})

    @Slot(str)
    def removeItem(self, item_id):
        print(f"PY removeItem", item_id)
        del self.m.components[item_id]
        try:
            del self.m.items[item_id]
        except KeyError:
            # the items grid information is updated by 'storeGridLayout'
            # slot therefore self.items should be already empty
            pass

    @Slot(str)
    def addTextArea(self):
        pass

    def plot_all_components(self):
        pass

    @Slot(str, QJsonValue)
    def onChartLayoutChange(self, item_id, ranges):
        """ Handle chart resize interaction. """
        chart = self.m.fetch_component(item_id)
        chart.ranges = ranges.toObject()

    def add_new_traces(self, item_id: str, type_: str) -> None:
        """ Process raw pd.DataFrame and store the data. """
        df = self.m.get_results(include_interval=True, include_id=False)

        totals_sr = calculate_totals(df)
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]

        for col_ix, val_sr in df.iteritems():
            trace_id = self.gen_trace_id()
            color = next(self.color_generator)
            total_value = float(totals_sr.loc[col_ix])
            file_name, interval, key, variable, units = col_ix

            self.m.traces.append(Trace(item_id, trace_id, file_name, interval,
                                       key, variable, units, val_sr.tolist(),
                                       total_value, timestamps, color, type_=type_))

        self.update_component(item_id)

    @Slot(str, str)
    def onTraceDropped(self, item_id, chart_type):
        self.thread_pool.start(Worker(self.add_new_traces, item_id, chart_type))

    @Slot(str, str)
    def updateChartType(self, item_id, chart_type):
        print(f"PY updateChartType {chart_type}")

        chart = self.m.components[item_id]
        chart.type_ = chart_type

        traces = self.m.fetch_traces(item_id)
        for trace in traces:
            trace.type_ = chart_type

        self.update_component(item_id)

    @Slot(str, str)
    def onTraceClick(self, item_id, trace_id):
        trace = self.m.fetch_trace(trace_id)
        trace.selected = not trace.selected

        self.update_component(item_id)

    @Slot(str)
    def deleteSelectedTraces(self, item_id):
        for trace in self.m.fetch_traces(item_id):
            if trace.selected:
                self.m.traces.remove(trace)

        self.update_component(item_id)
