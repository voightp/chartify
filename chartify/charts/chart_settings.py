from collections import defaultdict
from functools import partial
from typing import Tuple, List, Dict, Union, Generator
from chartify.view.icons import combine_colors
from chartify.view.css_theme import parse_color
from chartify.charts.trace import Axis, Trace, TraceData
from eso_reader.constants import *
import copy
import math


def combine_traces(traces: List[Trace]) -> Tuple[List, List, List, List, List, List]:
    """ Group multiple traces into a single one. """
    values, labels, colors, trace_ids, priorities, selected = [], [], [], [], [], []
    for trace in traces:
        values.append(abs(trace.total_value))  # TODO fix this
        labels.append(trace.name)
        colors.append(trace.color)
        trace_ids.append(trace.trace_id)
        priorities.append(trace.priority)
        selected.append(trace.selected)

    return values, labels, colors, trace_ids, priorities, selected


def group_by_units(traces: List[Trace]) -> Dict[str, List[Trace]]:
    """ Group units as dict with units as keys. """
    groups = defaultdict(list)
    for trace in traces:
        groups[trace.units].append(trace)
    return groups


def get_all_units(traces: List[Trace]) -> List[str]:
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


def gen_ref_matrix(n: int, max_columns: int, square: bool) -> List[List[int]]:
    """ Create reference n x m matrix. """
    m = [[]]
    i = math.sqrt(n)
    if square and i.is_integer() and max_columns > i:
        # override number of columns to create a 'square' matrix
        max_columns = i
    row = 0
    for i in range(n):
        if len(m[row]) < max_columns:
            m[row].append(i)
        else:
            m.append([i])
            row += 1
    return m


def domain_gen(n: int, gap: float, start: float = 0, end: float = 1) -> List[float]:
    """ Generate axis domain list. """
    w = ((end - ((n - end) * gap)) / n)
    start = start
    for _ in range(n):
        end = start + w
        yield [round(start, 4), round(end, 4)]
        start = end + gap


def gen_domain_vectors(n: int, gap: float = 0.05, max_columns: int = 3,
                       square: bool = True) -> Tuple[List[List[float]], List[List[float]]]:
    """ Create x and y list with domain data. """
    ref_matrix = gen_ref_matrix(n, max_columns, square)

    x_dom_mx = copy.deepcopy(ref_matrix)
    y_dom_mx = copy.deepcopy(ref_matrix)

    y_dom_gen = domain_gen(len(ref_matrix), gap)

    for i, row in enumerate(ref_matrix):
        x_dom_gen = domain_gen(len(row), gap)
        y_dom = next(y_dom_gen)
        for j, item in enumerate(row):
            x_dom_mx[i][j] = next(x_dom_gen)
            y_dom_mx[i][j] = y_dom

    x_dom_vector = [a for item in x_dom_mx for a in item]
    y_dom_vector = [a for item in y_dom_mx for a in item]

    return x_dom_vector, y_dom_vector


def set_shared_x_positions(xaxis: Axis, y_domain: List[float],
                           increment: float) -> List[float]:
    """ Set x axis position for shared x axis charts. """
    y_bottom = y_domain[0] - increment
    for i, child in enumerate(xaxis.visible_children[::-1]):
        child.anchor = "free"
        y_bottom += increment
        child.position = y_bottom

    y_bottom += increment
    return [round(y_bottom, 3), round(y_domain[1], 3)]


def set_shared_y_positions(yaxis: Axis, x_domain: List[float],
                           increment: float) -> List[float]:
    """ Set y axis position for shared y axis charts. """
    n = len(yaxis.visible_children)
    x_left = x_domain[0] - increment
    x_right = x_domain[1] if n == 0 else x_domain[1] + increment

    # assign axis from outer to inner chart space
    for i, child in enumerate(yaxis.visible_children[::-1]):
        child.anchor = "free"

        if n % 2 == 0:
            # start from left for even number of child axis
            i += 1

        j = i % 2
        if j == 0:
            x_right -= increment
            child.position = round(x_right, 2)
            child.side = "right"
        else:
            x_left += increment
            child.position = round(x_left, 2)
            child.side = "left"

    x_left += increment
    return [round(x_left, 3), round(x_right, 3)]


def set_axes_position(axes_map: List[Tuple[Axis, Axis]], shared_x: bool, shared_y: bool,
                      max_columns: int = 3, gap: float = 0.05, square: bool = True,
                      stacked_y_gap: float = 0.02, shared_x_gap: float = 0.08,
                      shared_y_gap: float = 0.08) -> None:
    """ Assign position and domain for all axes at given axes map. """
    x_domains, y_domains = gen_domain_vectors(len(axes_map), max_columns=max_columns,
                                              gap=gap, square=square)

    for (xaxis, yaxis), x_dom, y_dom in zip(axes_map, x_domains, y_domains):
        xaxis.anchor = yaxis.name
        yaxis.anchor = xaxis.name

        if shared_x:
            y_dom = set_shared_x_positions(xaxis, y_dom, shared_x_gap)
        else:
            for child in xaxis.children:
                child.anchor = yaxis.name

        if shared_y:
            x_dom = set_shared_y_positions(yaxis, x_dom, shared_y_gap)
            yaxis.domain = y_dom
            for child in yaxis.visible_children:
                child.domain = y_dom
        else:
            n = len(yaxis.children)
            gen = domain_gen(n + 1, stacked_y_gap, y_dom[0], y_dom[1])
            yaxis.domain = next(gen)
            for child in yaxis.visible_children:
                child.domain = next(gen)
                child.anchor = xaxis.name
                child.side = "left"

        xaxis.domain = x_dom
        for child in xaxis.visible_children:
            child.domain = x_dom


