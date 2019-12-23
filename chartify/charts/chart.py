from chartify.charts.chart_functions import (get_axis_settings, pie_chart,
                                             create_2d_axis_map, set_axes_position)

from chartify.charts.chart_settings import get_layout, style, config
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

    CHART_GAP = 25
    STACKED_Y_GAP = 20
    SHARED_X_GAP = 50
    SHARED_Y_GAP = 50
    N_COLUMNS = 3
    DEFAULT_RATIO = (0.001, 0.003)

    TOP_MARGIN = 20
    BOTTOM_MARGIN = 50
    LEFT_MARGIN = 50
    RIGHT_MARGIN = 50

    def __init__(self, item_id, chart_id, type_="scatter"):
        self.chart_id = chart_id
        self.item_id = item_id
        self.type_ = type_
        self.custom = False
        self.shared_x = False
        self.shared_y = True
        self.group_datetime = True
        self.show_custom_legend = True
        self.ranges = {"x": {}, "y": {}, "z": {}}
        self.geometry = {"w": -1, "h": -1}

    @staticmethod
    def to_ratio(px, ratio):
        """ Normalize pixels to ratio. """
        return px * ratio

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

    def get_ratio_per_pixel(self, top_margin: float):
        """ Calculate coefficient to transform pixels to domain position. """
        w = self.geometry["w"]
        h = self.geometry["h"]

        if w > 0 and h > 0:
            net_w = self.geometry["w"] - (self.LEFT_MARGIN + self.RIGHT_MARGIN)
            net_h = self.geometry["h"] - (top_margin + self.BOTTOM_MARGIN)

            h_ratio = 1 / net_w
            v_ratio = 1 / net_h

            return h_ratio, v_ratio
        else:
            return None

    def get_top_margin(self, n_traces):
        """ Set chart top margin. """
        if self.show_custom_legend and n_traces > 0:
            m = n_traces * self.LEGEND_TRACE_HEIGHT
            m = m if m <= self.LEGEND_MAX_HEIGHT else self.LEGEND_MAX_HEIGHT
            m = m + self.LEGEND_GAP
        else:
            m = self.TOP_MARGIN

        return m if m >= self.TOP_MARGIN else self.TOP_MARGIN

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

            annotations.extend(xaxis.get_title_annotations(line_color))
            annotations.extend(yaxis.get_title_annotations(line_color))

        return {**x_axes, **y_axes}, annotations

    @profile
    def as_plotly(self, traces, modebar_active_color, modebar_color,
                  line_color, grid_color, background_color):
        """ Create 'plotly' like chart. """
        # assign priority to set an appearance for each trace
        self.set_trace_priority(traces)

        top_margin = self.get_top_margin(len(traces))
        layout = get_layout(self.type_, modebar_active_color, modebar_color,
                            top_margin, self.BOTTOM_MARGIN, self.LEFT_MARGIN,
                            self.RIGHT_MARGIN)

        # convert pixels to chart relative ratios
        ratio = self.get_ratio_per_pixel(top_margin)
        h_ratio, v_ratio = ratio if ratio else self.DEFAULT_RATIO
        h_gap = self.CHART_GAP * h_ratio
        v_gap = self.CHART_GAP * v_ratio
        stacked_y_gap = self.STACKED_Y_GAP * v_ratio
        shared_x_gap = self.SHARED_X_GAP * v_ratio
        shared_y_gap = self.SHARED_Y_GAP * h_ratio

        if self.type_ == "pie":
            axes, annotations = self.generate_layout_axes(self.type_, [],
                                                          line_color, grid_color)
            data = pie_chart(traces, background_color, max_columns=self.N_COLUMNS,
                             square=True, v_gap=v_gap, h_gap=h_gap)
        else:
            axes_map = create_2d_axis_map(traces, self.group_datetime, self.shared_x)
            set_axes_position(axes_map, self.shared_x, self.shared_y,
                              max_columns=self.N_COLUMNS, v_gap=v_gap, h_gap=h_gap,
                              square=True, stacked_y_gap=stacked_y_gap,
                              shared_x_gap=shared_x_gap, shared_y_gap=shared_y_gap)
            data = [trace.as_plotly() for trace in traces]
            axes, annotations = self.generate_layout_axes(self.type_, axes_map,
                                                          line_color, grid_color)
        return {
            "componentType": "chart",
            "showCustomLegend": self.show_custom_legend,
            "sharedX": self.shared_x,
            "sharedY": self.shared_y,
            "groupDatetime": self.group_datetime,
            "chartType": self.type_,
            "divId": self.chart_id,
            "geometry": self.geometry,
            "layout": {
                **layout, **axes,
                "annotations": annotations
            },
            "data": data,
            "style": style,
            "config": config,
            "useResizeHandler": True
        }
