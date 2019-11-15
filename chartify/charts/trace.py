class Trace:
    def __init__(self, item_id, trace_id, file_name,
                 interval, key, variable, units, values, total_value,
                 timestamps, color, type_="scatter", xaxis="x",
                 yaxis="y", selected=False, priority="normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.file_name = file_name
        self.interval = interval
        self.key = key
        self.variable = variable
        self.units = units
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
