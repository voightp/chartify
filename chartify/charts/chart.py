from chartify.charts.chart_functions import (get_axis_settings, pie_chart,
                                             create_2d_axis_map, set_axes_position)

from chartify.charts.chart_settings import (get_layout, base_layout,
                                            style, config)
from typing import Dict, Any
from chartify.utils.tiny_profiler import profile
from chartify.charts.trace import Axis


class Chart:
    """
    A class to handle chart operation and to
    hold chart related data.

    """
    LEGEND_MAX_HEIGHT = 100
    LEGEND_TRACE_HEIGHT = 19
    LEGEND_GAP = 20

    def __init__(self, item_id, chart_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.custom = False
        self.shared_axes = "x"  # 'x' | 'x+y' | ''
        self.group_datetime = True
        self.show_custom_legend = True
        self.ranges = {"x": {}, "y": {}, "z": {}}

    @property
    def shared_x(self):
        """ Check if datetime axis is shared for all intervals. """
        return self.shared_axes == "x" or self.shared_axes == "x+y"

    @property
    def shared_y(self):
        """ Check if 'y' axis should be shared or stacked. """
        return self.shared_axes == "x+y"

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

    def get_top_margin(self, n_traces):
        """ Set chart top margin. """
        if self.show_custom_legend and n_traces > 0:
            m = n_traces * self.LEGEND_TRACE_HEIGHT
            m = m if m <= self.LEGEND_MAX_HEIGHT else self.LEGEND_MAX_HEIGHT
        else:
            m = base_layout["margin"]["t"]

        return m + self.LEGEND_GAP

    @profile
    def generate_layout_axes(self, chart_type, axes_map, line_color, grid_color):
        """ Generate chart layout properties. """
        x_axes, y_axes = {}, {}
        annotations = []

        if not axes_map:
            # assign dummy axes to plot nice default chart layout
            axes_map = [(Axis("x", ""), Axis("y", ""))]

        for xaxis, yaxis in axes_map:
            y_axes.update(get_axis_settings(chart_type, yaxis, line_color,
                                            grid_color, ranges=self.ranges["y"]))

            x_axes.update(get_axis_settings(chart_type, xaxis, line_color,
                                            grid_color, ranges=self.ranges["x"]))

            annotations.extend(xaxis.get_title_annotations())
            annotations.extend(yaxis.get_title_annotations())

        return {**x_axes, **y_axes}, annotations

    @profile
    def as_plotly(self, traces, modebar_active_color, modebar_color,
                  line_color, grid_color, background_color):
        """ Create 'plotly' like chart. """
        # assign priority to set an appearance for each trace
        self.set_trace_priority(traces)

        # copy layout to avoid overriding base parameters
        top_margin = self.get_top_margin(len(traces))
        layout = get_layout(self.type_, top_margin, modebar_active_color,
                            modebar_color)

        if self.type_ == "pie":
            axes, annotations = {}, []
            data = pie_chart(traces, background_color,
                             max_columns=3, square=True, gap=0.05)
        else:
            axes_map = create_2d_axis_map(traces, self.group_datetime, self.shared_x)
            set_axes_position(axes_map, self.shared_x, self.shared_y,
                              max_columns=3, gap=0.05, square=True,
                              stacked_y_gap=0.02, shared_x_gap=0.08,
                              shared_y_gap=0.08)

            axes, annotations = self.generate_layout_axes(self.type_, axes_map,
                                                          line_color, grid_color)
            data = [trace.as_plotly() for trace in traces]

        return {
            "componentType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "sharedAxes": self.shared_axes,
            "chartType": self.type_,
            "divId": self.chart_id,
            "layout": {
                **layout, **axes,
                "annotations": annotations
            },
            "data": data,
            "style": style,
            "config": config,
            "useResizeHandler": True
        }
