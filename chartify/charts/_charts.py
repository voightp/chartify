import pandas as pd

from eso_reader.building_eso_file import averaged_units
from chartify.charts.trace import Trace, plot_pie_chart
from chartify.utils.utils import (get_str_identifier, update_recursively,
                                  merge_dcts, remove_recursively)
from chartify.charts.chart_settings import (get_xaxis_settings, get_yaxis_settings,
                                            style, config, layout_dct, color_generator,
                                            get_units_axis_dct, gen_dom_matrices, STATISTICAL_CHARTS, ONE_DIM_CHARTS)


def calculate_totals(df):
    """ Calculate df sum or average (based on units). """
    units = df.columns.get_level_values("units")
    cnd = units.isin(averaged_units)

    avg_df = df.loc[:, cnd].mean()
    sum_df = df.loc[:, [not b for b in cnd]].sum()

    sr = pd.concat([avg_df, sum_df])

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


    def __init__(self, chart_id, item_id, palette, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.palette = palette
        self.type_ = type_
        self.traces = []
        self.trace_ids = []
        self.layout = layout_dct
        self.show_custom_legend = True
        self.shared_axes = False
        self.color_gen = color_generator(0)

    @property
    def figure(self):
        """ Get a base 'plotly' like figure. """
        return {
            "itemType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": self.layout,
            "data": [],
            "style": style,
            "config": config,
            "useResizeHandler": True
        }

    @update_attr("layout")
    def set_layout_colors(self, palette):
        """ Apply specific color scheme to the chart layout. """
        c1 = palette.get_color("PRIMARY_COLOR")
        c2 = palette.get_color("PRIMARY_COLOR", 0.3)
        update_dct = {}
        for k, v in self.layout.items():
            if "axis" in k:
                update_dct[k] = {
                    "color": c1,
                    "linecolor": c1,
                    "gridcolor": c2,
                    "zerolinecolor": c1
                }
        return update_dct

    def get_trace(self, trace_id):
        """ Return traces  for given id. """
        if "#" in trace_id:
            # pie charts are treated as grouped traces
            trace_ids = trace_id.split("#")
        else:
            trace_ids = [trace_id]

        traces = [tr for tr in self.traces if tr.trace_id in trace_ids]

        if not traces:
            raise ValueError("TRACE MISSING: " + trace_id)

        if len(traces) == 1:
            return traces[0]

        return traces

    def get_n_traces(self):
        """ Get a current number of traces. """
        return len(self.traces)

    def get_selected_ids(self):
        """ Get all currently selected trace ids. """
        return [tr.trace_id for tr in self.traces if tr.selected]

    def gen_id(self):
        """ Generate unique trace id. """
        all_ids = [tr.trace_id for tr in self.traces]
        return get_str_identifier("trace", all_ids, start_i=1,
                                  delimiter="-", brackets=False)

    def plot_chart(self, traces=None):
        """ Create data required to update chart. """
        traces = traces if traces else self.traces

        if self.type_ in ONE_DIM_CHARTS:
            # clean up all previously displayed charts
            rm_ids = self.trace_ids[:]

            # pass all traces as it's required to generate
            # completely new traces dict
            traces_dct = self.plot_traces(self.traces)

        else:
            # create 'plotly' like dict traces and update axes
            # as assigned axes depend on all displayed units
            traces_dct = merge_dcts(self.plot_traces(traces),
                                    self.set_trace_axes(traces))

            # remove pie chart traces if these were previously assigned
            all_ids = set([tr.trace_id for tr in self.traces])
            rm_ids = list(set(self.trace_ids).difference(all_ids))

        self.trace_ids = list(traces_dct.keys())

        upd_dct = {"traces": traces_dct,
                   "layout": self.update_layout()}

        rm_dct = {"traces": self.clean_up_traces(),
                  "layout": self.clean_up_layout()}

        upd_dct = {k: v for k, v in upd_dct.items() if v}
        rm_dct = {k: v for k, v in rm_dct.items() if v}

        return upd_dct, rm_dct, rm_ids

    def process_data(self, df):
        """ Process raw pd.DataFrame and store the data. """
        totals_sr = calculate_totals(df)
        timestamps = [dt.timestamp() for dt in df.index.to_pydatetime()]

        new_traces = []
        for col_ix, val_sr in df.iteritems():
            trace_id = self.gen_id()

            # channel cannot handle numpy.float
            total_value = float(totals_sr.loc[col_ix])

            # create a new color to distinguish traces and set emphasis
            color = next(self.color_gen)
            priority = "low" if self.any_trace_selected() else "normal"

            args = (self.item_id, trace_id, col_ix, val_sr.tolist(),
                    total_value, timestamps, color)
            kwargs = {"priority": priority, "type_": self.type_}

            trace = Trace(*args, **kwargs)

            new_traces.append(trace)
            self.traces.append(trace)

        return self.plot_chart(new_traces)

    def clean_up_traces(self):
        """ Remove redundant chart attributes. """
        remove_dct = {}

        if self.type_ in STATISTICAL_CHARTS:
            # clean up 'x' - passing none will remove all 'x' data
            for trace_id in self.trace_ids:
                remove_dct[trace_id] = {"x": None}

        return remove_dct

    def update_chart_type(self, chart_type):
        """ Update the current chart type. """
        self.type_ = chart_type

        for trace in self.traces:
            trace.type_ = chart_type

        return self.plot_chart()

    def delete_selected_traces(self):
        """ Remove currently selected traces. """
        ids = self.get_selected_ids()

        for trace_id in ids:
            trace = self.get_trace(trace_id)
            self.traces.remove(trace)

        return self.plot_chart()

    @update_attr("layout")
    def clean_up_layout(self):
        """ clean up previous xaxis and yaxis assignment. """
        remove_dct = {}
        for k in self.layout.keys():
            if "yaxis" in k or "xaxis" in k:
                remove_dct[k] = None
        return remove_dct

    def handle_trace_selected(self, trace_id):
        """ Reverse 'selected' attribute for the given trace. """
        trace = self.get_trace(trace_id)

        if self.type_ in ONE_DIM_CHARTS and isinstance(trace, list):
            for tr in trace:
                tr.selected = not tr.selected

            selected = all(map(lambda x: x.selected, trace))
            trace_dct1 = {trace_id: {"opacity": 1 if selected else 0.7}}

        else:
            selected = not trace.selected
            trace.selected = selected

            is_normal = not self.any_trace_selected()
            trace_dct1 = self.set_trace_emphasis(normal=is_normal)

        trace_dct2 = {trace_id: {"selected": selected}}

        # dicts need to be updated recursively in order
        # to not override lower nested levels
        update_dct = merge_dcts(trace_dct1,
                                trace_dct2)

        return {"traces": update_dct}

    def set_legend_visibility(self, visible=True):
        self.show_custom_legend = visible
