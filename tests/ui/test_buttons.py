from pathlib import Path

import pytest
from PySide2.QtCore import QPoint, Qt
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QAction, QMenu

from chartify.ui.buttons import (
    StatusButton,
    ClickButton,
    TitledButton,
    ToggleButton,
    CheckableButton,
    MenuButton,
)
from chartify.utils.icon_painter import Pixmap
from tests import ROOT


@pytest.fixture(scope="module")
def icon1():
    path = Path(ROOT, "resources/icons/test.png")
    return QIcon(Pixmap(path))


@pytest.fixture(scope="module")
def icon2():
    path = Path(ROOT, "resources/icons/test.png")
    return QIcon(Pixmap(path, r=100, g=100, b=100, a=0.7))


class TestClickButton:
    @pytest.fixture
    def button(self, qtbot):
        button = ClickButton(None)
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, qtbot, button: ClickButton):
        assert button.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
        assert not button.isCheckable()
        assert not button.click_act

    def test_action(self, qtbot, button: ClickButton):
        act = QAction()
        button.connect_action(act)
        assert button.click_act == act

        with qtbot.wait_signal(act.triggered):
            qtbot.mouseClick(button, Qt.LeftButton)

    def test_icons(self, qtbot, button: ClickButton, icon1: QIcon, icon2: QIcon):
        button.set_icons(icon1, icon2)

        assert button.icons["enabled"] == icon1
        assert button.icons["disabled"] == icon2

    def test_set_enabled(self, qtbot, button: ClickButton, icon1: QIcon, icon2: QIcon):
        button.set_icons(icon1, icon2)
        button.setEnabled(False)

        assert not button.isEnabled()


class TestTitledButton:
    @pytest.fixture
    def button(self, qtbot):
        button = TitledButton("test", None)
        actions = []
        for i in range(5):
            a = QAction(f"Action {i}", button)
            a.setData(f"Action {i} data")
            a.setCheckable(True)
            actions.append(a)
        menu = QMenu(button)
        menu.addActions(actions)
        button.setMenu(menu)
        button.setDefaultAction(actions[0])
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, button: TitledButton):
        assert button.title.text() == "test"

    def test_enabled(self, qtbot, button: TitledButton):
        button.setEnabled(False)
        assert not button.isEnabled()
        assert not button.title.isEnabled()

    def test_data(self, button: TitledButton):
        assert button.data() == "Action 0 data"

    def test_filter_visible_actions(self, button: TitledButton):
        dt = ["Action 2 data", "Action 3 data"]
        button.filter_visible_actions(dt)
        assert button.data() == "Action 2 data"
        for a, b in zip(button.menu().actions(), [False, False, True, True, False]):
            assert a.isVisible() == b

    def test_update_state(self, button: TitledButton):
        original_act = button.menu().actions()[0]
        act = button.menu().actions()[-1]
        assert button.update_state(act)
        assert not original_act.isChecked()

    def test_update_state_internally(self, button: TitledButton):
        data = "Action 4 data"
        button.update_state_internally(data)
        assert button.data() == data

    def test_update_state_internally_invalid(self, button: TitledButton):
        data = "Invalid data"
        with pytest.raises(KeyError):
            button.update_state_internally(data)


class TestToggleButton:
    @pytest.fixture
    def button(self, qtbot):
        button = ToggleButton(None)
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, button: ToggleButton):
        assert button.slider.minimum() == 0
        assert button.slider.maximum() == 1
        assert button.slider.value() == 0
        assert not button.label

    def test_button_signal(self, qtbot, button: ToggleButton):
        signals = [button.slider.valueChanged, button.stateChanged]
        callbacks = [lambda x: 1, lambda x: x]
        with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
            button.slider.setValue(1)
        assert button.isChecked()

    def test_setText(self, qtbot, button: ToggleButton):
        button.setText("FOO")
        assert button.label.text() == "FOO"

    def test_is_checked(self, button: ToggleButton):
        assert not button.isChecked()

    def test_set_checked(self, button: ToggleButton):
        button.setChecked(True)
        assert button.isChecked()
        assert button.slider.property("isChecked") is True

    def test_set_unchecked(self, button: ToggleButton):
        button.setChecked(False)
        assert not button.isChecked()
        assert button.slider.property("isChecked") == ""

    def test_set_enabled_checked(self, button: ToggleButton):
        button.setChecked(True)
        button.setEnabled(True)
        assert button.isChecked()
        assert button.isEnabled()
        assert button.slider.property("isChecked") is True

    def test_set_enabled_unchecked(self, button: ToggleButton):
        button.setChecked(False)
        button.setEnabled(True)
        assert not button.isChecked()
        assert button.isEnabled()
        assert button.slider.property("isChecked") == ""

    def test_set_disabled_checked(self, button: ToggleButton):
        button.setChecked(True)
        button.setEnabled(False)
        assert button.isChecked()
        assert not button.isEnabled()
        assert button.slider.property("isChecked") == ""
        assert button.slider.property("isEnabled") is False

    def test_set_disabled_unchecked(self, button: ToggleButton):
        button.setChecked(False)
        button.setEnabled(False)
        assert not button.isChecked()
        assert not button.isEnabled()
        assert button.slider.property("isChecked") == ""
        assert button.slider.property("isEnabled") is False


class TestMenuButton:
    @pytest.fixture
    def button(self, qtbot):
        button = MenuButton("TEST", None)
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, button: CheckableButton):
        assert button.toolButtonStyle() == Qt.ToolButtonIconOnly
        assert button.text() == "TEST"
        assert button.popupMode() == MenuButton.InstantPopup


class TestCheckableButton:
    @pytest.fixture
    def button(self, qtbot):
        button = CheckableButton(None)
        button.status_label = "FOO BAR BAZ\nSomething something something Dark Side"
        button.show()
        qtbot.add_widget(button)
        return button

    def test_button_init(self, button: CheckableButton):
        assert button.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
        assert button.isCheckable()

    def test_button_toggled(self, qtbot, button: CheckableButton):
        icon = button.icon()
        with qtbot.wait_signal(button.toggled, check_params_cb=lambda x: x):
            qtbot.mouseClick(button, Qt.LeftButton)
        assert button.isChecked()
        assert button.icon() is not icon

    def test_set_icons(self, button: CheckableButton):
        i1, i2, i3, i4 = QIcon(), QIcon(), QIcon(), QIcon()
        button.set_icons(i1, i2, i3, i4)
        assert button.icons["primary"]["enabled"] == i1
        assert button.icons["primary"]["disabled"] == i2
        assert button.icons["secondary"]["enabled"] == i3
        assert button.icons["secondary"]["disabled"] == i4

    def test_button_enabled(self, button: CheckableButton):
        icon = button.icon()
        button.setEnabled(True)
        assert button.isEnabled()
        assert button.icon() is not icon


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
