from chartify.charts.chart_settings import appearance, gen_dom_matrices
from collections import defaultdict


def PieTrace(raw_traces):
    # all the traces are grouped together
    groups = defaultdict(list)
    for trace in raw_traces:
        trace.selected = False
        groups[trace.units].append(trace)

    x_doms, y_doms = gen_dom_matrices(groups.keys(), max_columns=3, gap=0,
                                      flat=True, is_square=True)
    pies = {}
    for x_dom, y_dom, traces in zip(x_doms, y_doms, groups.values()):
        values, labels, colors = [], [], []

        # pie is unique trace which wraps generic traces
        trace_id = "#".join([tr.trace_id for tr in traces])
        item_id = traces[0].item_id

        for tr in traces:
            # value is not plotted when being negative
            values.append(abs(tr.total_value))
            labels.append(tr.name)
            colors.append(tr.color)

        pies[trace_id] = {
            "type": "pie",
            "opacity": 0.7,
            "itemId": item_id,
            "traceId": trace_id,
            "marker": {
                "colors": colors,
            },
            "values": values,
            "labels": labels,
            "domain": {
                "x": x_dom,
                "y": y_dom
            }
        }

    return pies


def shared(trace):
    return {
        "itemId": trace.item_id,
        "traceId": trace.trace_id,
        "name": trace.name,
        "color": trace.color,
        "hoverlabel": {
            "namelength": -1,
        },
    }


def scatter(traces):
    data = []
    for trace in traces:
        attr1 = shared(trace)
        attr2 = appearance(trace.type_, trace.color, trace.priority)
        attr3 = {
            "type": "scattergl",
            "mode": "markers",
            "hoverinfo": "all",
            "x": trace.js_timestamps,
            "y": trace.values,
            "xaxis": trace.xaxis,
            "yaxis": trace.yaxis,
        }
        data.append({**attr1, **attr2, **attr3})


class Trace:
    def __init__(self, item_id, trace_id, info_tup, values, total_value,
                 timestamps, color, type_="scatter", xaxis="x", yaxis="y",
                 selected=False, priority="normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.file_name = info_tup[0]
        self.variable_id = info_tup[1]
        self.interval = info_tup[2]
        self.key = info_tup[3]
        self.variable = info_tup[4]
        self.units = info_tup[5]
        self.values = values
        self.total_value = total_value
        self.timestamps = timestamps
        self.color = color
        self.type_ = type_
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.selected = selected
        self.priority = priority

    @property
    def js_timestamps(self):
        return [ts * 1000 for ts in self.timestamps]

    @property
    def name(self):
        return f"{self.interval} | {self.file_name}<br>" \
            f"{self.key} | {self.variable} | {self.units}"

    def plot_trace(self):
        types = {
            "scatter": self.as_scatter,
            "line": self.as_line,
            "bar": self.as_bar,
            "bubble": self.as_bubble,
            "histogram": self.as_hist,
            "box": self.as_box
        }
        return {**types[self.type_](), **self.shared()}

    def as_scatter(self):
        return {
            "type": "scattergl",
            "mode": "markers",
            "hoverinfo": "all",
            "x": self.js_timestamps,
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
        }

    def as_line(self):
        return {
            "type": "scattergl",
            "mode": "lines+markers",
            "hoverinfo": "all",
            "x": self.js_timestamps,
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
        }

    def as_bar(self):
        return {
            "type": "bar",
            "hoverinfo": "all",
            "x": self.js_timestamps,
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
        }

    def as_bubble(self):
        pass

    def as_box(self):
        return {
            "type": "box",
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
            "hoverinfo": "name+y",
        }

    def as_hist(self):
        pass
