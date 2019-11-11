from chartify.charts.chart_settings import *


def plot_pie_chart(traces, background_color):
    """ Plot a 'special' pie chart data. """
    groups = group_by_units(traces)
    x_doms, y_doms = gen_dom_matrices(groups.keys(), max_columns=3, gap=0,
                                      flat=True, is_square=True)
    data = []
    for x_dom, y_dom, traces in zip(x_doms, y_doms, groups.values()):
        values, labels, colors, trace_ids, priorities = combine_traces(traces)
        data.append({
            "type": "pie",
            "opacity": 1,
            "itemId": traces[0].item_id,
            "traceIds": trace_ids,
            "pull": 0,
            "hole": 0,
            "values": values,
            "labels": labels,
            "domain": {
                "x": x_dom,
                "y": y_dom
            },
            **get_pie_appearance(priorities, colors, background_color)
        })

    return data


def plot_2d_chart(traces, type_="scatter", custom=False):
    """ Plot a 'standard' 2d chart of a given type. """
    data = []
    for trace in traces:
        type_ = trace.type_ if custom else type_
        data.append({**get_appearance(type_, trace.color, trace.priority),
                     **get_shared_attributes(trace.item_id, trace.trace_id,
                                             trace.name, trace.color),
                     **get_axis_inputs(type_, trace.values, trace.js_timestamps,
                                       trace.xaxis, trace.yaxis)})
    return data


class Chart:
    LEGEND_MAX_HEIGHT = 100
    LEGEND_TRACE_HEIGHT = 19
    LEGEND_GAP = 10

    def __init__(self, chart_id, item_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.custom = False
        self.shared_axes = False
        self.show_custom_legend = True

    def set_trace_axes(self, traces, shared_axes):
        """ Assign trace 'x' and 'y' axes (based on units). """
        units = get_all_units(traces)
        units_x_dct = get_units_axis_dct(units, axis="x")
        units_y_dct = get_units_axis_dct(units, axis="y")

        for trace in traces:
            yaxis = units_y_dct[trace.units]

            if shared_axes:
                xaxis = "x"
            else:
                xaxis = units_x_dct[trace.units]

            trace.xaxis = xaxis
            trace.yaxis = yaxis

    def set_trace_priority(self, traces):
        """ Set emphasised trace appearance. """
        all_normal = all(map(lambda x: not x.selected, traces))
        for trace in traces:
            if all_normal:
                trace.priority = "normal"
            elif trace.selected:
                trace.priority = "high"
            else:
                trace.priority = "low"

    def generate_data(self, traces, background_color):
        if self.type_ in ["pie", "histogram", "box"]:
            self.shared_axes = False

        self.set_trace_axes(traces, self.shared_axes)
        self.set_trace_priority(traces)

        if self.type_ == "pie":
            data = plot_pie_chart(traces, background_color)
        else:
            data = plot_2d_chart(traces)

        return data

    def set_top_margin(self, layout, n_traces):
        """ Set chart top margin. """
        if self.show_custom_legend:
            m = n_traces * self.LEGEND_TRACE_HEIGHT
            m = m if m <= self.LEGEND_MAX_HEIGHT else self.LEGEND_MAX_HEIGHT
        else:
            m = layout_dct["margin"]["t"]

        layout["margin"]["t"] = m + self.LEGEND_GAP

    def generate_layout(self, n_traces, units, grid_color1, grid_color2):
        """ Generate chart layout properties. """
        layout = copy.deepcopy(layout_dct)
        self.set_top_margin(layout, n_traces)

        if self.type_ != "pie":
            # pie chart does not require x, y axes
            if self.shared_axes:
                x_doms, y_doms = None, None
            else:
                x_doms, y_doms = gen_dom_matrices(units, max_columns=3, gap=0.05,
                                                  flat=True, is_square=True)

            yaxis = get_yaxis_settings(len(units), grid_color1, grid_color2,
                                       increment=0.08, titles=units,
                                       y_domains=y_doms)

            xaxis = get_xaxis_settings(len(yaxis.keys()), grid_color1, grid_color2,
                                       increment=0.08, x_domains=x_doms,
                                       chart_type=self.type_)
        else:
            xaxis, yaxis = {}, {}

        return {**layout, **yaxis, **xaxis}

    def plot_chart(self, traces, grid_color1, grid_color2, background_color):
        data = self.generate_data(traces, background_color)
        layout = self.generate_layout(len(traces), get_all_units(traces),
                                      grid_color1, grid_color2)

        return {
            "itemType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": layout,
            "data": data,
            "style": style,
            "config": config,
            "useResizeHandler": True
        }
