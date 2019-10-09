import pandas as pd

from eso_reader.building_eso_file import averaged_units
from esopie.utils.utils import (get_str_identifier, update_recursively,
                                merge_dcts, remove_recursively)
from esopie.chart_settings import (get_xaxis_settings,
                                   get_yaxis_settings, get_trace_appearance,
                                   style, config, get_trace_settings,
                                   layout_dct, color_generator, get_units_axis_dct,
                                   gen_domain_matrices)


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


def calculate_totals(df):
    """ Calculate df sum or average (based on units). """
    units = df.columns.get_level_values("units")
    cnd = units.isin(averaged_units)

    avg_df = df.loc[:, cnd].mean()
    sum_df = df.loc[:, [not b for b in cnd]].sum()

    sr = pd.concat([avg_df, sum_df])
    drop = [nm for nm in sr.index.names if nm != "id"]
    sr.index = sr.index.droplevel(drop)

    return sr


def update_attr(attr_name):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            attr = self.__getattribute__(attr_name)

            out = func(self, *args, **kwargs)
            if isinstance(out, dict):
                update_recursively(attr, out)
                return out
            else:
                remove_recursively(attr, out[1])
                update_recursively(attr, out[0])
            return list(out)

        return wrapper

    return decorator


class Points:
    def __init__(self, name_tup, values, total_value, timestamp):
        self.name_tup = name_tup
        self.values = values
        self.total_value = total_value
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
    def interval(self):
        return self.name_tup[1]

    @property
    def key(self):
        return self.name_tup[2]

    @property
    def variable(self):
        return self.name_tup[3]

    @property
    def units(self):
        return self.name_tup[4]


