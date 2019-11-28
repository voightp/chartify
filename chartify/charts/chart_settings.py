from collections import defaultdict
from chartify.view.icons import combine_colors
from chartify.view.css_theme import parse_color
from eso_reader.constants import *
import copy
import math


def combine_traces(traces):
    """ Group multiple traces into a single one. """
    values, labels, colors, trace_ids, priorities, selected = [], [], [], [], [], []
    for trace in traces:
        values.append(abs(trace.total_value))
        labels.append(trace.name)
        colors.append(trace.color)
        trace_ids.append(trace.trace_id)
        priorities.append(trace.priority)
        selected.append(trace.selected)

    return values, labels, colors, trace_ids, priorities, selected


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


def get_all_intervals(traces):
    """ Get a list of all used units. """
    full = [tr.interval for tr in traces]
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
            "x": values,
            "yaxis": yaxis,
            "xaxis": xaxis,
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
                "color": color,
                "shape": "hvh"  # "linear" | "spline" | "hv" | "vh" | "hvh" | "vhv"
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


def gen_domain_vectors(items, gap=0.05, max_columns=3, square=True):
    ref_matrix = gen_ref_matrix(items, max_columns, square)

    x_dom_mx = copy.deepcopy(ref_matrix)
    y_dom_mx = copy.deepcopy(ref_matrix)

    y_dom_gen = dom_gen(len(ref_matrix), gap)

    for i, row in enumerate(ref_matrix):
        x_dom_gen = dom_gen(len(row), gap)
        y_dom = next(y_dom_gen)
        for j, item in enumerate(row):
            x_dom_mx[i][j] = next(x_dom_gen)
            y_dom_mx[i][j] = y_dom

    x_dom_vector = [a for item in x_dom_mx for a in item]
    y_dom_vector = [a for item in y_dom_mx for a in item]

    return x_dom_vector, y_dom_vector


def set_yaxes_positions(yaxes, increment):
    # modify gaps between y axes, initial domain is [0, 1]
    s = 0
    e = 1 + increment

    for i, k in enumerate(yaxes.keys()):

        # skip first y axis as this axis is a 'base' one
        # and has its settings defined in default layout
        if i == 0:
            continue

        yaxes[k] = {**yaxes[k],
                    "anchor": "free",
                    "overlaying": "y"}
        j = i % 2

        if j == 0:
            s += increment
            pos = round(s, 2)
        else:
            e -= increment
            pos = round(e, 2)

        yaxes[k]["position"] = pos
        yaxes[k]["side"] = "left" if j == 0 else "right"

    return yaxes


def get_yaxis_settings(n, line_color, grid_color, increment=0.1,
                       titles=None, y_domains=None, ranges_y=None):
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

    if n == 0:
        return {"yaxis": shared_attributes}

    yaxes = defaultdict(dict)

    for i in range(n):
        nm = "yaxis" if i == 0 else f"yaxis{i + 1}"

        if titles:
            yaxes[nm]["title"] = titles[i]

        yaxes[nm]["rangemode"] = "tozero"
        yaxes[nm]["type"] = "linear"

    if not y_domains:
        yaxes = set_yaxes_positions(yaxes, increment)
    else:
        for i, k in enumerate(yaxes.keys()):
            yaxes[k] = {**yaxes[k],
                        "domain": y_domains[i],
                        "anchor": "x" if i == 0 else f"x{i + 1}",
                        "side": "left"}

    for k in yaxes.keys():
        if k in ranges_y.keys():
            yaxes[k]["range"] = ranges_y[k]

        yaxes[k] = {**yaxes[k],
                    **shared_attributes}

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
                       x_domains=None, date_axis=True, ranges_x=None):
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

    for k in ranges_x.keys():
        if k in xaxes.keys():
            xaxes[k]["range"] = ranges_x[k]

    return xaxes