def get_axis_settings(axis, line_color, grid_color, ranges=None):
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

    if not axis:
        return {"yaxis": shared_attributes}

    yaxes = axis.as_plotly()

    for k, attributes in yaxes.items():
        yaxes[k] = {**attributes, **shared_attributes}
        if k in ranges.keys():
            yaxes[k]["range"] = ranges[k]

    return yaxes


def group_traces(traces, x_types, y_types):
    """ Group traces based on axis types. """
    grouped = defaultdict(partial(defaultdict, list))
    for trace, x, y in zip(traces, x_types, y_types):
        grouped[x][y].append(trace)
    return grouped


def get_xy_types(traces, group_datetime=True):
    """ Get unique list of types for each trace. """
    x_types, y_types, = [], []
    for trace in traces:
        refs = [trace.x_ref, trace.y_ref]
        types = [x_types, y_types]
        for r, t in zip(refs, types):
            if r == "datetime" and not group_datetime:
                t.append(trace.interval)
            elif isinstance(r, TraceData):
                t.append(r.units)
            else:
                t.append(r)

    return x_types, y_types


def axis_gen(axis: str = "x", start: int = 1) -> Generator[str, None, None]:
    """ Generate stream of axis identifiers. """
    i = start
    while True:
        # first axis does not have an index
        yield f"{axis}{i}" if i != 1 else f"{axis}"
        i += 1


def get_intervals(traces: List[Trace]) -> List[str]:
    """ Get a list of all trace intervals. """
    full = [trace.interval for trace in traces]
    setlist = []
    for e in full:
        if e not in setlist and e:
            setlist.append(e)
    return setlist


def standard_axis(type_: str, axes_gen: Generator, axes: Dict[str, str]) -> Axis:
    """ Create standard axis and add axes reference. """
    axis_name = next(axes_gen)
    axes[type_] = axis_name
    return Axis(axis_name, type_)


def shared_interval_axis(traces: List[Trace], axes_gen: Generator,
                         axes: Dict[str, str]) -> Axis:
    """ Assign trace interval reference and create parent axis. """
    intervals = get_intervals(traces)

    p = {TS: 0, H: 1, D: 2, M: 3, A: 4, RP: 5}
    intervals = sorted(intervals, key=lambda x: p[x])
    axis_name = next(axes_gen)

    if TS in intervals and H in intervals:
        # hourly and timestep results should be always plotted
        # on the same axis, hourly title should be used for both
        intervals.remove(TS)
        axes[TS] = axis_name

    axes[intervals[0]] = axis_name
    parent = Axis(axis_name, intervals[0])

    for interval in intervals[1:]:
        axis_name = next(axes_gen)
        axes[interval] = axis_name
        parent.add_child(Axis(axis_name, interval, visible=False))

    return parent


def assign_trace_axes(traces, xaxes, yaxes):
    """ Assign trace 'x' and 'y' axes. """
    for trace in traces:
        if trace.x_ref == "datetime":
            trace.xaxis = xaxes[trace.interval]
        else:
            trace.xaxis = xaxes[trace.x_type]

        if trace.y_ref == "datetime":
            trace.yaxis = yaxes[trace.interval]
        else:
            trace.yaxis = yaxes[trace.y_type]


def create_2d_axis_map(traces, group_datetime=True, shared_x=True):
    """ Create axis reference dictionaries. """
    # group axis based on x data type, different intervals will be plotted
    # as independent charts when shared x is not requested
    x_types, y_types = get_xy_types(traces, group_datetime=group_datetime)
    grouped = group_traces(traces, x_types, y_types)

    axes_map = []

    x_axes_gen = axis_gen("x", start=1)
    y_axes_gen = axis_gen("y", start=1)

    # each chart in layout grid has only one main x and y axis
    main_x, main_y = None, None
    for x_type, y_traces in grouped.items():
        # initialize temporary axis reference dictionaries,
        # these are used to assign axis for each trace group
        xaxes, yaxes = {}, {}

        if x_type == "datetime":
            traces = [tr for trs in y_traces.values() for tr in trs]
            xaxis = shared_interval_axis(traces, x_axes_gen, xaxes)
        else:
            xaxis = standard_axis(x_type, x_axes_gen, xaxes)

        if not main_x:
            # always set first x axis as main
            main_x = xaxis
        else:
            if shared_x:
                # there's only one main x axis for shared x
                # all consequent axes will be added as children
                main_x.add_child(xaxis)
            else:
                main_x = xaxis

        main_y = main_y if shared_x else None
        for y_type, traces in y_traces.items():
            if y_type == "datetime":
                yaxis = shared_interval_axis(traces, y_axes_gen, yaxes)
            else:
                yaxis = standard_axis(y_type, y_axes_gen, yaxes)

            if not main_y:
                main_y = yaxis
            else:
                main_y.add_child(yaxis)

            # set axis reference for the current trace group
            assign_trace_axes(traces, xaxes, yaxes)

        if (main_x, main_y) not in axes_map:
            # avoid adding other main pairs for shared x scenarios
            axes_map.append((main_x, main_y))

    return axes_map
