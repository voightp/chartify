import pandas as pd
import numpy as np
from plotly.offline import plot
import plotly.graph_objs as go


def my_plot(df):
    data = []
    df.reset_index(inplace=True)
    timestamp = df.pop("timestamp")
    for column in df:
        col_data = df[column]
        name = " ".join(column)
        ix = timestamp
        trace = genTrace(col_data, name, ix)
        data.append(trace)

    layout = dict(title="My Test Chart!", xaxis=dict(title='World Rank', zeroline=True))
    fig = dict(data=data, layout=layout)

    plot(fig, filename="my_test.html")


def genTrace(columnData, name, index):
    trace = go.Scatter(
        x=index,
        y=columnData,
        mode="lines+markers",
        name=name
    )
    return trace

