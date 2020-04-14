import pytest

from chartify.ui.buttons import StatusButton


class TestStatusButton():
    @pytest.fixture
    def button(self, qtbot):
        button = StatusButton(None)
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, qtbot, button):
        qtbot.stop()
