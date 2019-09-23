from esopie.utils.utils import get_str_identifier, update_recursively
from esopie.chart_settings import (get_x_domain, get_x_axis_settings,
                                   get_y_axis_settings, get_units_y_dct,
                                   style, config, get_trace_settings,
                                   layout_dct)


def trace2d(id_, item_id, x, y, name, **kwargs):
    print(x)
    dct = {
        "id": id_,
        "itemId": item_id,
        "name": name,
        "x": x,
        "y": y,
        **kwargs
    }

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
    MAX_UNITS = 4

    def __init__(self, chart_id, item_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.raw_data = {}
        self.traces = {}
        self.layout = layout_dct
        self.custom = False

    @property
    def figure(self):
        return {
            "itemType": "chart",
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": self.layout,
            "data": list(self.traces.values()),
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
        update_dct = {"data": [{}]}
        kwargs = get_trace_settings(chart_type)
        for trace in self.traces.values():
            for k, v in kwargs.items():
                trace[k] = v
            update_dct["data"].append(kwargs)
        return update_dct

    def pop_trace(self, trace_id):
        pass

    def populate_layout(self):
        n = len(self.all_units)
        yaxis = get_y_axis_settings(n, increment=0.1)

        x_domain = get_x_domain(n, increment=0.1)
        xaxis = get_x_axis_settings(n=1, domain=x_domain)

        update_recursively(self.layout, {**yaxis, **xaxis})

    def populate_traces(self, ids=None):
        units_y_dct = get_units_y_dct(self.all_units)
        kwargs = get_trace_settings(self.type_)

        for id_, points in self.raw_data.items():
            if not ids or id_ in ids:
                yaxis = units_y_dct[points.units]
                kwargs["yaxis"] = yaxis
                trace = trace2d(id_, self.item_id,
                                points.js_timestamp,
                                points.data,
                                points.name,
                                **kwargs)
                self.traces[id_] = trace

    def update_figure(self, update_dct):
        pass

    def set_legend_visibility(self, visible=True):
        self.layout["showlegend"] = visible

    def set_legend_y(self, div_height):
        h_trace = 19  # this depends on legend text size (px)
        gap = 10  # space between legend and chart (px)
        max_y = 2  # a maximum height ratio between legend and chart is 50/50

        n_traces = len(self.traces.keys())
        margin = self.layout["margin"]["t"] + self.layout["margin"]["b"]

        y = div_height - margin
        y1 = gap
        y2 = h_trace * n_traces

        y_norm0 = (y - y1 - y2) / y
        y_norm1 = (y1 / y) / y_norm0
        y_norm2 = (y2 / y) / y_norm0

        y_leg = 1 + y_norm1 + y_norm2

        self.layout["legend"]["y"] = max_y if max_y <= y_leg else y_leg
