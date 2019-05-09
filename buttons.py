from PySide2.QtWidgets import QWidget, QToolButton, QApplication, QVBoxLayout, QHBoxLayout, QLabel
import sys

style = """
QToolButton { 
    width: 150px;
    height: 150px; 
}

QLabel {
    margin-left: 30px;
}
"""


class TitledButton(QWidget):
    def __init__(self, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = QToolButton(self)
        self.title = QLabel(title, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.button)


if __name__ == "__main__":
    app = QApplication()
    app.setStyleSheet(style)
    btn = TitledButton("FOO")
    btn.show()
    sys.exit(app.exec_())
