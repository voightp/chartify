import copy

from esopie.utils.utils import get_str_identifier, update_recursively
from esopie.chart_settings import (get_x_domain, get_x_axis_settings,
                                   get_y_axis_settings, get_trace_appearance,
                                   style, config, get_trace_settings,
                                   layout_dct, color_generator, get_units_y_dct)


def assign_color(dct, color):
    try:
        dct["marker"]["color"] = color
    except KeyError:
        dct["marker"] = {"color": color}


def trace2d(trace_id, item_id, x, y, name, color, **kwargs):
    dct = {
        "traceId": trace_id,
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
    LEGEND_TRACE_HEIGHT = 19
    LEGEND_GAP = 10

    def __init__(self, chart_id, item_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.raw_data = {}
        self.traces = {}
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

    def get_n_traces(self):
        return len(self.traces.keys())

    def any_trace_selected(self):
        return any(map(lambda x: x["selected"], self.traces.values()))

    def process_data(self, df):
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]
        ids = self.raw_data.keys()
        new_ids = []

        for col_ix, sr in df.iteritems():
            id_ = get_str_identifier("trace", ids, start_i=1,
                                     delimiter="-", brackets=False)
            new_ids.append(id_)
            self.raw_data[id_] = Points(col_ix, sr.tolist(), timestamps)

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

    def get_top_margin(self):
        n_traces = self.get_n_traces()
        if self.show_custom_legend:
            m = n_traces * self.LEGEND_TRACE_HEIGHT
            m = m if m <= self.LEGEND_MAX_HEIGHT else self.LEGEND_MAX_HEIGHT
        else:
            m = layout_dct["margin"]["t"]
        return m + self.LEGEND_GAP

    def populate_layout(self):
        n = len(self.all_units)
        yaxis = get_y_axis_settings(n, increment=0.05)

        x_domain = get_x_domain(n, increment=0.05)
        xaxis = get_x_axis_settings(n=1, domain=x_domain)

        m = self.get_top_margin()
        margin = {"margin": {"t": m}}

        update_recursively(self.layout, {**yaxis, **xaxis, **margin})

    def populate_traces(self, ids=None):
        units_y_dct = get_units_y_dct(self.all_units)
        settings = get_trace_settings(self.type_)

        dt = {k: v for k, v in self.raw_data.items() if k in ids}

        for id_, points in dt.items():
            yaxis = units_y_dct[points.units]
            color = next(self.color_gen)

            # further keyword modifications could mutate the data
            kwargs = copy.deepcopy(settings)
            kwargs["yaxis"] = yaxis
            kwargs["selected"] = False

            trace = trace2d(id_, self.item_id,
                            points.js_timestamp,
                            points.data,
                            points.name,
                            color,
                            **kwargs)

            self.traces[id_] = trace

    def handle_trace_selected(self, trace_id):
        update_dct = {}
        all_ids = self.traces.keys()
        trace = self.traces[trace_id]
        trace["selected"] = not trace["selected"]

        appearance = {
            "high": [],
            "normal": [],
            "low": []
        }

        if not self.any_trace_selected():
            # all traces should appear as normal
            appearance["normal"] = all_ids
        else:
            for id_ in all_ids:
                if self.traces[id_]["selected"]:
                    appearance["high"].append(id_)
                else:
                    appearance["low"].append(id_)

        for k, v in appearance.items():
            a = get_trace_appearance(self.type_, k)
            for id_ in v:
                update_dct[id_] = a

        update_dct[trace_id]["selected"] = trace["selected"]
        update_recursively(self.traces, update_dct)

        return update_dct

    def update_figure(self, update_dct):
        pass

    def set_legend_visibility(self, visible=True):
        self["showCustomLegend"] = visible
