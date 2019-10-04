def get_trace_appearance(chart_type, priority="normal"):
    props = {
        "high": {
            "markerSize": 6,
            "lineWidth": 2,
            "opacity": 1
        },
        "normal": {
            "markerSize": 5,
            "lineWidth": 2,
            "opacity": 0.7
        },
        "low": {
            "markerSize": 5,
            "lineWidth": 2,
            "opacity": 0.3
        }
    }

    shared = {
        "opacity": props[priority]["opacity"]
    }

    settings = {
        "scatter": {
            "marker": {
                "size": props[priority]["markerSize"],
            },
        },
        "line": {
            "marker": {
                "size": props[priority]["markerSize"],
            },
            "line": {
                "width": props[priority]["lineWidth"],
            },
        },
        "bubble": {

        },
        "bar": {

        },
        "pie": {

        },
        "histogram": {

        },
        "box": {

        }
    }

    return {**shared, **settings[chart_type]}


def get_trace_settings(chart_type):
    shared = {
        "hoverlabel": {
            "namelength": -1,
        },
        "marker": {
            "symbol": "circle",
        },
    }

    cases = {
        "scatter": {
            "type": "scattergl",
            "mode": "markers",
        },
        "line": {
            "type": "scattergl",
            "mode": "lines+markers",
        },
        "bubble": {
            "type": "scattergl",
            "mode": "markers",
        },
        "bar": {
            "type": "bar",
        },
        "pie": {
            "type": "pie",
        },
        "histogram": {
            "type": "histogram",
        },
        "box": {
            "type": "box",
        }
    }

    return {**shared, **cases[chart_type]}


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
        "y": 1.05,
        "yanchor": "top",
        "type": "date",
        "rangeselector": {
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
    "xaxis2": {
        "domain": [0, 1],
        "y": 1.25,
        "overlaying": "x"
    }
}

layout_dct = {
    "autosize": True,
    "hovermode": "closest",
    "modebar": {"activecolor": "rgba(180,180,180,1)",
                "bgcolor": "transparent",
                "color": "rgba(180,180,180,1)",
                "orientation": "v"},
    "paper_bgcolor": "transparent",
    "plot_bgcolor": "transparent",
    "showlegend": False,
    "legend": {"orientation": "v",
               "x": 0,
               "xanchor": "left",
               "y": 1.1,
               "yanchor": "top"},
    # "title": {"text": "A Fancy Plot"},
    "xaxis": {"autorange": True,
              "range": [],
              "type": "linear",
              "gridcolor": "white"},
    "yaxis": {"autorange": True,
              "range": [],
              "rangemode": "tozero",
              "type": "linear",
              "gridcolor": "white"},
    "margin": {"l": 50,
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


def get_y_axis_settings(n=1, increment=0.1, titles=None):
    dct = {}

    # modify gaps between y axes
    s = 0 - increment
    e = 1 + increment
    for i in range(1, n + 1):
        nm = "yaxis" if i == 1 else f"yaxis{i}"
        dct[nm] = {}
        j = i % 2
        dct[nm]["side"] = "left" if j == 1 else "right"

        if titles:
            dct[nm]["title"] = titles[i - 1]

        if i < 2:
            # skip first default y axis as for some unknown
            # reason assigning parameters below would break
            # the 'hover' mechanism
            continue

        if j == 1:
            s += increment
            pos = round(s, 2)
        else:
            e -= increment
            pos = round(e, 2)

        dct[nm]["position"] = pos
        dct[nm]["anchor"] = "free"
        dct[nm]["rangemode"] = "tozero"
        dct[nm]["overlaying"] = "y"

    return dct


def get_x_domain(n_yaxis=1, increment=0.1):
    domain = [0, 1]
    if n_yaxis > 2:
        for i in range(n_yaxis - 2):
            j = i % 2
            inc = increment if j == 0 else -increment
            domain[j] = round(domain[j] + inc, 2)
    return domain


def get_x_axis_settings(n=1, domain=None):
    keys = list(x_axis_dct.keys())[0:n]
    dct = {k: v for k, v in x_axis_dct.items() if k in keys}

    if domain:
        # update domain to match y axis settings
        for k in dct.keys():
            dct[k]["domain"] = domain

    return dct


def get_units_y_dct(units_lst):
    ys_dct = {}
    for i, u in enumerate(units_lst):
        y = f"y{i + 1}" if i != 0 else "y"
        ys_dct[u] = y
    return ys_dct
