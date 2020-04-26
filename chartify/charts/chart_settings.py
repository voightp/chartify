from esofile_reader.constants import *

from chartify.ui.icons import combine_colors
from chartify.utils.css_theme import parse_color


def get_pie_trace_appearance(priorities, colors, background_color):
    weights = {"low": 0.3, "normal": 0.7, "high": 1}
    if isinstance(background_color, str):
        background_color = parse_color(background_color)

    new_colors = []
    for p, c in zip(priorities, colors):
        if isinstance(c, str):
            c = parse_color(c)
        new_colors.append(combine_colors(c, background_color, weights[p]))

    return {
        "marker": {"colors": new_colors,},
    }


def get_2d_trace_appearance(type_, color, interval, priority="normal"):
    weights = {
        "low": {"markerSize": 2, "lineWidth": 1, "opacity": 0.3},
        "normal": {"markerSize": 3, "lineWidth": 2, "opacity": 0.7},
        "high": {"markerSize": 4, "lineWidth": 2, "opacity": 1},
    }

    line_shape = {
        None: "linear",
        TS: "linear",
        H: "linear",
        D: "hvh",
        M: "hvh",
        A: "hvh",
        RP: "hvh",
    }

    shared = {
        "opacity": weights[priority]["opacity"],
        "hoverlabel": {"namelength": -1,},
    }

    props = {
        "scatter": {
            "type": "scattergl",
            "mode": "markers",
            "hoverinfo": "all",
            "marker": {
                "size": weights[priority]["markerSize"],
                "color": color,
                "symbol": "circle",
            },
        },
        "line": {
            "type": "scattergl",
            "mode": "lines+markers",
            "hoverinfo": "all",
            "marker": {
                "size": weights[priority]["markerSize"],
                "color": color,
                "symbol": "circle",
            },
            "line": {
                "width": weights[priority]["lineWidth"],
                "color": color,
                "shape": line_shape[
                    interval
                ],  # "linear" | "spline" | "hv" | "vh" | "hvh" | "vhv"
            },
        },
        "bar": {"type": "bar", "hoverinfo": "all", "marker": {"color": color}},
        "bubble": {},
        "histogram": {
            "type": "histogram",
            "hoverinfo": "x+y",
            "histfunc": "count",  # "count" | "sum" | "avg" | "min" | "max"
            "histnorm": "percent",  # "" | "percent" | "probability" | "density" | "probability density""
            "marker": {"color": color},
        },
        "box": {
            "type": "box",
            "hoverinfo": "name+y",
            "jitter": 0.5,
            "boxpoints": "false",  # all | outliers |suspectedoutliers | false
            "whiskerwidth": 0.2,
            "marker_size": 2,
            "marker": {"color": color},
        },
    }

    return {**shared, **props[type_]}


style = {"width": "100%", "height": "100%"}

config = {
    "scrollZoom": False,
    "responsive": True,
    "displaylogo": False,
    "editable": False,
}


def get_axis_appearance(chart_type, line_color, grid_color):
    default = {
        "showline": True,
        "showgrid": True,
        "zeroline": True,
    }

    attributes = {
        "histogram": {"showline": True, "showgrid": False, "zeroline": False,},
        "box": {"showline": True, "showgrid": False, "zeroline": False,},
        "pie": {"showline": True, "showgrid": True, "zeroline": False,},
    }

    shared = {
        "color": line_color,
        "linecolor": line_color,
        "zerolinecolor": line_color,
        "gridcolor": grid_color,
        "linewidth": 1,
        "gridwidth": 1,
        "zerolinewidth": 2,
    }

    return {**shared, **attributes.get(chart_type, default)}


def get_layout(
    chart_type,
    modebar_active_color,
    modebar_color,
    top_margin,
    bottom_margin,
    left_margin,
    right_margin,
):
    attributes = {
        "histogram": {"bargap": 0.05, "bargroupgap": 0.2, "barmode": "overlay"},
        "bar": {"bargap": 0.05, "bargroupgap": 0.2,},
    }

    shared = {
        "autosize": True,
        "hovermode": "closest",
        "paper_bgcolor": "transparent",
        "plot_bgcolor": "transparent",
        "showlegend": False,
        "modebar": {
            "activecolor": modebar_active_color,
            "color": modebar_color,
            "bgcolor": "transparent",
            "orientation": "v",
        },
        "margin": {"t": top_margin, "b": bottom_margin, "l": left_margin, "r": right_margin,},
    }
    return {**shared, **attributes.get(chart_type, {})}


def color_generator(i=0):
    colors = [
        "rgb(31, 119, 180)",
        "rgb(255, 127, 14)",
        "rgb(44, 160, 44)",
        "rgb(214, 39, 40)",
        "rgb(148, 103, 189)",
        "rgb(140, 86, 75)",
        "rgb(227, 119, 194)",
        "rgb(127, 127, 127)",
        "rgb(188, 189, 34)",
        "rgb(23, 190, 207)",
    ]
    while True:
        try:
            colors[i]
        except IndexError:
            i = 0

        yield colors[i]
        i += 1


def generate_grid_item(frame_id, type_):
    shared = {"i": frame_id, "x": 0, "y": 9999}

    cases = {
        "chart": {"w": 6, "h": 2, "minW": 2, "minH": 2},
        "textArea": {"w": 1, "h": 1, "minW": 1, "minH": 1},
    }

    return {**shared, **cases[type_]}
