from PySide2.QtCore import QObject
from PySide2.QtWidgets import QWidget


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
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.style().unpolish(self)
        self.style().polish(self)
        for child in self.children():
            if issubclass(type(child), QWidget):
                self.style().unpolish(child)
                self.style().polish(child)
        return result

    return wrapper
