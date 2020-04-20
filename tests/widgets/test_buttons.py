import pytest
from PySide2.QtCore import QPoint, QSize, Qt
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QAction

from chartify.ui.buttons import StatusButton, ClickButton


class TestClickButton:
    @pytest.fixture
    def button(self, qtbot):
        button = ClickButton(None, icon_size=QSize(30, 30))
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, qtbot, button: ClickButton):
        assert button.iconSize() == QSize(30, 30)
        assert button.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
        assert not button.isCheckable()
        assert not button.click_act

    def test_action(self, qtbot, button: ClickButton):
        act = QAction()
        button.connect_action(act)
        assert button.click_act == act

        with qtbot.wait_signal(act.triggered):
            qtbot.mouseClick(button, Qt.LeftButton)

    def test_icons(self, qtbot, button: ClickButton):
        icon1 = QIcon()
        icon2 = QIcon()
        button.set_icons(icon1, icon2)

        assert button.icons["enabled"] == icon1
        assert button.icons["disabled"] == icon2
        assert button.icon() == icon1

    def test_set_enabled(self, qtbot, button: ClickButton):
        button.setEnabled(False)
        icon1 = QIcon()
        icon2 = QIcon()
        button.set_icons(icon1, icon2)

        assert button.icons["enabled"] == icon1
        assert button.icons["disabled"] == icon2
        assert button.icon() == icon2

        button.setEnabled(True)
        assert button.icon() == icon1


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

        qtbot.mouseMove(button, QPoint(999, 999))
        qtbot.wait(100)  # give some time for dialog to hide
        assert not button.status_dialog.isVisible()
