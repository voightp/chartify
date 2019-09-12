class Chart:
    def __init__(self, id_):
        self.id_ = id_
        self.data = []
        self.layout = {
            "autosize": True,
            "modebar": {"activecolor": "rgba(175,28,255,0.5)",
                        "bgcolor": "rgba(0, 0, 0, 0)",
                        "color": "rgba(175,28,255,1)",
                        "orientation": "h"},
            "paper_bgcolor": "transparent",
            "plot_bgcolor": "transparent",
            "showlegend": True,
            "title": {"text": "A Fancy Plot"},
            "xaxis": {"autorange": True,
                      "range": [],
                      "type": "linear"},
            "yaxis": {"autorange": True,
                      "range": [],
                      "type": "linear"}
        }


class Trace:
    def __init__(self, id_, mode="scattergl", x=None, y=None, z=None):
        self.id_ = id_
        self.mode = mode
        self.x = x
        self.y = y
        self.z = z

    def plotly(self):
        return {
            "id": self.id_,
            "mode": self.mode,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "marker": {
                "symbol":"circle",
                "opacity":1,
            }
        }
