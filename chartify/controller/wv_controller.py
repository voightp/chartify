from PySide2.QtCore import QObject, Slot, Signal, QJsonValue, QJsonArray

from functools import partial
from chartify.charts.chart import Chart
from chartify.charts.chart_settings import generate_grid_item
from chartify.utils.utils import int_generator, calculate_totals
from chartify.settings import Settings
from chartify.charts.trace import Trace

from PySide2.QtWebEngineWidgets import QWebEnginePage
from PySide2 import QtWebChannel


def pythonify(func):
    """ Wraps function to convert QJSON to dict. """

    def wrapper(*args):
        new_args = []
        for a in args:
            if isinstance(a, QJsonValue):
                a = a.toObject()
            new_args.append(a)
        return func(*args)

    return wrapper


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
    appearanceUpdated = Signal(bool, "QVariantMap", "QVariantMap")
    chartUpdated = Signal(str, "QVariantMap")
    componentAdded = Signal(str, "QVariantMap", "QVariantMap")

    trace_counter = int_generator()
    item_counter = int_generator()

    def __init__(self, model, web_view):
        super().__init__()
        self.m = model
        self.wv = web_view

        page = MyPage()
        self.wv.setPage(page)

        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self)
        self.wv.page().setWebChannel(self.channel)

        self.counter = int_generator()

    def gen_trace_id(self):
        """ Generate unique trace id. """
        while True:
            trace_id = f"trace-{next(self.trace_counter)}"
            if trace_id not in self.m.fetch_all_trace_ids():
                break
        return trace_id

    def gen_component_ids(self, name):
        """ Generate unique chart ids. """
        while True:
            i = next(self.item_counter)
            item_id = f"trace-{next(self.trace_counter)}"
            if item_id not in self.m.fetch_all_item_ids():
                break

        return item_id, f"{name}-{i}", f"frame-{i}"

    def process_traces(self, item_id, df):
        """ Process raw pd.DataFrame and store the data. """
        totals_sr = calculate_totals(df)
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]

        for col_ix, val_sr in df.iteritems():
            trace_id = self.gen_trace_id()
            color = next(self.color_gen)
            values = val_sr.tolist()
            total_value = float(totals_sr.loc[col_ix])
            file_name, _, interval, key, variable, units = col_ix

            args = (item_id, trace_id, file_name, interval,
                    key, variable, units, values, total_value,
                    timestamps, color)
            kwargs = {"priority": "normal", "type_": self.type_}

            self.m.add_trace(trace_id, Trace(*args, **kwargs))

    def plot_component(self, item_id):
        """ Request UI update for given component. """
        component = self.m.components[item_id]
        palette = self.m.fetch_palette(Settings.PALETTE_NAME)

        line_color = palette.get_color("PRIMARY_TEXT_COLOR", as_tuple=True)
        grid_color = palette.get_color("PRIMARY_TEXT_COLOR", opacity=0.3, as_tuple=True)
        background_color = palette.get_color("BACKGROUND_COLOR", as_tuple=True)

        if isinstance(component, Chart):
            traces = self.m.fetch_traces(item_id)
            chart = component.as_plotly(traces, line_color, grid_color,
                                        background_color)
            self.chartUpdated.emit(item_id, chart)

    @Slot(str)
    def addNewChart(self, chart_type):
        """ Handle new 'chart' object request. """
        print(f"PY addNewChart {chart_type}")
        # create reference ids to backtrack user
        # interaction with layout elements on the UI
        item_id, frame_id, chart_id = self.gen_component_ids("chart")

        chart = Chart(item_id, chart_id, chart_type)
        self.m.components[item_id] = chart

        item = generate_grid_item(frame_id, "chart")
        self.m.items[item_id] = item

        self.plot_component(item_id)

    @pythonify
    @Slot(QJsonValue)
    def storeGridLayout(self, layout):
        print("PY storeGridLayout")
        self.m.store_frid_layout(layout)

    def set_appearance(self, palette):
        if palette != self.palette:
            update_dct = {}
            colors = palette.get_all_colors()

            for id_, component in self.components.items():
                dct = component.set_layout_colors(palette)
                update_dct[id_] = {"layout": dct}

            self.palette = palette
            self.appearanceUpdated.emit(colors, update_dct)

    @Slot()
    def onConnectionInitialized(self):
        # TODO handle 'Flat' assignment
        self.appearanceUpdated.emit(True, self.palette.get_all_colors(), {})

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

    def plot_all_components(self):
        pass

    @pythonify
    @Slot(str, QJsonValue)
    def onChartLayoutChange(self, item_id, ranges):
        """ Handle chart resize interaction. """
        chart = self.m.fetch_component(item_id)
        chart.ranges = ranges

    def add_chart_data(self, item_id, df):
        print("add_chart_data", item_id)

        self.process_traces(item_id, df)
        # print(json.dumps(update_dct, indent=4))

        self.chartUpdated.emit(item_id, upd_dct, rm_dct, rm_traces)

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
        upd_dct, rm_dct, rm_traces = chart.update_chart_type(chart_type)
        upd_dct["chartType"] = chart_type

        self.chartUpdated.emit(item_id, upd_dct, rm_dct, rm_traces)

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
        upd_dct, rm_dct, rm_traces = chart.delete_selected_traces()

        self.chartUpdated.emit(item_id, upd_dct, rm_dct, rm_traces)
