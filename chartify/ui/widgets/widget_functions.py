from PySide2.QtCore import QObject
from PySide2.QtWidgets import QWidget, QLayout


class SignalBlocker:
    def __init__(self, *args: QObject):
        self.args = args

    def __enter__(self):
        for a in self.args:
            a.blockSignals(True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for a in self.args:
            a.blockSignals(False)


def refresh_css(func):
    """ Update css on a widget and all its children. """

    def wrapper(self, *args, **kwargs):
        def loop(wgt):
            for child in wgt.children():
                if issubclass(type(child), QWidget):
                    wgt.style().unpolish(child)
                    wgt.style().polish(child)
                    loop(child)

        result = func(self, *args, **kwargs)
        self.style().unpolish(self)
        self.style().polish(self)
        loop(self)
        return result

    return wrapper


def print_args(func):
    def wrapper(*args, **kwargs):
        print("FUNCTION " + func.__name__)
        print("called with args: ", end="")
        print(*args)
        print("called with kwargs: ", end="")
        print(**kwargs)
        print()
        return func(*args, **kwargs)

    return wrapper


def clear_layout(layout: QLayout) -> None:
    """ Delete all widgets from given group. """
    while not layout.isEmpty():
        wgt = layout.itemAt(0).widget()
        layout.removeWidget(wgt)
        wgt.deleteLater()
