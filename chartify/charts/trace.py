from eso_reader.constants import *

class Axis:
    def __init__(self, name, title, anchor=None, visible=True, overlaying=None):
        self.name = name
        self.title = title
        self.visible = visible
        self.children = []
        self._anchor = anchor
        self._overlaying = overlaying
        self._domain = []
        self._position = None
        self._side = None

    def __repr__(self):
        return f"Axis: {self.name}\n" \
            f"\tTitle: {self.title}\n" \
            f"\tVisible: {self.visible}\n" \
            f"\tAnchor: {self.anchor}\n" \
            f"\tOverlaying: {self._overlaying}\n" \
            f"\tDomain: {', '.join([str(d) for d in self.domain]) if self.domain else []}\n" \
            f"\tPosition: {self.position}\n" \
            f"\tSide: {self.side}\n" \
            f"\tChildren: {', '.join([ch.name for ch in self.children])}\n" \
            f"\t\tVisible: {', '.join([ch.name for ch in self.children if ch.visible])}\n" \
            f"\t\tHidden: {', '.join([ch.name for ch in self.children if not ch.visible])}\n"

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

    @property
    def position(self):
        return self._position

    @property
    def side(self):
        return self._side

    @property
    def domain(self):
        return self._domain

    @property
    def type(self):
        return "date" if self.name in [TS, H, D, M, A, RP, "datetime"] else "linear"

    @anchor.setter
    def anchor(self, anchor):
        self._anchor = anchor
        for child in self.hidden_children:
            child.anchor = anchor

    @overlaying.setter
    def overlaying(self, overlaying):
        self._overlaying = overlaying
        for child in self.children:
            child.overlaying = overlaying

    @position.setter
    def position(self, position):
        self._position = position
        for child in self.hidden_children:
            child.position = position

    @side.setter
    def side(self, side):
        self._side = side
        for child in self.hidden_children:
            child.side = side

    @domain.setter
    def domain(self, domain):
        self._domain = domain
        for child in self.hidden_children:
            child.domain = domain

    def add_child(self, axis):
        if self.overlaying:
            axis.overlaying = self.overlaying
        else:
            axis.overlaying = self.name

        self.children.append(axis)

    def as_plotly(self):
        attributes = {
            "title": self.title,
            "visible": self.visible,
            "anchor": self.anchor,
            "overlaying": self.overlaying,
            "domain": self.domain,
            "position": self.position,
            "side": self.side,
            "type": self.type,
            "rangemode": "tozero",
        }
        children = {ch.long_name: ch.as_plotly() for ch in self.children}
        return {self.long_name: attributes, **children}


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
                 type_: str, selected: bool = False, priority: str = "normal"):
        self.item_id = item_id
        self.trace_id = trace_id
        self.color = color
        self.type_ = type_
        self.selected = selected
        self.priority = priority


class Trace1D(Trace):
    def __init__(self, ref, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ref = ref

    @property
    def values(self):
        return self.ref.values if self.ref else None

    @property
    def total_value(self):
        return self.ref.total_value if self.ref else None


class Trace2D(Trace):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        if isinstance(ref, str):
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
        elif isinstance(ref, TraceData):
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

    @property
    def interval(self):
        return self._interval


class Trace3D(Trace2D):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
