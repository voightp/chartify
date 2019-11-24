class TraceData:
    def __init__(self, item_id, name, primary_data, primary_data_type,
                 secondary_data=None, secondary_data_type=None):
        self.item_id = item_id
        self.name = name
        self.primary_data = primary_data
        self.primary_data_type = primary_data_type
        self.secondary_data = secondary_data
        self.secondary_data_type = secondary_data_type


class Trace2D:
    def __init__(self, x_data, y_data):
        self.x_data = x_data
        self.y_data = y_data


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
