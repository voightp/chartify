from esopie.chart_settings import get_appearance, gen_dom_matrices
from collections import defaultdict


def PieTrace(raw_traces):
    # all the traces are grouped together
    groups = defaultdict(list)
    for trace in raw_traces:
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


class GenericTrace:
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

    @property
    def appearance(self):
        return get_appearance(self.type_, self.color, self.priority)

    def set_priority(self, priority):
        if self.priority != priority:
            self.priority = priority
            return self.appearance

    def pl_trace(self):
        types = {
            "scatter": self.as_scatter,
            "line": self.as_line,
            "bar": self.as_bar,
            "bubble": self.as_bubble,
            "histogram": self.as_hist,
            "box": self.as_box
        }
        return {**types[self.type_](), **self.shared()}

    def shared(self):
        ap = get_appearance(self.type_, self.color, self.priority)
        return {
            "itemId": self.item_id,
            "traceId": self.trace_id,
            "name": self.name,
            "color": self.color,
            "hoverlabel": {
                "namelength": -1,
            },
            **ap
        }

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
