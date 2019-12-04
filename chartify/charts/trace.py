class Axis:
    def __init__(self, name, title, anchor=None, visible=True, overlaying=None):
        self.name = name
        self.title = title
        self.visible = visible
        self._anchor = anchor
        self._overlaying = overlaying
        self.children = []
        self.domain = []
        self.position = None
        self.side = None

    @property
    def visible_children(self):
        return [axis for axis in self.children if axis.visible]

    @property
    def hidden_children(self):
        return [axis for axis in self.children if not axis.visible]

    @property
    def long_name(self):
        axis = self.name[0]
        return self.name.replace(axis, f"{axis}axis")

    @property
    def anchor(self):
        return self._anchor

    @property
    def overlaying(self):
        return self._overlaying

    @anchor.setter
    def anchor(self, anchor):
        self._anchor = anchor
        for child in self.children:
            child.anchor = anchor

    @overlaying.setter
    def overlaying(self, overlaying):
        self._overlaying = overlaying
        for child in self.children:
            child.overlaying = overlaying

    def add_child(self, axis):
        axis.overlaying = self.name
        self.children.append(axis)

    def set_position(self, start, end):
        self.position = [start, end]

    def set_domain(self, start, end):
        self.domain = [start, end]


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
    def __init__(self, item_id: str, trace_id: str, color: str,
                 type_: str, selected: bool, priority: str):
        self.item_id = item_id
        self.trace_id = trace_id
        self.color = color
        self.type_ = type_
        self.selected = selected
        self.priority = priority


class Trace1D(Trace):
    def __init__(self, ref, *args):
        super().__init__(*args)
        self.ref = ref

    @property
    def values(self):
        return self.ref.values if self.ref else None

    @property
    def total_value(self):
        return self.ref.total_value if self.ref else None


class Trace2D(Trace):
    def __init__(self, name, *args):
        super().__init__(*args)
        self.name = name
        self.xaxis = None
        self.yaxis = None
        self._x_ref = None
        self._y_ref = None
        self._z_ref = None
        self._num_values = None
        self._interval = None
        self._timestamps = None

    @property
    def x_ref(self):
        return self._x_ref

    @property
    def y_ref(self):
        return self._y_ref

    def _validate_ref(self, ref):
        """ Check if the reference can be assigned. """
        if ref == "datetime":
            valid = True
        elif isinstance(ref, TraceData):
            num_check = not self._num_values or len(ref.values) == self._num_values
            int_check = not self._interval or not ref.interval or \
                        ref.interval == self._interval
            valid = num_check and int_check
        else:
            valid = False

        if not valid:
            print(f"Cannot set ref: '{ref.name}',"
                  f"number of values or interval does not match!")
        else:
            # assign number of values, interval or timestamps for
            # cases where any of those hasn't been assigned already
            if not self._num_values:
                self._num_values = len(ref.values)
            if not self._interval and ref.interval:
                self._interval = ref.interval
            if not self._timestamps and ref.timestamps:
                self._timestamps = ref.timestamps

        return valid

    @x_ref.setter
    def x_ref(self, x_ref):
        if self._validate_ref(x_ref):
            self._x_ref = x_ref

    @y_ref.setter
    def y_ref(self, y_ref):
        if self._validate_ref(y_ref):
            self._y_ref = y_ref

    @property
    def x_values(self):
        return self._x_ref.values if isinstance(self._x_ref, TraceData) else None

    @property
    def y_values(self):
        return self._y_ref.values if isinstance(self._y_ref, TraceData) else None

    @property
    def x_type(self):
        return self._x_ref.units if isinstance(self._x_ref, TraceData) else self._x_ref

    @property
    def y_type(self):
        return self._y_ref.units if isinstance(self._y_ref, TraceData) else self._y_ref

    @property
    def js_timestamps(self):
        if self._timestamps:
            return [ts * 1000 for ts in self._timestamps]


class Trace3D(Trace2D):
    def __init__(self, *args):
        super().__init__(*args)
        self.zaxis = None
        self._z_ref = None

    @property
    def z_ref(self):
        return self._z_ref

    @z_ref.setter
    def z_ref(self, z_ref):
        if self._validate_ref(z_ref):
            self._z_ref = z_ref

    @property
    def z_values(self):
        return self._z_ref.values if isinstance(self._z_ref, TraceData) else None

    @property
    def z_type(self):
        return self._z_ref.units if isinstance(self._z_ref, TraceData) else self._z_ref
