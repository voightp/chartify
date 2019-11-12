from collections import defaultdict
from chartify.view.icons import combine_colors
import copy
import math


def combine_traces(traces):
    """ Group multiple traces into a single one. """
    values, labels, colors, trace_ids, priorities = [], [], [], [], []
    for trace in traces:
        values.append(abs(trace.total_value))
        labels.append(trace.name)
        colors.append(trace.color)
        trace_ids.append(trace.trace_id)
        priorities.append(trace.priority)

    return values, labels, colors, trace_ids, priorities


def group_by_units(traces):
    """ Group units as dict with units as keys. """
    groups = defaultdict(list)
    for trace in traces:
        groups[trace.units].append(trace)
    return groups


def get_all_units(traces):
    """ Get a list of all used units. """
    full = [tr.units for tr in traces]
    setlist = []
    for e in full:
        if e not in setlist:
            setlist.append(e)
    return setlist


def get_axis_inputs(type_, values, timestamps, xaxis, yaxis):
    props = {
        "scatter": {
            "x": timestamps,
            "y": values,
            "xaxis": xaxis,
            "yaxis": yaxis,
        },
        "bubble": {
            "x": timestamps,
            "y": values,
            "xaxis": xaxis,
            "yaxis": yaxis,
        },
        "histogram": {
            "type": "hist",
            "y": values,
            "xaxis": xaxis,
            "yaxis": yaxis,
        },
        "box": {
            "type": "box",
            "y": values,
            "xaxis": xaxis,
            "yaxis": yaxis,
        },
    }

    if type_ in ["scatter", "bar", "line"]:
        type_ = "scatter"

    return props[type_]


def get_shared_attributes(item_id, trace_id, name, color):
    return {
        "itemId": item_id,
        "traceId": trace_id,
        "name": name,
        "color": color,
        "hoverlabel": {
            "namelength": -1,
        },
    }


def get_pie_appearance(priorities, colors, background_color):
    weights = {
        "low": 0.3,
        "normal": 0.7,
        "high": 1
    }

    new_colors = []
    for p, c in zip(priorities, colors):
        new_colors.append(combine_colors(c, background_color, weights[p]))

    return {
        "marker": {
            "colors": new_colors,
        },
    }


