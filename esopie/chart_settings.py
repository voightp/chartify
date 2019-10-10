from collections import defaultdict
import copy


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
            "opacity": 0.5
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
            "marker": {
                "size": weights[priority]["markerSize"],
                "color": color,
                "symbol": "circle",
            }
        },
        "line": {
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

        },
        "bubble": {

        },
        "pie": {

        },
        "histogram": {

        },
        "box": {
            "jitter": 0.5,
            "boxpoints": 'all',
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

layout_dct = {
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
    "legend": {
        "orientation": "v",
        "x": 0,
        "xanchor": "left",
        "y": 1.1,
        "yanchor": "top"},
    "xaxis": {
        "autorange": True,
        "range": [],
        "type": "linear",
        "yaxis": {
            "autorange": True,
            "range": [],
            "rangemode": "tozero",
            "type": "linear",
            "side": "left",
        },
        "margin": {
            "l": 50,
            "t": 50,
            "b": 50}
    }
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


def get_item(frame_id, type_):
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


def gen_ref_matrix(items, max_columns):
    m = [[]]
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


def gen_domain_matrices(items, gap=0.05, max_columns=3, flat=True):
    ref_matrix = gen_ref_matrix(items, max_columns)

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


def get_yaxis_settings(n=1, increment=0.1, titles=None, y_domains=None):
    dct = defaultdict(dict)

    for i in range(n):
        nm = "yaxis" if i == 0 else f"yaxis{i + 1}"

        if titles:
            dct[nm]["title"] = titles[i]

        dct[nm]["rangemode"] = "tozero"

    if not y_domains:
        add_shared_yaxis_data(dct, increment)
    else:
        for i, k in enumerate(dct.keys()):
            dct[k] = {**dct[k],
                      "domain": y_domains[i],
                      "anchor": "x" if i == 0 else f"x{i + 1}",
                      "side": "left"}
    return dct


def get_shared_xdomain(n_yaxis, increment):
    domain = [0, 1]
    if n_yaxis > 2:
        for i in range(n_yaxis - 1):
            j = i % 2
            inc = increment if j == 0 else -increment
            domain[j] = round(domain[j] + inc, 2)
    return domain


def get_xaxis_settings(n_yaxis=1, increment=0.1, x_domains=None,
                       chart_type="scatter"):
    dct = defaultdict(dict)
    types = ["scatter", "bar", "bubble", "line"]
    axis_type = "date" if chart_type in types else "-"

    shared = {"gridcolor": "#444",
              "zeroline": True,
              "zerolinewidth": 10,
              "zerolinecolor": "#444"}

    if not x_domains:
        x_dom = get_shared_xdomain(n_yaxis, increment)
        dct["xaxis"] = x_axis_dct["xaxis"]
        dct["xaxis"] = {"domain": x_dom,
                        "type": axis_type,
                        **shared}

    else:
        for i in range(len(x_domains)):
            nm = "xaxis" if i == 0 else f"xaxis{i + 1}"
            dct[nm] = {"side": "bottom",
                       "type": axis_type,
                       "domain": x_domains[i],
                       "anchor": "y" if i == 0 else f"y{i + 1}",
                       **shared}

    return dct


def get_units_axis_dct(units_lst, axis="x"):
    axis_y = {}
    for i, u in enumerate(units_lst):
        y = f"{axis}{i + 1}" if i != 0 else f"{axis}"
        axis_y[u] = y
    return axis_y
