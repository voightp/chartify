from PySide2.QtCore import (QObject, Slot, Signal, QJsonValue, QJsonArray,
                            QUrl, QThreadPool)
from PySide2.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
from PySide2.QtGui import QColor
from PySide2 import QtWebChannel

from chartify.charts.chart import Chart
from chartify.charts.chart_settings import generate_grid_item, color_generator
from chartify.charts.chart_functions import transform_trace
from chartify.utils.utils import int_generator, calculate_totals
from chartify.settings import Settings
from chartify.charts.trace import Trace1D, Trace2D, TraceData
from chartify.model.model import AppModel
from chartify.controller.threads import Worker
from chartify.utils.tiny_profiler import profile
import json
import uuid

from typing import Tuple, List, Union


class MyPage(QWebEnginePage):
    def __init__(self):
        super().__init__()
        self.setBackgroundColor(QColor("transparent"))

    def javaScriptConsoleMessage(self, level, msg, line, source):
        if "PERFORMANCE WARNING" not in msg:
            print(f"JS >> {source} {line} {msg}")


class WVController(QObject):
    """
    A controller to provide communication between
    web view instance and core application.

    """
    fullLayoutUpdated = Signal("QVariantMap", "QVariantMap", "QVariantMap")
    componentUpdated = Signal(str, "QVariantMap")
    componentAdded = Signal(str, "QVariantMap", "QVariantMap")

    color_generator = color_generator()
    item_counter = int_generator()

    def __init__(self, model: AppModel, web_view: QWebEngineView):
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
        self.m.fullUpdateRequested.connect(self.handle_full_layout_update)

    @profile
    def handle_full_layout_update(self, colors: List[tuple]):
        """ Re-render components whet color scheme updates. """
        components = {}
        for component in self.m.fetch_all_components():
            plot = self.plot_component(component)
            components[component.item_id] = plot

        items = self.m.fetch_all_items()

        self.fullLayoutUpdated.emit(items, components, colors)

    @profile
    def gen_component_ids(self, name: str) -> Tuple[str, str, str]:
        """ Generate unique chart ids. """
        while True:
            i = next(self.item_counter)
            item_id = f"item-{i}"
            if item_id not in self.m.fetch_all_item_ids():
                break

        return item_id, f"frame-{i}", f"{name}-{i}",

    @profile
    def plot_component(self, component: Union[Chart]) -> dict:
        """ Request UI update for given component. """
        palette = self.m.fetch_palette(Settings.PALETTE_NAME)

        line_color = palette.get_color("PRIMARY_TEXT_COLOR")
        grid_color = palette.get_color("PRIMARY_TEXT_COLOR", opacity=0.3)
        modebar_color = palette.get_color("PRIMARY_TEXT_COLOR")
        modebar_active_color = palette.get_color("PRIMARY_TEXT_COLOR", opacity=0.5)
        background_color = palette.get_color("BACKGROUND_COLOR")

        if isinstance(component, Chart):
            traces = self.m.fetch_traces(component.item_id)
            component = component.as_plotly(traces, line_color, modebar_active_color,
                                            modebar_color, grid_color, background_color)
        print(json.dumps(component, indent=4))
        return component

    @profile
    def update_component(self, item_id: str) -> None:
        """ Request UI update for given component. """
        component = self.m.fetch_component(item_id)
        plot = self.plot_component(component)
        if plot:
            self.componentUpdated.emit(item_id, plot)

    @profile
    def add_new_traces(self, item_id: str, type_: str) -> None:
        """ Process raw pd.DataFrame and store the data. """
        df = self.m.get_results(include_interval=True, include_id=False)
        totals = calculate_totals(df)
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]
        chart = self.m.fetch_component(item_id)

        for col_ix, values in df.iteritems():
            trace_data_id = str(uuid.uuid1())
            color = next(self.color_generator)
            name = " | ".join(col_ix)  # file_name | interval | key | variable | units
            units = col_ix[-1]
            interval = col_ix[1]
            total_value = float(totals.loc[col_ix])
            trace_dt = TraceData(item_id, trace_data_id, name, values.tolist(),
                                 total_value, units, timestamps=timestamps,
                                 interval=interval)

            self.m.wv_database["trace_data"].append(trace_dt)

            if not chart.custom:
                # automatically create a new trace to be added into chart layout
                trace_id = str(uuid.uuid1())
                trace = Trace1D(name, item_id, trace_id, color, type_)
                trace.ref = trace_dt

                if type_ != "pie":
                    trace = transform_trace(trace, type_)

                self.m.wv_database["traces"].append(trace)

        self.update_component(item_id)

    @Slot(str)
    def onNewChartRequested(self, chart_type: str) -> None:
        """ Handle new 'chart' object request. """
        print(f"PY addNewChart {chart_type}")
        # create reference ids to backtrack user
        # interaction with layout elements on the UI
        item_id, frame_id, chart_id = self.gen_component_ids("chart")

        component = Chart(item_id, chart_id, chart_type)
        item = generate_grid_item(frame_id, "chart")

        self.m.wv_database["components"].append(component)
        self.m.wv_database["items"][item_id] = item

        plot = self.plot_component(component)

        if plot:
            self.componentAdded.emit(item_id, item, plot)

    @Slot()
    def onConnectionInitialized(self) -> None:
        """ Callback from the webview after initialized. """
        colors = self.m.palettes[Settings.PALETTE_NAME].get_all_colors()
        self.handle_full_layout_update(colors)

    @Slot(str)
    def onItemRemoved(self, item_id: str) -> None:
        """ Remove component from app model. """
        print(f"PY removeItem", item_id)
        component = self.m.fetch_component(item_id)
        self.m.wv_database["components"].remove(component)
        try:
            del self.m.wv_database["items"][item_id]
        except KeyError:
            # grid information should be updated by 'storeGridLayout'
            pass

    @Slot(str, QJsonValue)
    def onChartLayoutChanged(self, item_id: str, layout: QJsonValue,
                             geometry: QJsonValue) -> None:
        """ Handle chart resize interaction. """
        chart = self.m.fetch_component(item_id)
        chart.geometry = geometry.toObject()
        chart.ranges = {"x": {}, "y": {}, "z": {}}
        layout = layout.toObject()

        if self.m.fetch_traces(item_id):
            # only store data for non empty layouts as this would
            # introduce unwanted zoom effect when adding initial traces
            for k, v in layout.items():
                if "xaxis" in k:
                    try:
                        chart.ranges["x"][k] = layout[k]["range"]
                    except KeyError:
                        pass
                elif "yaxis" in k:
                    try:
                        chart.ranges["y"][k] = layout[k]["range"]
                    except KeyError:
                        pass
                elif "zaxis" in k:
                    try:
                        chart.ranges["z"][k] = layout[k]["range"]
                    except KeyError:
                        pass

    @Slot(QJsonValue)
    def onGridLayoutChanged(self, layout: QJsonValue) -> None:
        """ Store current grid layout. """
        self.m.wv_database["items"] = layout.toObject()

    @Slot(str, str)
    def onChartTypeUpdated(self, item_id: str, chart_type: str) -> None:
        """ Update chart type for given chart. """
        print(f"PY updateChartType {chart_type}")
        chart = self.m.fetch_component(item_id)
        chart.type_ = chart_type
        chart.ranges = {"x": {}, "y": {}, "z": {}}

        traces = self.m.fetch_traces(item_id)
        for trace in traces:
            trace = transform_trace(trace, chart_type)
            if trace:
                self.m.update_trace(trace)

        self.update_component(item_id)

    @Slot(str, str)
    def onTraceDropped(self, item_id: str, chart_type: str) -> None:
        """ Handle trace webview trace drop. """
        self.thread_pool.start(Worker(self.add_new_traces, item_id, chart_type))

    @Slot(str, str)
    def onTraceClick(self, item_id: str, trace_id: str) -> None:
        """ Handle trace webview trace click. """
        trace = self.m.fetch_trace(trace_id)
        trace.selected = not trace.selected

        self.update_component(item_id)

    @Slot(str)
    def onTracesDeleted(self, item_id: str) -> None:
        """ Remove selected traces from app model. """
        for trace in self.m.fetch_traces(item_id):
            if trace.selected:
                self.m.wv_database["traces"].remove(trace)

        self.update_component(item_id)