def get_appearance(type_, color, priority="normal"):
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

    shared = {
        "opacity": weights[priority]["opacity"]
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
                "color": color
            }

        },
        "bar": {
            "type": "bar",
            "hoverinfo": "all",
        },
        "bubble": {

        },
        "histogram": {
            "type": "hist",
            "hoverinfo": "name+y",
        },
        "box": {
            "type": "box",
            "hoverinfo": "name+y",
            "jitter": 0.5,
            "boxpoints": "false",  # all | outliers |suspectedoutliers | false
            "whiskerwidth": 0.2,
            "marker_size": 2,
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


def gen_ref_matrix(items, max_columns, square):
    m = [[]]

    i = math.sqrt(len(items))
    if square and i.is_integer() and max_columns > i:
        # override number of columns to create a 'square' matrix
        max_columns = i

    row = 0
    for item in items:
        if len(m[row]) < max_columns:
            m[row].append(item)
        else:
            m.append([item])
            row += 1
    return m


def dom_gen(n, gap):
    w = (1 - ((n - 1) * gap)) / n
    start = 0
    for _ in range(n):
        end = start + w
        yield [start, end]
        start = end + gap


def gen_domain_matrices(items, gap=0.05, max_columns=3, flat=True, is_square=True):
    ref_matrix = gen_ref_matrix(items, max_columns, is_square)

    x_dom_mx = copy.deepcopy(ref_matrix)
    y_dom_mx = copy.deepcopy(ref_matrix)

    y_dom_gen = dom_gen(len(ref_matrix), gap)

    for i, row in enumerate(ref_matrix):
        x_dom_gen = dom_gen(len(row), gap)
        y_dom = next(y_dom_gen)
        for j, item in enumerate(row):
            x_dom_mx[i][j] = next(x_dom_gen)
            y_dom_mx[i][j] = y_dom

    if flat:
        x_dom_mx = [a for item in x_dom_mx for a in item]
        y_dom_mx = [a for item in y_dom_mx for a in item]

    return x_dom_mx, y_dom_mx


def add_shared_yaxis_data(yaxis_dct, increment):
    # modify gaps between y axes, initial domain is [0, 1]
    s = 0
    e = 1 + increment

    for i, k in enumerate(yaxis_dct.keys()):

        # skip first y axis as this axis is a 'base' one
        # and has its settings defined in default layout
        if i == 0:
            continue

        yaxis_dct[k] = {**yaxis_dct[k],
                        "anchor": "free",
                        "overlaying": "y"}
        j = i % 2

        if j == 0:
            s += increment
            pos = round(s, 2)
        else:
            e -= increment
            pos = round(e, 2)

        yaxis_dct[k]["position"] = pos
        yaxis_dct[k]["side"] = "left" if j == 0 else "right"


def get_yaxis_settings(n, line_color, grid_color, increment=0.1,
                       titles=None, y_domains=None, range_y=None):
    shared_attributes = {
        "color": line_color,
        "linecolor": line_color,
        "zerolinecolor": line_color,
        "gridcolor": grid_color,
        "showline": True,
        "linewidth": 1,
        "showgrid": True,
        "gridwidth": 1,
        "zeroline": True,
        "zerolinewidth": 2
    }
    yaxes = defaultdict(dict)

    for i in range(n):
        nm = "yaxis" if i == 0 else f"yaxis{i + 1}"

        if titles:
            yaxes[nm]["title"] = titles[i]

        yaxes[nm]["rangemode"] = "tozero"
        yaxes[nm]["type"] = "linear"

    if not y_domains:
        add_shared_yaxis_data(yaxes, increment)
    else:
        for i, k in enumerate(yaxes.keys()):
            yaxes[k] = {**yaxes[k],
                        "domain": y_domains[i],
                        "anchor": "x" if i == 0 else f"x{i + 1}",
                        "side": "left",
                        **shared_attributes}

    if range_y:
        yaxes["yaxis"]["range"] = range_y

    return yaxes


def get_shared_xdomain(n_yaxis, increment):
    domain = [0, 1]
    if n_yaxis > 2:
        for i in range(n_yaxis - 1):
            j = i % 2
            inc = increment if j == 0 else -increment
            domain[j] = round(domain[j] + inc, 2)
    return domain


def get_xaxis_settings(n_yaxis, line_color, grid_color, increment=0.1,
                       x_domains=None, date_axis=True, range_x=None):
    shared_attributes = {
        "color": line_color,
        "linecolor": line_color,
        "zerolinecolor": line_color,
        "gridcolor": grid_color,
        "showline": True,
        "linewidth": 1,
        "showgrid": True,
        "gridwidth": 1,
        "zeroline": True,
        "zerolinewidth": 2
    }

    xaxes = defaultdict(dict)
    axis_type = "date" if date_axis else "-"

    if not x_domains:
        x_dom = get_shared_xdomain(n_yaxis, increment)
        xaxes["xaxis"] = x_axis_dct["xaxis"]
        xaxes["xaxis"] = {"domain": x_dom,
                          "type": axis_type,
                          **shared_attributes}

    else:
        for i in range(len(x_domains)):
            nm = "xaxis" if i == 0 else f"xaxis{i + 1}"
            xaxes[nm] = {"side": "bottom",
                         "type": axis_type,
                         "domain": x_domains[i],
                         "anchor": "y" if i == 0 else f"y{i + 1}",
                         **shared_attributes}

    if range_x:
        xaxes["xaxis"]["range"] = range_x

    return xaxes


def get_units_axis_dct(units_lst, axis="x"):
    axis_y = {}
    for i, u in enumerate(units_lst):
        y = f"{axis}{i + 1}" if i != 0 else f"{axis}"
        axis_y[u] = y
    return axis_y
