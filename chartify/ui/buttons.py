from typing import List

from PySide2.QtCore import Qt, Signal, QEvent, QPoint
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (
    QToolButton,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFrame,
    QSlider,
    QDialog,
    QAction,
)

from chartify.utils.utils import refresh_css


class ClickButton(QToolButton):
    """ A base class which automatically modifies
    icon transparency when disabled.

    Clicked signal triggers a previously assigned
    action. The button stays 'checked' until the action
    finishes.

    The button is meant to be used as non-checkable.

    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setCheckable(False)
        self.icons = {"enabled": QIcon(), "disabled": QIcon()}
        self.click_act = None
        self.clicked.connect(self.trigger_act)

    def trigger_act(self) -> None:
        """ Execute assigned action. """
        # set 'checked' state while the action executes
        self.setCheckable(True)
        self.setChecked(True)

        if self.click_act:
            self.click_act.trigger()

        # revert to the original state
        self.setCheckable(False)

    def connect_action(self, act: QAction) -> None:
        """ Assign click action to the button. """
        self.click_act = act

    def set_icons(self, enabled_icon: QIcon, disabled_icon: QIcon) -> None:
        """ Populate button's icons. """
        self.icons["enabled"] = enabled_icon
        self.icons["disabled"] = disabled_icon
        self.setIcon(enabled_icon if self.isEnabled() else disabled_icon)

    def setEnabled(self, enabled: bool) -> None:
        """ Override to adjust icon opacity. """
        super().setEnabled(enabled)
        # update icon appearance, if icons attr has not been
        # set before, this won't make any difference
        icon = self.icons["enabled"] if enabled else self.icons["disabled"]
        if icon:
            self.setIcon(icon)


class TitledButton(ClickButton):
    """ A custom button to include a top left title label.  """

    def __init__(self, text, parent):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setPopupMode(QToolButton.InstantPopup)
        self.title = QLabel(text, self)
        self.title.move(QPoint(4, 2))
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.title.setEnabled(enabled)

    def data(self) -> str:
        return self.defaultAction().data()

    def filter_visible_actions(self, actions_data: List[str]) -> None:
        """ Show only actions on the given list(based on data). """
        if self.data() not in actions_data:
            # current action is not in requested actions
            self.update_state_internally(actions_data[0])
        for act in self.menu().actions():
            act.setVisible(act.data() in actions_data)

    def update_state(self, act: QAction) -> bool:
        """ Handle changing button actions. """
        current_act = self.defaultAction()
        changed = current_act != act
        if changed:
            self.setDefaultAction(act)
        current_act.setChecked(not changed)
        return changed

    def update_state_internally(self, data: str) -> None:
        """ Handle changing buttons state when handling not internally. """
        for act in self.menu().actions():
            if act.data() == data:
                changed = self.update_state(act)
                act.setChecked(changed)
                break
        else:
            raise KeyError(f"Unexpected action {data} requested!")


class ToggleButton(QFrame):
    """ A custom button to represent a toggle button.

    The appearance is handled by CSS. Default object name is 'toggleButton'
    ('toggleButtonContainer' for parent frame) and the appearance changes
    based on the current state.

    There can be tree states enabled unchecked ('toggleButton'), enabled
    checked ('toggleButtonChecked') and disabled ('toggleButtonDisabled').

    """

    stateChanged = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.onValueChange)

        self.label = None

        layout.addWidget(self.slider)

    def onValueChange(self, val: int) -> None:
        """ Trigger slider stateChange signal. """
        self.setChecked(bool(val))
        self.stateChanged.emit(val)

    def isChecked(self) -> bool:
        """ Get the current state of toggle button. """
        return bool(self.slider.value())

    def isEnabled(self) -> bool:
        """ Check if the slider is enabled. """
        return self.slider.isEnabled()

    def setText(self, text: str) -> None:
        """ Set toggle button label. """
        self.label = QLabel(self)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.label.setText(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.label.setIndent(0)
        self.layout().insertWidget(0, self.label)

    def setChecked(self, checked: bool) -> None:
        """ Set toggle button checked. """
        self.slider.setValue(int(checked))
        self.slider.setProperty("isChecked", True if checked else "")
        refresh_css(self.slider)

    def setEnabled(self, enabled: bool) -> None:
        """ Enable or disable the button. """
        self.slider.setEnabled(enabled)
        if enabled:
            self.slider.setProperty("isChecked", True if self.isChecked() else "")
            self.slider.setProperty("isEnabled", "")
        else:
            self.slider.setProperty("isChecked", "")
            self.slider.setProperty("isEnabled", False)
        refresh_css(self.slider)


class MenuButton(QToolButton):
    """ A button to mimic 'Action' behaviour.

    This is in place to allow resizing the
    icon as QAction does not allow that.

    """

    def __init__(self, text, parent):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setText(text)
        self.setPopupMode(QToolButton.InstantPopup)


class CheckableButton(QToolButton):
    """ A button to allow changing icon color when checked. """

    def __init__(self, parent):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setCheckable(True)
        self.toggled.connect(self._toggled)
        self.icons = {
            "primary": {"enabled": QIcon(), "disabled": QIcon()},
            "secondary": {"enabled": QIcon(), "disabled": QIcon()},
        }

    def _toggled(self, checked: bool) -> None:
        """ Update icons state. """
        key = "secondary" if checked else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"
        self.setIcon(self.icons[key][enabled])

    def update_icon(self) -> None:
        """ Update current icon based on button state. """
        key = "secondary" if self.isChecked() else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"
        self.setIcon(self.icons[key][enabled])

    def set_icons(
        self, icon1: QIcon, icon1_disabled: QIcon, icon2: QIcon, icon2_disabled: QIcon
    ) -> None:
        """ Assign button icons. """
        self.icons["primary"]["enabled"] = icon1
        self.icons["primary"]["disabled"] = icon1_disabled
        self.icons["secondary"]["enabled"] = icon2
        self.icons["secondary"]["disabled"] = icon2_disabled
        self.update_icon()

    def setEnabled(self, enabled: bool) -> None:
        """ Override to adjust icon opacity. """
        super().setEnabled(enabled)
        self.update_icon()


class StatusButton(QToolButton):
    """  A button which can display some information on hover. """

    def __init__(self, parent):
        super().__init__(parent)
        self.status_dialog = QDialog(self)
        self.status_dialog.setWindowFlag(Qt.FramelessWindowHint)
        self._status_label = QLabel(self.status_dialog)
        self._status_label.setObjectName("statusLabel")

    @property
    def text(self):
        return self._status_label.text()

    @property
    def status_label(self) -> QLabel:
        return self._status_label

    @status_label.setter
    def status_label(self, label: str) -> None:
        self._status_label.setText(label)
        self._status_label.resize(self._status_label.sizeHint())

    def enterEvent(self, event: QEvent):
        self.show_status()

    def leaveEvent(self, event: QEvent):
        self.hide_status()

    def show_status(self):
        """ Display status dialog. """
        p = self.mapToGlobal(QPoint(0, 0))
        p.setY(p.y() - self.status_label.height() - 5)
        self.status_dialog.move(p)
        self.status_dialog.setVisible(True)

    def hide_status(self):
        """ Hide status dialog. """
        self.status_dialog.setVisible(False)
