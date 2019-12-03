class Axis:
    def __init__(self, name, title, visible=True):
        self.name = name
        self.title = title
        self.visible = visible
        self.children = []

    @property
    def long_name(self):
        axis = self.name[0]
        return self.name.replace(axis, f"{axis}axis")


class TraceData:
    def __init__(self, item_id, trace_data_id, name, values,
                 total_value, units, timestamps=None, interval=None):
        self.item_id = item_id
        self.trace_data_id = trace_data_id
        self.name = name
        self.values = values
        self.total_value = total_value
        self.units = units
        self.timestamps = timestamps
        self.interval = interval

    @property
    def js_timestamps(self):
        return [ts * 1000 for ts in self.timestamps]


class Trace:
    def __init__(self, item_id, trace_id, name, units, color, type_="scatter",
                 xaxis="x", yaxis="y", zaxis="z", selected=False, priority="normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.name = name
        self.units = units
        self.color = color
        self.type_ = type_
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.zaxis = zaxis
        self.selected = selected
        self.priority = priority
        self._x_ref = None
        self._y_ref = None
        self._z_ref = None
        self._num_values = None

    @property
    def x_ref(self):
        return self._x_ref

    @property
    def y_ref(self):
        return self._y_ref

    @property
    def z_ref(self):
        return self._z_ref

    @x_ref.setter
    def x_ref(self, x_ref):
        if x_ref == "datetime":
            self._x_ref = "datetime"
        elif self._num_values == len(x_ref.values) or not self._num_values:
            self._num_values = len(x_ref.values)
            self._x_ref = x_ref
        else:
            print(f"Cannot set x_ref: '{x_ref.name}',"
                  f"number of values does not match!")

    @y_ref.setter
    def y_ref(self, y_ref):
        if y_ref == "datetime":
            self._y_ref = "datetime"
        elif self._num_values == len(y_ref.values) or not self._num_values:
            self._num_values = len(y_ref.values)
            self._y_ref = y_ref
        else:
            print(f"Cannot set y_ref: '{y_ref.name}',"
                  f"number of values does not match!")

    @z_ref.setter
    def z_ref(self, z_ref):
        if z_ref == "datetime":
            self._z_ref = "datetime"
        elif self._num_values == len(z_ref.values) or not self._num_values:
            self._num_values = len(z_ref.values)
            self._z_ref = z_ref
        else:
            print(f"Cannot set z_ref: '{z_ref.name}',"
                  f"number of values does not match!")

    @property
    def x_values(self):
        return self._x_ref.values if isinstance(self._x_ref, TraceData) else None

    @property
    def y_values(self):
        return self._y_ref.values if isinstance(self._y_ref, TraceData) else None

    @property
    def z_values(self):
        return self._z_ref.values if isinstance(self._z_ref, TraceData) else None

    @property
    def x_type(self):
        return self._x_ref.units if isinstance(self._x_ref, TraceData) else self._x_ref

    @property
    def y_type(self):
        return self._y_ref.units if isinstance(self._y_ref, TraceData) else self._y_ref

    @property
    def z_type(self):
        return self._z_ref.units if isinstance(self._z_ref, TraceData) else self._z_ref

    @property
    def timestamps(self):
        if isinstance(self._x_ref, TraceData) and self._x_ref.timestamps:
            return self._x_ref.timestamps
        elif isinstance(self._y_ref, TraceData) and self._y_ref.timestamps:
            return self._y_ref.timestamps
        elif isinstance(self._z_ref, TraceData) and self._z_ref.timestamps:
            return self._z_ref.timestamps
        else:
            print(f"Any TraceData of '{self.name}' does "
                  f"not include timestamp information.")

    @property
    def js_timestamps(self):
        if self.timestamps:
            return [ts * 1000 for ts in self.timestamps]

    @property
    def interval(self):
        if isinstance(self._x_ref, TraceData) and self._x_ref.timestamps:
            return self._x_ref.interval
        elif isinstance(self._y_ref, TraceData) and self._y_ref.timestamps:
            return self._y_ref.interval
        elif isinstance(self._z_ref, TraceData) and self._z_ref.timestamps:
            return self._z_ref.interval
        else:
            print(f"Any TraceData of '{self.name}' does "
                  f"not include interval information.")
