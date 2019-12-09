from collections import defaultdict
from functools import partial
from typing import Tuple, List, Dict, Union, Generator
from chartify.view.icons import combine_colors
from chartify.view.css_theme import parse_color
from eso_reader.constants import *


def get_pie_appearance(priorities, colors, background_color):
    weights = {
        "low": 0.3,
        "normal": 0.7,
        "high": 1
    }
    if isinstance(background_color, str):
        background_color = parse_color(background_color)

    new_colors = []
    for p, c in zip(priorities, colors):
        if isinstance(c, str):
            c = parse_color(c)
        new_colors.append(combine_colors(c, background_color, weights[p]))

    return {
        "marker": {
            "colors": new_colors,
        },
    }


def get_appearance(type_, color, interval, priority="normal"):
    weights = {
        "low": {
            "markerSize": 5,
            "lineWidth": 1,
            "opacity": 0.3
        },

        "normal": {
            "markerSize": 5,
            "lineWidth": 2,
            "opacity": 0.7
        },
        "high": {
            "markerSize": 6,
            "lineWidth": 2,
            "opacity": 1
        }}

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
        "hoverlabel": {
            "namelength": -1,
        },
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
            }
        },
        "line": {
            "type": "scattergl",
            "mode": "lines+markers",
            "hoverinfo": "all",
            "marker": {
                "size": weights[priority]["markerSize"],
                "color": color,
                "symbol": "circle"
            },
            "line": {
                "width": weights[priority]["lineWidth"],
                "color": color,
                "shape": line_shape[interval]  # "linear" | "spline" | "hv" | "vh" | "hvh" | "vhv"
            }

        },
        "bar": {
            "type": "bar",
            "hoverinfo": "all",
            "marker": {
                "color": color
            }
        },
        "bubble": {

        },
        "histogram": {
            "type": "histogram",
            "hoverinfo": "x+y",
            "histfunc": "count",  # "count" | "sum" | "avg" | "min" | "max"
            "histnorm": "percent",  # "" | "percent" | "probability" | "density" | "probability density""
            "marker": {
                "color": color
            }
        },
        "box": {
            "type": "box",
            "hoverinfo": "name+y",
            "jitter": 0.5,
            "boxpoints": "false",  # all | outliers |suspectedoutliers | false
            "whiskerwidth": 0.2,
            "marker_size": 2,
            "marker": {
                "color": color
            }
        },
    }

    return {**shared, **props[type_]}


style = {
    "width": "100%",
    "height": "100%"
}

config = {
    "scrollZoom": False,
    "responsive": True,
    "displaylogo": False,
    "editable": False
}

x_axis_dct = {
    "xaxis": {
        "domain": [0, 1],
        "autorange": True,
        "type": "linear",
        "rangeselector": {
            "y": 1.05,
            "yanchor": "top",
            "visible": True,
            "buttons": [
                {
                    "count": 1,
                    "label": "1m",
                    "step": "month",
                    "stepmode": "backward",
                    "visible": True
                }, {
                    "count": 7,
                    "label": "1w",
                    "step": "day",
                    "stepmode": "backward",
                    "visible": True
                }, {
                    "count": 1,
                    "label": "1d",
                    "step": "day",
                    "stepmode": "backward",
                    "visible": True
                },
                {"step": "all"}
            ]
        },
        "rangeslider": {
            "visible": False,
            "thickness": 0.05
        }
    },
}

base_layout = {
    "autosize": True,
    "hovermode": "closest",
    "bargap": 0.05,
    "modebar": {
        "activecolor": "rgba(180,180,180,1)",
        "bgcolor": "transparent",
        "color": "rgba(180,180,180,0.5)",
        "orientation": "v"},
    "paper_bgcolor": "transparent",
    "plot_bgcolor": "transparent",
    "showlegend": False,
    "margin": {
        "l": 50,
        "t": 50,
        "b": 50}
}


def get_base_layout(top_margin, modebar_active_color, modebar_color):
    mod = {
        "modebar": {
            "activecolor": modebar_active_color,
            "color": modebar_color
        },
        "margin": {
            "t": top_margin
        }
    }
    return {**base_layout, **mod}


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
        "rgb(23, 190, 207)"
    ]
    while True:
        try:
            colors[i]
        except IndexError:
            i = 0

        yield colors[i]
        i += 1


def generate_grid_item(frame_id, type_):
    shared = {
        "i": frame_id,
        "x": 0,
        "y": 9999
    }

    cases = {
        "chart": {
            "w": 6,
            "h": 2,
            "minW": 4,
            "minH": 2
        },
        "textArea": {
            "w": 1,
            "h": 1,
            "minW": 1,
            "minH": 1
        },
    }

    return {**shared, **cases[type_]}
