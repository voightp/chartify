import pytest
from PySide2.QtCore import QPoint
from PySide2.QtWidgets import QFrame

from chartify.ui.buttons import StatusButton


class TestStatusButton():
    @pytest.fixture
    def button(self, qtbot):
        window = QFrame()
        window.setFrameStyle(QFrame.Panel)
        window.setFixedHeight(400)
        window.setFixedWidth(600)

        subwindow = QFrame(window)
        subwindow.setFrameStyle(QFrame.Panel)
        subwindow.setFixedHeight(200)
        subwindow.setFixedWidth(300)
        subwindow.move(QPoint(100,100))

        button = StatusButton(subwindow)
        button.move(100, 100)
        window.show()
        button.status_label = "FOO BAR BAZ\nSomething something something Dark Side"
        qtbot.add_widget(button)
        return button

    def test_button_init(self, qtbot, button):
        qtbot.stop()
