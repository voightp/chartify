import pandas as pd

from eso_reader.building_eso_file import averaged_units
from esopie.trace import RawTrace
from esopie.utils.utils import (get_str_identifier, update_recursively,
                                merge_dcts, remove_recursively)
from esopie.chart_settings import (get_xaxis_settings, get_yaxis_settings,
                                   style, config, layout_dct, color_generator,
                                   get_units_axis_dct, gen_domain_matrices)


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
        self.raw_traces = {}
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
        full = [points.units for points in self.raw_traces.values()]
        setlist = []
        for e in full:
            if e not in setlist:
                setlist.append(e)
        return setlist

    def get_n_traces(self):
        """ Get a current number of traces. """
        return len(self.raw_traces.keys())

    def get_all_ids(self):
        """ Get all displayed trace ids. """
        return list(self.raw_traces.keys())

    def get_selected_ids(self):
        """ Get all currently selected trace ids. """
        return [tr.trace_id for tr in self.raw_traces.values() if tr.selected]

    def any_trace_selected(self):
        """ Check if there's at least one trace selected. """
        return any(map(lambda x: x.selected, self.raw_traces.values()))

    def process_data(self, df):
        """ Process raw pd.DataFrame and store the data. """
        totals_sr = calculate_totals(df)
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]

        new_traces = {}
        for col_ix, sr in df.iteritems():
            ids = self.get_all_ids()
            trace_id = get_str_identifier("trace", ids, start_i=1,
                                          delimiter="-", brackets=False)
            values = sr.tolist()
            info = list(col_ix)
            id_ = info.pop(1)
            total_value = totals_sr.at[id_]
            priority = "low" if self.any_trace_selected() else "normal"

            args = (self.item_id, trace_id, tuple(info), values,
                    total_value, timestamps, next(self.color_gen))
            kwargs = {"priority": priority}

            trace = RawTrace(*args, **kwargs)
            new_traces[trace_id] = trace
            self.raw_traces[trace_id] = trace

        # create 'plotly' like dict traces and update axes
        # as assigned axes depend on all displayed units
        traces_dct1 = self.plot_traces(new_traces)
        traces_dct2 = self.set_trace_axes(new_traces)

        traces = merge_dcts(traces_dct1, traces_dct2)

        # update_layout returns 'update' and 'remove' dicts
        # but since nothing needs to be removed when adding
        # traces, remove dct can be ignored
        layout, _ = self.update_layout()

        return {"traces": traces, "layout": layout}

    def update_chart_type(self, chart_type):
        """ Update the current chart type. """
        self.type_ = chart_type

        for trace in self.raw_traces.values():
            trace.type_ = chart_type

        traces = self.plot_traces(self.raw_traces)
        return {"traces": traces, "chartType": chart_type}

    def delete_selected_traces(self):
        """ Remove currently selected traces. """
        orig_n_units = len(self.get_all_units())
        ids = self.get_selected_ids()
        for id_ in ids:
            del self.raw_traces[id_]
            del self.traces[id_]

        # TODO handle situation when the chart is empty
        all_traces = self.raw_traces
        trace_dct = self.set_normal_appearance(all_traces)
        if orig_n_units != len(self.get_all_units()):
            dct = self.set_trace_axes(all_traces)
            trace_dct = merge_dcts(trace_dct, dct)

        update_dct, remove_dct = self.update_layout()

        return (
            ids,
            {"traces": trace_dct, "layout": update_dct},
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
    def set_trace_axes(self, raw_traces):
        """ Assign trace 'x' and 'y' axes (based on units). """
        update_dct = {}

        units = self.get_all_units()
        units_x_dct = get_units_axis_dct(units, axis="x")
        units_y_dct = get_units_axis_dct(units, axis="y")

        for trace_id, trace in raw_traces.items():
            yaxis = units_y_dct[trace.units]

            if self.shared_axes:
                xaxis = "x"
            else:
                xaxis = units_x_dct[trace.units]

            trace.xaxis = xaxis
            trace.yaxis = yaxis

            update_dct[trace_id] = {"yaxis": yaxis, "xaxis": xaxis}

        return update_dct

    @update_attr("traces")
    def plot_traces(self, raw_traces):
        """ Transform 'raw' trace objects into 'plotly' dicts. """
        return {k: v.pl_trace() for k, v in raw_traces.items()}

    @update_attr("traces")
    def set_normal_appearance(self, raw_traces):
        """ Reset trace visual appearance to 'normal'. """
        update_dct = {}

        for trace_id, trace in raw_traces.items():
            out = trace.set_priority("normal")
            if out:
                update_dct[trace_id] = out

        return update_dct

    @update_attr("traces")
    def set_emph_appearance(self, raw_traces):
        """ Set emphasised trace appearance. """
        update_dct = {}

        for trace_id, trace in raw_traces.items():
            if trace.selected:
                pr = "high"
            else:
                pr = "low"
            out = trace.set_priority(pr)
            if out:
                update_dct[trace_id] = out

        return update_dct

    def handle_trace_selected(self, trace_id):
        """ Reverse 'selected' attribute for the given trace. """
        # reverse selected state of the clicked trace
        all_traces = self.raw_traces
        trace = self.raw_traces[trace_id]
        selected = not trace.selected
        trace.selected = selected

        if not self.any_trace_selected():
            # trace has been deselected and there
            # is no other trace selected
            trace_dct1 = self.set_normal_appearance(all_traces)
        else:
            # all traces weren't selected but the one clicked
            trace_dct1 = self.set_emph_appearance(all_traces)

        trace_dct2 = self.set_trace_selected(trace_id, selected)

        # dicts need to be updated recursively in order
        # to not override lower nested levels
        update_dct = merge_dcts(trace_dct1, trace_dct2)

        return update_dct

    @update_attr("traces")
    def set_trace_selected(self, trace_id, selected):
        """ Set 'selected' state for the given trace. """
        return {trace_id: {"selected": selected}}

    def set_legend_visibility(self, visible=True):
        self.show_custom_legend = visible
