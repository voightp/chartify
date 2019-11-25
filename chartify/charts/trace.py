class TraceData:
    def __init__(self, item_id, trace_data_id, name, values,
                 total_value, units, timestamps=None):
        self.item_id = item_id
        self.trace_data_id = trace_data_id
        self.name = name
        self.values = values
        self.total_value = total_value
        self.units = units
        self.timestamps = timestamps

    @property
    def js_timestamps(self):
        return [ts * 1000 for ts in self.timestamps]


class Trace:
    def __init__(self, item_id, trace_id, name, units, color, x_ref=None,
                 y_ref=None, z_ref=None, type_="scatter", xaxis="x",
                 yaxis="y", zaxis="z", selected=False, priority="normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.name = name
        self.units = units
        self.color = color
        self.x_ref = x_ref
        self.y_ref = y_ref
        self.z_ref = z_ref
        self.type_ = type_
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.zaxis = zaxis
        self.selected = selected
        self.priority = priority

    @property
    def x_units(self):
        return self.x_ref.units if isinstance(self.x_ref, TraceData) else None

    @property
    def y_units(self):
        return self.y_ref.units if isinstance(self.y_ref, TraceData) else None

    @property
    def z_units(self):
        return self.z_ref.units if isinstance(self.z_ref, TraceData) else None