def get_xaxes(intervals, start_x=1):
    """ Assign x axes and create x reference map. """

    def long_name(short_name):
        return short_name.replace("x", "xaxis")

    xaxes, xaxes_ref = {}, {}
    xaxes_gen = axis_gen("x", start=start_x)

    p = {TS: 0, H: 1, D: 2, M: 3, A: 4, RP: 5}
    intervals = sorted(intervals, key=lambda x: p[x])
    x = next(xaxes_gen)

    if TS in intervals and H in intervals:
        # hourly and time step results should be
        # always plotted on the same axis
        ts = intervals.pop(intervals.index(TS))
        xaxes[ts] = x

    xaxes[intervals[0]] = x
    xaxes_ref[long_name(x)] = []
    for dt in intervals[1:]:
        xi = next(xaxes_gen)
        xaxes[dt] = xi
        xaxes_ref[long_name(x)].append(long_name(xi))

    return xaxes, xaxes_ref


def get_yaxes(units, shared_y=True):
    """ Assign y axes and create y reference map. """

    def long_name(short_name):
        return short_name.replace("y", "yaxis")

    yaxes, yaxes_ref = {}, {}
    yaxes_gen = axis_gen("y", start=1)

    if not shared_y:
        for dt in units:
            yi = next(yaxes_gen)
            yaxes[dt] = yi
            yaxes_ref[long_name(yi)] = []
    else:
        y = next(yaxes_gen)
        yaxes[units[0]] = y
        yaxes_ref[long_name(y)] = []
        for dt in units[1:]:
            yi = next(yaxes_gen)
            yaxes[dt] = yi
            yaxes_ref[long_name(y)].append(long_name(yi))

    return yaxes, yaxes_ref


def get_axis_types(traces):
    """ Get unique list of types for each trace. """
    x_types, y_types, z_types = [], [], []
    for trace in traces:
        refs = [trace.x_ref, trace.y_ref, trace.z_ref]
        types = [x_types, y_types, z_types]
        for r, t in zip(refs, types):
            if r == "datetime":
                t.append("datetime")
            elif r.units:
                t.append(r.units)

    return x_types, y_types, z_types


def group_traces(traces, x_types, y_types):
    grouped = defaultdict(list)
    for trace, x, y in zip(traces, x_types, y_types):
        grouped[x].append(trace)
    return list(grouped.values())


def get_independent_axis_map(traces, x_types, y_types):
    grouped = defaultdict(list)
    for trace, x, y in zip(traces, x_types, y_types):
        grouped[(x, y)].append(trace)
    return list(grouped.values())


def get_axis_map(traces, shared_axes="x"):
    """ Create axis reference dictionaries. """
    x_types, y_types, _ = get_axis_types(traces)

    if shared_axes == "x":
        # y axes are vertically stacked
        grouped = group_traces(traces, x_types, y_types)
    elif shared_axes == "x+y":
        # y axes are placed next to each other
        grouped = group_traces(traces, x_types, y_types)
    else:
        # each x and y combination placed in independent chart
        grouped = get_independent_axis_map(traces, x_types, y_types)

    xaxes, xaxes_ref = {}, {}
    if not shared_axes:
        start = 1
        grouped = group_by_units(traces)
        for u, traces in grouped.items():
            intervals = get_all_intervals(traces)
            xaxes_i, xaxes_ref_i = get_xaxes(intervals, start_x=start)
            xaxes[u] = xaxes_i
            xaxes_ref = {**xaxes_ref, **xaxes_ref_i}
            start += len(intervals)
    else:
        intervals = get_all_intervals(traces)
        xaxes, xaxes_ref = get_xaxes(intervals)

    yaxes, yaxes_ref = get_yaxes(units, shared_y=shared_axes == "x+y")

    return xaxes, yaxes, xaxes_ref, yaxes_ref


def axis_gen(axis="x", start=1):
    """ Generate stream of axis identifiers. """
    i = start
    while True:
        # first axis does not have an index
        yield f"{axis}{i}" if i != 1 else f"{axis}"
        i += 1


class TestTrace:
    def __init__(self, i, u):
        self.interval = i
        self.units = u


trcs = [
    TestTrace(TS, "W"),
    TestTrace(H, "W"),
    TestTrace(D, "J"),
    TestTrace(TS, "J"),
    TestTrace(M, "J"),
    TestTrace(M, "kWh"),
    TestTrace(RP, "J"),
    # TestTrace("", "J"),
]

out1 = get_axis_map(trcs, shared_axes="x")
out2 = get_axis_map(trcs, shared_axes="x+y")
out3 = get_axis_map(trcs, shared_axes="")

print(out1)
print(out2)
print(out3)
