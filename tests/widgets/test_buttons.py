import pytest
from PySide2.QtCore import QPoint

from chartify.ui.buttons import StatusButton


class TestStatusButton:
    @pytest.fixture
    def button(self, qtbot):
        button = StatusButton(None)
        button.move(100, 100)
        button.status_label = "FOO BAR BAZ\nSomething something something Dark Side"
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, qtbot, button: StatusButton):
        assert button.text == "FOO BAR BAZ\nSomething something something Dark Side"
        assert not button.status_dialog.isVisible()

    def test_button_show(self, qtbot, button: StatusButton):
        qtbot.mouseMove(button)
        qtbot.wait(100)  # give some time for dialog to show
        assert button.status_dialog.isVisible()

    def test_button_hide(self, qtbot, button: StatusButton):
        qtbot.mouseMove(button)
        qtbot.wait(100)  # give some time for dialog to show
        assert button.status_dialog.isVisible()

        qtbot.mouseMove(button, QPoint(999,999))
        qtbot.wait(100)  # give some time for dialog to hide
        assert not button.status_dialog.isVisible()