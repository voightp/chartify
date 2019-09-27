import copy

from esopie.utils.utils import get_str_identifier, update_recursively
from esopie.chart_settings import (get_x_domain, get_x_axis_settings,
                                   get_y_axis_settings, get_units_y_dct,
                                   style, config, get_trace_settings,
                                   layout_dct, color_generator)


def assign_color(dct, color):
    try:
        dct["marker"]["color"] = color
    except KeyError:
        dct["marker"] = {"color": color}


def trace2d(id_, item_id, x, y, name, color, **kwargs):
    dct = {
        "id": id_,
        "itemId": item_id,
        "name": name,
        "x": x,
        "y": y,
        **kwargs
    }

    assign_color(dct, color)

    return dct


class Points:
    def __init__(self, name_tup, data, timestamp):
        self.name_tup = name_tup
        self.data = data
        self.timestamp = timestamp

    @property
    def js_timestamp(self):
        return [ts * 1000 for ts in self.timestamp]

    @property
    def name(self):
        return " | ".join(self.name_tup)

    @property
    def file_name(self):
        return self.name_tup[0]

    @property
    def units(self):
        return self.name_tup[-1]


class Chart:
    LEGEND_MAX_HEIGHT = 100
    LEGEND_WIDTH = 400
    LEGEND_TRACE_HEIGHT = 19
    LEGEND_GAP = 10

    def __init__(self, chart_id, item_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.raw_data = {}
        self.traces = {}
        self.selected_traces = []
        self.layout = layout_dct
        self.show_custom_legend = True
        self.color_gen = color_generator(0)

    @property
    def data(self):
        return list(self.traces.values())

    @property
    def figure(self):
        return {
            "itemType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "selectedTraces": self.selected_traces,
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": self.layout,
            "data": self.data,
            "style": style,
            "config": config,
            "useResizeHandler": True
        }

    @property
    def all_units(self):
        full = [points.units for points in self.raw_data.values()]
        setlist = []
        for e in full:
            if e not in setlist:
                setlist.append(e)
        return setlist

    def gen_trace_id(self):
        ids = self.raw_data.keys()
        return get_str_identifier("trace", ids, start_i=1,
                                  delimiter="-", brackets=False)

    def process_data(self, df):
        dates = df.index.to_pydatetime()
        timestamps = [dt.timestamp() for dt in dates]
        dct = df.to_dict(orient="list")
        new_ids = []

        for col_ix, vals in dct.items():
            id_ = self.gen_trace_id()
            new_ids.append(id_)
            self.raw_data[id_] = Points(col_ix, vals, timestamps)

        return new_ids

    def add_data(self, df, auto_update=True):
        new_ids = self.process_data(df)

        if auto_update:
            self.populate_traces(new_ids)
            self.populate_layout()

    def update_chart_type(self, chart_type):
        self.type_ = chart_type
        kwargs = get_trace_settings(chart_type)
        for trace in self.data:
            update_recursively(trace, kwargs)

    def pop_trace(self, trace_id):
        pass

    def populate_layout(self):
        n = len(self.all_units)
        yaxis = get_y_axis_settings(n, increment=0.05)

        x_domain = get_x_domain(n, increment=0.05)
        xaxis = get_x_axis_settings(n=1, domain=x_domain)

        update_recursively(self.layout, {**yaxis, **xaxis})

    def populate_traces(self, ids=None):
        units_y_dct = get_units_y_dct(self.all_units)
        settings = get_trace_settings(self.type_)

        dt = {k: v for k, v in self.raw_data.items() if k in ids}

        for id_, points in dt.items():
            # further keyword modifications could mutate the data
            kwargs = copy.deepcopy(settings)
            yaxis = units_y_dct[points.units]
            color = next(self.color_gen)
            kwargs["yaxis"] = yaxis

            trace = trace2d(id_, self.item_id,
                            points.js_timestamp,
                            points.data,
                            points.name,
                            color,
                            **kwargs)

            self.traces[id_] = trace

    def update_figure(self, update_dct):
        pass

    def set_legend_visibility(self, visible=True):
        self["showCustomLegend"] = visible

    def set_chart_offset(self):
        pass
