def get_trace_settings(chart_type):
    shared = {
        "hoverlabel": {
            "namelength": -1,
        },
        "marker": {
            "symbol": "circle",
            "opacity": 1,
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
        "y": 1.15,
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

y_axis_dct = {
    "yaxis": {
        "side": "left",
        "position": 0
    },
    "yaxis2": {
        "side": "right",
        "position": 1,
    },
    "yaxis3": {
        "side": "left",
        "position": 0.1
    },
    "yaxis4": {
        "side": "right",
        "position": 0.9
    },
    "yaxis5": {
        "side": "left",
        "position": 0.2
    },
    "yaxis6": {
        "side": "right",
        "position": 0.8
    },
}

layout_dct = {
    "autosize": True,
    "modebar": {"activecolor": "rgba(180,180,180,1)",
                "bgcolor": "transparent",
                "color": "rgba(180,180,180,1)",
                "orientation": "v"},
    "paper_bgcolor": "transparent",
    "plot_bgcolor": "transparent",
    "showlegend": True,
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


def get_y_axis_settings(n=1, increment=0.1):
    keys = list(y_axis_dct.keys())[0:n]
    shared = {
        "anchor": "free",
        "rangemode": "tozero",
        "overlaying": "y",
    }
    dct = {k: {**v, **shared} for k, v in y_axis_dct.items() if k in keys}

    # modify gaps between y axes
    domain = [0, 1]
    for i, k in enumerate(dct.keys()):
        if i < 2:
            # skip first left and right y axis as
            # these should be 'nominal' (0, 1)
            continue
        j = i % 2
        pos = domain[j]

        pos = round(pos + (increment if j == 0 else -increment), 2)
        dct[k]["position"] = pos

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
