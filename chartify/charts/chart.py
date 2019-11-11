from chartify.charts.chart_settings import (get_xaxis_settings, get_yaxis_settings,
                                            style, config, layout_dct, color_generator,
                                            get_units_axis_dct, gen_dom_matrices,
                                            STATISTICAL_CHARTS, ONE_DIM_CHARTS)


def get_all_units(traces):
    """ Get a list of all used units. """
    full = [tr.units for tr in traces]
    setlist = []
    for e in full:
        if e not in setlist:
            setlist.append(e)
    return setlist


class Chart:
    def __init__(self, chart_id, item_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.show_custom_legend = True
        self.shared_axes = False

    def set_trace_axes(self, traces):
        """ Assign trace 'x' and 'y' axes (based on units). """
        units = get_all_units(traces)
        units_x_dct = get_units_axis_dct(units, axis="x")
        units_y_dct = get_units_axis_dct(units, axis="y")

        for trace in traces:
            yaxis = units_y_dct[trace.units]

            if self.shared_axes:
                xaxis = "x"
            else:
                xaxis = units_x_dct[trace.units]

            trace.xaxis = xaxis
            trace.yaxis = yaxis

    def set_trace_priority(self, traces, normal=True):
        """ Set emphasised trace appearance. """
        for trace in traces:
            if normal:
                p = "normal"
            elif trace.selected:
                p = "high"
            else:
                p = "low"
            trace.priority = p

    def generate_data(self, traces):
        all_normal = all(map(lambda x: not x.selected, traces))
        self.set_trace_priority(traces, normal=all_normal)

        self.set_trace_axes(traces)

        data =

    def generate_layout(self):
        pass

    def plot_chart(self, traces, grid_color1, grid_color2):
        return {
            "itemType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": layout,
            "data": [],
            "style": style,
            "config": config,
            "useResizeHandler": True
        }
