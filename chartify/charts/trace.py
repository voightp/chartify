from eso_reader.constants import *
from chartify.charts.chart_settings import *


class Axis:
    X_SHIFT = 30
    Y_SHIFT = 30
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
               f"\tAnchor: {self.anchor.name if isinstance(self.anchor, Axis) else self.anchor}\n" \
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
        return "date" if self.title in [TS, H, D, M, A, RP, "datetime"] else "linear"

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

    def contains_title(self, title):
        """ Check if axis or its children already contain given title. """
        titles = [self.title]
        for child in self.children:
            titles.append(child.title)
        return title in titles

    def get_title_annotations(self, color):
        annotations = []
        is_x = "x" in self.name

        if self.domain:
            a = round((self.domain[1] + self.domain[0]) / 2, 2)

            if self.anchor == "free":
                b = self.position
            else:
                b = self.anchor.domain[1] if self.side == "right" else self.anchor.domain[0]

            x, y = (a, b) if is_x else (b, a)

            attributes = {
                "text": f"{self.title}",
                "x": x,
                "y": y,
                "showarrow": False,
                "xanchor": "center",
                "yanchor": "middle",
                "xref": "paper",
                "yref": "paper",
                "xshift": 0 if is_x else -self.X_SHIFT,
                "yshift": -self.Y_SHIFT if is_x else 0,
                "textangle": 0 if is_x else -90,
                "font": {"color": color},
            }

            annotations.append(attributes)

            for child in self.visible_children:
                a = child.get_title_annotations(color)
                annotations.append(*a)

        return annotations

    def as_plotly(self):
        attributes = {
            "visible": self.visible,
            "anchor": self.anchor.name if isinstance(self.anchor, Axis) else self.anchor,
            "overlaying": self.overlaying,
            "domain": self.domain,
            "position": self.position,
            "side": self.side,
            "type": self.type,
            "rangemode": "tozero" if "y" in self.name else "normal",
        }
        p = {self.long_name: attributes}
        for child in self.children:
            ch = child.as_plotly()
            p = {**p, **ch}
        return p


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
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.ref = None

    @property
    def values(self):
        return self.ref.values if self.ref else None

    @property
    def total_value(self):
        return self.ref.total_value if self.ref else None

    def as_2d_trace(self):
        trace = Trace2D(self.name, self.item_id, self.trace_id, self.color,
                        self.type_, self.selected, self.priority)
        trace.x_ref = "datetime"
        trace.y_ref = self.ref
        return trace


class Trace2D(Trace):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.xaxis = None
        self.yaxis = None
        self._x_ref = None
        self._y_ref = None
        self._num_values = None
        self._interval = None
        self._timestamps = None

    @property
    def ref(self):
        return self.x_ref if isinstance(self.x_ref, TraceData) else self.y_ref

    @property
    def x_ref(self):
        return self._x_ref

    @property
    def y_ref(self):
        return self._y_ref

    def _validate_ref(self, ref):
        """ Check if the reference can be assigned. """
        if isinstance(ref, str) or ref is None:
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

    def _get_ref_values(self, ref):
        """ Get data for a given reference."""
        if ref == "datetime":
            return self.js_timestamps
        elif isinstance(ref, TraceData):
            return ref.values

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

    def as_1d_trace(self):
        trace = Trace1D(self.name, self.item_id, self.trace_id, self.color,
                        self.type_, self.selected, self.priority)
        trace.ref = self.ref
        return trace

    def as_plotly(self):
        return {
            "itemId": self.item_id,
            "traceId": self.trace_id,
            "name": self.name,
            "color": self.color,
            "selected": self.selected,
            "x": self._get_ref_values(self.x_ref),
            "y": self._get_ref_values(self.y_ref),
            "xaxis": self.xaxis,
            "yaxis": self.yaxis,
            **get_2d_trace_appearance(self.type_, self.color,
                                      self.interval, self.priority)
        }


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
