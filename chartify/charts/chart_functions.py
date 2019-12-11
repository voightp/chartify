import copy
import math

from collections import defaultdict
from functools import partial
from typing import Tuple, List, Dict, Union, Generator, Any

from chartify.charts.trace import Axis, Trace2D, TraceData, Trace1D
from chartify.charts.chart_settings import get_pie_trace_appearance, get_axis_appearance
from eso_reader.constants import *


def combine_traces(traces: List[Trace1D]) -> Dict[str, Union[str, List]]:
    """ Group multiple traces into a single one. """
    combined = defaultdict(list)
    for trace in traces:
        combined["values"].append(abs(trace.total_value))
        combined["labels"].append(trace.name)
        combined["colors"].append(trace.color)
        combined["traceIds"].append(trace.trace_id)
        combined["priorities"].append(trace.priority)
        combined["selected"].append(trace.selected)
    return combined


def pie_chart(traces: List[Trace1D], background_color: str, max_columns: int = 3,
              gap: float = 0.05, square: bool = True) -> List[Dict[str, Any]]:
    """ Plot a 'special' pie chart data. """
    groups = group_by_units(traces)
    x_domains, y_domains = gen_domain_vectors(len(groups.keys()), square=square,
                                              max_columns=max_columns, gap=gap)
    data = []
    for x_dom, y_dom, traces in zip(x_domains, y_domains, groups.values()):
        combined = combine_traces(traces)
        colors = combined.pop("colors")
        priorities = combined.pop("priorities")

        data.append({
            "type": "pie",
            "opacity": 1,
            "itemId": traces[0].item_id,
            "pull": [0.1 if trace.selected else 0 for trace in traces],
            "hole": 0.3,
            "domain": {
                "x": x_dom,
                "y": y_dom
            },
            **combined,
            **get_pie_trace_appearance(priorities, colors, background_color)
        })

    return data


def group_by_units(traces: List[Trace1D]) -> Dict[str, List[Trace1D]]:
    """ Group units as dict with units as keys. """
    groups = defaultdict(list)
    for trace in traces:
        groups[trace.ref.units].append(trace)
    return groups


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
        xaxis.anchor = yaxis
        yaxis.anchor = xaxis

        if shared_x:
            y_dom = set_shared_x_positions(xaxis, y_dom, shared_x_gap)
        else:
            for child in xaxis.children:
                child.anchor = yaxis

        if shared_y:
            x_dom = set_shared_y_positions(yaxis, x_dom, shared_y_gap)
            yaxis.domain = y_dom
            for child in yaxis.visible_children:
                child.domain = y_dom
                child.overlaying = None
        else:
            n = len(yaxis.visible_children)
            gen = domain_gen(n + 1, stacked_y_gap, y_dom[0], y_dom[1])
            yaxis.domain = next(gen)
            for child in yaxis.visible_children:
                child.domain = next(gen)
                child.anchor = xaxis
                child.side = "left"
                child.overlaying = None

        xaxis.domain = x_dom
        for child in xaxis.visible_children:
            child.domain = x_dom


def get_axis_settings(chart_type: str, axis: Axis, line_color: str, grid_color: str,
                      ranges: Dict[str, List[float]] = None) -> Dict[str, Any]:
    """ Create axes plotly dictionary. """
    appearance = get_axis_appearance(chart_type, line_color, grid_color)

    axes = axis.as_plotly()

    for k, attributes in axes.items():
        axes[k] = {**attributes, **appearance}
        if k in ranges.keys():
            axes[k]["range"] = ranges[k]

    return axes


def group_traces(traces: List[Trace2D], x_types: List[str],
                 y_types: List[str]) -> Dict[str, Dict[str, List[Trace2D]]]:
    """ Group traces based on axis types. """
    grouped = defaultdict(partial(defaultdict, list))
    for trace, x, y in zip(traces, x_types, y_types):
        grouped[x][y].append(trace)
    return grouped


def get_xy_types(traces: List[Trace2D], group_datetime: bool = True):
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


def get_intervals(traces: List[Trace2D]) -> List[str]:
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


def shared_interval_axis(traces: List[Trace2D], axes_gen: Generator,
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


def assign_trace_axes(traces: List[Trace2D], xaxes: Dict[str, str],
                      yaxes: Dict[str, str]) -> None:
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


def create_2d_axis_map(traces: List[Trace2D], group_datetime: bool = True,
                       shared_x: bool = True) -> List[Tuple[Axis, Axis]]:
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
                if yaxis.title == main_y.title:
                    yaxis.visible = False
                main_y.add_child(yaxis)

            # set axis reference for the current trace group
            assign_trace_axes(traces, xaxes, yaxes)

        if (main_x, main_y) not in axes_map:
            # avoid adding other main pairs for shared x scenarios
            axes_map.append((main_x, main_y))

    return axes_map


def transform_trace(trace: Union[Trace1D, Trace2D], type_: str):
    """ Reassign reference for a specific chart. """
    ref = trace.ref
    trace.type_ = type_

    if not isinstance(trace, Trace1D) and type_ == "pie":
        trace = trace.as_1d_trace()

    else:
        if isinstance(trace, Trace1D):
            trace = trace.as_2d_trace()

        if type_ == "histogram":
            trace.x_ref = ref
            trace.y_ref = "%"
        elif type_ == "box":
            trace.x_ref = None
            trace.y_ref = ref
        else:
            trace.x_ref = "datetime"
            trace.y_ref = ref

    return trace