class Chart:
    """
    A class to handle chart operation and to
    hold chart related data.

    """
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
        self.shared_axes = False
        self.color_gen = color_generator(0)

    @property
    def data(self):
        """ Get 'plotly' like trace data. """
        return list(self.traces.values())

    @property
    def figure(self):
        """ Get a base 'plotly' like figure. """
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

    def get_all_units(self):
        """ Get a list of all used units. """
        full = [points.units for points in self.raw_data.values()]
        setlist = []
        for e in full:
            if e not in setlist:
                setlist.append(e)
        return setlist

    def get_n_traces(self):
        """ Get a current number of traces. """
        return len(self.traces.keys())

    def get_all_ids(self):
        """ Get all displayed trace ids. """
        return list(self.traces.keys())

    def get_selected_ids(self):
        """ Get all currently selected trace ids. """
        return [tr["traceId"] for tr in self.data if tr["selected"]]

    def any_trace_selected(self):
        """ Check if there's at least one trace selected. """
        return any(map(lambda x: x["selected"], self.traces.values()))

    def process_data(self, df, auto_update=True):
        """ Process raw pd.DataFrame and store the data. """
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]
        totals_sr = calculate_totals(df)

        new_ids = []
        for col_ix, sr in df.iteritems():
            ids = self.raw_data.keys()
            id_ = get_str_identifier("trace", ids, start_i=1,
                                     delimiter="-", brackets=False)
            new_ids.append(id_)

            # ignore col_ix[1] as variable 'id' is not required
            name_tup = (col_ix[0], col_ix[2], col_ix[3], col_ix[4], col_ix[5])
            total_value = totals_sr.at[col_ix[1]]

            points = Points(name_tup, sr.tolist(), total_value, timestamps)
            self.raw_data[id_] = points

        if auto_update:
            return self.populate_traces(new_ids)

    @update_attr("traces")
    def update_all_traces_type(self, chart_type):
        """ Override a trace type for all traces. """
        settings = get_trace_settings(chart_type)
        update_dct = {}

        for trace_id in self.traces.keys():
            update_dct[trace_id] = settings

        return update_dct

    def update_chart_type(self, chart_type):
        """ Update the current chart type. """
        self.type_ = chart_type
        traces = self.update_all_traces_type(chart_type)
        return {"traces": traces, "chartType": chart_type}

    def delete_selected_traces(self):
        """ Remove currently selected traces. """
        orig_n_units = len(self.get_all_units())
        ids = self.get_selected_ids()
        for id_ in ids:
            del self.raw_data[id_]
            del self.traces[id_]

        new_n_units = len(self.get_all_units())
        traces = self.update_traces_appearance()
        if orig_n_units != new_n_units:
            dct = self.update_traces_axes()
            traces = merge_dcts(traces, dct)

        update_dct, remove_dct = self.update_layout()

        return (
            ids,
            {"traces": traces, "layout": update_dct},
            {"layout": remove_dct}
        )

    def get_top_margin(self):
        """ Calculate chart top margin. """
        n_traces = self.get_n_traces()
        if self.show_custom_legend:
            m = n_traces * self.LEGEND_TRACE_HEIGHT
            m = m if m <= self.LEGEND_MAX_HEIGHT else self.LEGEND_MAX_HEIGHT
        else:
            m = layout_dct["margin"]["t"]
        return m + self.LEGEND_GAP

    @update_attr("layout")
    def update_layout(self):
        """ Generate chart layout properties. """
        units = self.get_all_units()
        n = len(units)
        x_doms, y_doms = None, None

        if not self.shared_axes:
            x_doms, y_doms = gen_domain_matrices(units, max_columns=3,
                                                 gap=0.05, flat=True)

        yaxis = get_yaxis_settings(n, increment=0.08, titles=units,
                                   y_domains=y_doms)

        xaxis = get_xaxis_settings(n_yaxis=n, increment=0.08,
                                   x_domains=x_doms)

        margin = {"margin": {"t": self.get_top_margin()}}

        update_dct = {**yaxis, **xaxis, **margin}
        remove_dct = {}

        # clean up previous xaxis and yaxis assignment
        for k in self.layout.keys():
            if "yaxis" in k or "xaxis" in k:
                remove_dct[k] = None

        return update_dct, remove_dct

    @update_attr("traces")
    def update_traces_axes(self):
        """ Assign trace 'x' and 'y' axes (based on units). """
        update_dct = {}

        units = self.get_all_units()
        units_y_dct = get_units_axis_dct(units, axis="y")
        units_x_dct = get_units_axis_dct(units)

        for id_, trace in self.traces.items():
            yaxis = units_y_dct[trace["units"]]

            if self.shared_axes:
                xaxis = "x"
            else:
                xaxis = units_x_dct[trace["units"]]

            update_dct[id_] = {"yaxis": yaxis, "xaxis": xaxis}

        return update_dct

    @update_attr("traces")
    def add_traces(self, ids):
        """ Transform 'raw' trace objects for given ids.  """
        update_dct = {}
        dt = {k: v for k, v in self.raw_data.items() if k in ids}

        for id_, points in dt.items():
            color = next(self.color_gen)

            kwargs = get_trace_settings(self.type_)
            trace = trace2d(id_, self.item_id,
                            points.js_timestamp,
                            points.values,
                            points.name,
                            color,
                            selected=False,
                            units=points.units,
                            **kwargs)

            update_dct[id_] = trace

        return update_dct

    def populate_traces(self, ids):
        """ Create 'trace' object from raw data for given ids. """
        # create 'trace' objects and set appearance
        dct1 = self.add_traces(ids)
        dct2 = self.update_traces_appearance()
        dct3 = self.update_traces_axes()

        traces = merge_dcts(dct1, dct2, dct3)

        # update_layout returns 'update' and 'remove' dicts but since nothing
        # needs to be removed when adding traces, remove dct can be ignored
        layout, _ = self.update_layout()

        return {"traces": traces, "layout": layout}

    @update_attr("traces")
    def update_traces_appearance(self):
        """ Update trace visual settings. """
        all_ids = self.get_all_ids()

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

        update_dct = {}
        for k, v in appearance.items():
            for id_ in v:
                update_dct[id_] = get_trace_appearance(self.type_, k)

        return update_dct

    def handle_trace_selected(self, trace_id):
        """ Reverse 'selected' attribute for the given trace. """
        # reverse selected state of the clicked trace
        selected = not self.traces[trace_id]["selected"]

        dct1 = self.set_trace_selected(trace_id, selected)
        dct2 = self.update_traces_appearance()

        # dicts need to be updated recursively in order
        # to not override lower nested levels
        update_dct = merge_dcts(dct1, dct2)

        return update_dct

    @update_attr("traces")
    def set_trace_selected(self, trace_id, selected):
        """ Set 'selected' state for the given trace. """
        return {trace_id: {"selected": selected}}

    def set_legend_visibility(self, visible=True):
        self.show_custom_legend = visible
