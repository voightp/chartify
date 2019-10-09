from esopie.chart_settings import get_appearance


class RawTrace:
    def __init__(self, item_id, trace_id, info_tup, values, total_value,
                 timestamps, color, type_="scatter", xaxis="x", yaxis="y",
                 selected=False, priority="normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.file_name = info_tup[0]
        self.interval = info_tup[1]
        self.key = info_tup[2]
        self.variable = info_tup[3]
        self.units = info_tup[4]
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
        return f"{self.interval} | {self.file_name}" \
            f" | {self.key} | {self.variable} | {self.units}"

    def set_priority(self, priority):
        dct = {}
        if self.priority == priority:
            self.priority = priority
            dct = get_appearance(self.type_, self.color, self.priority)
        return dct

    def pl_trace(self):
        types = {
            "scatter": self.as_scatter,
            "line": self.as_line,
            "bar": self.as_bar,
            "bubble": self.as_bubble,
            "pie": self.as_pie,
            "histogram": self.as_hist,
            "box": self.as_box
        }
        return types[self.type_]()

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
            "x": self.js_timestamps,
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
        }

    def as_line(self):
        return {
            "type": "scattergl",
            "mode": "lines+markers",
            "x": self.js_timestamps,
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
        }

    def as_bar(self):
        return {
            "type": "bar",
            "x": self.js_timestamps,
            "y": self.values,
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
        }

    def as_bubble(self):
        pass

    def as_box(self):
        pass

    def as_hist(self):
        pass

    def as_pie(self):
        pass
