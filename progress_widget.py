from PySide2 import QtCore
from PySide2.QtWidgets import QWidget, QLabel, QProgressBar, QFormLayout, QStatusBar


class MyStatusBar(QStatusBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.widgets = {}
        self.progressBars = {}
        self.labels = {}

    def add_progress_bar(self, id, name):
        name = QLabel(name)
        bar = MyProgressBar(self)
        self.progressBars[id] = bar
        self.labels[id] = name
        widget = MiniWidget(self, name, bar)
        self.widgets[id] = widget
        self.addWidget(widget)

    def remove_progress_bar(self, id):
        self.progressBars[id].deleteLater()
        self.labels[id].deleteLater()
        self.widgets[id].deleteLater()
        del self.labels[id]
        del self.progressBars[id]
        del self.widgets[id]


class MiniWidget(QWidget):
    def __init__(self, parent, name, bar):
        super().__init__(parent)
        self.layout = QFormLayout()
        self.setLayout(self.layout)
        self.layout.addRow(name, bar)


class MyProgressBar(QProgressBar):
    def __init__(self, parent):
        super().__init__(parent)
        self._text = None

        self.setAlignment(QtCore.Qt.AlignCenter)

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text
