from PySide2.QtWidgets import QTextEdit, QSizePolicy, QLineEdit, QFrame, QHBoxLayout
from PySide2.QtGui import QTextOption
from PySide2.QtCore import Qt, Signal

# TODO this might not be necessary
# the reason behind this is that I'd like to find a way to hack cursor color
class LineEdit(QFrame):
    """
    A custom line edit to allow changing cursor color.

    """
    textEdited = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.line_edit = QLineEdit(self)
        self.line_edit.textEdited.connect(self.on_text_change)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.line_edit)

    def on_text_change(self):
        """ Trigger textEdited signal. """
        self.textEdited.emit()

    def text(self):
        """ Get str content. """
        return self.line_edit.text()

    def setPlaceholderText(self, text):
        """ Set LineEdit placeholder text. """
        self.line_edit.setPlaceholderText(text)
