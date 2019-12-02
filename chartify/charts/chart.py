from chartify.charts.chart_settings import *
from eso_reader.constants import *


def plot_pie_chart(traces, background_color):
    """ Plot a 'special' pie chart data. """
    groups = group_by_units(traces)
    x_doms, y_doms = gen_domain_vectors(groups.keys(), max_columns=3, gap=0.05,
                                        square=True)
    data = []
    for x_dom, y_dom, traces in zip(x_doms, y_doms, groups.values()):
        (values, labels, colors, trace_ids,
         priorities, selected) = combine_traces(traces)

        data.append({
            "type": "pie",
            "opacity": 1,
            "itemId": traces[0].item_id,
            "traceIds": trace_ids,
            "pull": [0.1 if tr.selected else 0 for tr in traces],
            "hole": 0.3,
            "values": values,
            "labels": labels,
            "selected": selected,
            "domain": {
                "x": x_dom,
                "y": y_dom
            },
            **get_pie_appearance(priorities, colors, background_color)
        })

    return data


def plot_2d_chart(traces, type_="scatter"):
    """ Plot a 'standard' 2d chart of a given type. """
    data = []
    for trace in traces:
        type_ = trace.type_ if type_ == "custom" else type_
        data.append({
            "itemId": trace.item_id,
            "traceId": trace.trace_id,
            "name": trace.name,
            "color": trace.color,
            "selected": trace.selected,
            "hoverlabel": {
                "namelength": -1,
            },
            **get_appearance(type_, trace.color, trace.priority),
            **get_axis_inputs(type_, trace.values, trace.js_timestamps,
                              trace.xaxis, trace.yaxis)})
    return data


class Chart:
    """
    A class to handle chart operation and to
    hold chart related data.

    """
    LEGEND_MAX_HEIGHT = 100
    LEGEND_TRACE_HEIGHT = 19
    LEGEND_GAP = 10

    def __init__(self, item_id, chart_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.custom = False
        self.shared_axes = "x"  # 'x' | 'x+y' | ''
        self.show_custom_legend = True
        self.ranges = {"x": {}, "y": {}, "z": {}}

    @staticmethod
    def set_trace_priority(traces):
        """ Set emphasised trace appearance. """
        all_normal = all(map(lambda x: not x.selected, traces))
        for trace in traces:
            if all_normal:
                trace.priority = "normal"
            elif trace.selected:
                trace.priority = "high"
            else:
                trace.priority = "low"

    def set_trace_axes(self, traces, xaxes, yaxes):
        """ Assign trace 'x' and 'y' axes (based on units). """
        for trace in traces:
            if not self.shared_axes:
                trace.xaxis = xaxes[trace.units][trace.interval]
            else:
                trace.xaxis = xaxes[trace.interval]

            trace.yaxis = yaxes[trace.units]

    def generate_data(self, traces, xaxes, yaxes, background_color):
        """ Generate chart data (traces). """
        data = []
        if self.type_ in ["pie", "histogram", "box"]:
            self.shared_axes = False

        if traces:
            self.set_trace_axes(traces, xaxes, yaxes)
            self.set_trace_priority(traces)

            if self.type_ == "pie":
                data = plot_pie_chart(traces, background_color)
            else:
                data = plot_2d_chart(traces, type_=self.type_)

        return data

    def set_top_margin(self, layout, n_traces):
        """ Set chart top margin. """
        if self.show_custom_legend:
            m = n_traces * self.LEGEND_TRACE_HEIGHT
            m = m if m <= self.LEGEND_MAX_HEIGHT else self.LEGEND_MAX_HEIGHT
        else:
            m = base_layout["margin"]["t"]

        layout["margin"]["t"] = m + self.LEGEND_GAP

    def generate_layout(self, n_traces, xaxes_ref, yaxes_ref, units,
                        line_color, grid_color):
        """ Generate chart layout properties. """
        layout = copy.deepcopy(base_layout)
        self.set_top_margin(layout, n_traces)

        if self.shared_axes:
            x_domains, y_domains = None, None
        else:
            x_domains, y_domains = gen_domain_vectors(units, max_columns=3,
                                                      gap=0.05, square=True)

        y_axes = get_yaxis_settings(len(units), line_color, grid_color,
                                    titles=units, y_domains=y_domains,
                                    increment=0.08, ranges_y=self.ranges["y"])

        date_axis = self.type_ in ["scatter", "bar", "bubble", "line"]
        x_axes = get_xaxis_settings(len(y_axes.keys()), line_color, grid_color,
                                    increment=0.08, x_domains=x_domains,
                                    date_axis=date_axis, ranges_x=self.ranges["x"])

        return {**layout, **y_axes, **x_axes}

    def as_plotly(self, traces, line_color, grid_color, background_color):
        """ Create 'plotly' like chart. """
        if self.shared_axes == "x":
            shared_x = True
            shared_y = False
        elif self.shared_axes == "x+y":
            shared_x = True
            shared_y = True
        else:
            shared_x = False
            shared_y = False

        xaxes, yaxes, xaxes_ref, yaxes_ref = get_axis_map(traces, shared_x, shared_y)
        data = self.generate_data(traces, xaxes, yaxes, background_color)
        layout = self.generate_layout(len(traces), xaxes_ref, yaxes_ref, units,
                                      line_color, grid_color)
        return {
            "componentType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "sharedAxes": self.shared_axes,
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": layout,
            "data": data,
            "style": style,
            "config": config,
            "useResizeHandler": True
        }
