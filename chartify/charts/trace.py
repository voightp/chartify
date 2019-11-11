class Trace:
    def __init__(self, item_id, trace_id, info_tuple, values, total_value,
                 timestamps, color, type_="scatter", xaxis="x", yaxis="y",
                 selected=False, priority="normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.file_name = info_tuple[0]
        self.variable_id = info_tuple[1]
        self.interval = info_tuple[2]
        self.key = info_tuple[3]
        self.variable = info_tuple[4]
        self.units = info_tuple[5]
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
