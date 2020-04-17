from PySide2.QtCore import Qt, Signal, QSize, QEvent, QPoint
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFrame,
    QSlider,
    QDialog
)

from chartify.utils.utils import refresh_css


class ClickButton(QToolButton):
    """
    A base class which automatically modifies
    icon transparency when disabled.

    Clicked signal triggers a previously assigned
    action. The button stays 'checked' until the action
    finishes.

    The button is meant to be used as non-checkable.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setCheckable(False)
        self.setIconSize(QSize(20, 20))
        self.icons = {"enabled": QIcon(), "disabled": QIcon()}

        self.click_act = None
        self.clicked.connect(self.trigger_act)

    def trigger_act(self):
        """ Execute assigned action. """
        # set 'checked' state while the action executes
        self.setCheckable(True)
        self.setChecked(True)

        if self.click_act:
            self.click_act.trigger()

        # revert to the original state
        self.setCheckable(False)

    def connect_action(self, act):
        """ Assign click action to the button. """
        self.click_act = act

    def set_icons(self, enabled_icon, disabled_icon):
        """ Populate button's icons. """
        self.icons["enabled"] = enabled_icon
        self.icons["disabled"] = disabled_icon

        icon = enabled_icon if self.isEnabled() else disabled_icon
        self.setIcon(icon)

    def setEnabled(self, enabled):
        """ Override to adjust icon opacity. """
        super().setEnabled(enabled)

        # update icon appearance, if icons attr has not been
        # set before, this won't make any difference
        icon = self.icons["enabled"] if enabled else self.icons["disabled"]
        if icon:
            self.setIcon(icon)


class TitledButton(QFrame):
    """
    A custom button to include a top left title label.

    Note that when extending QToolButton behaviour,
    it's required to ad wrapping functions to pass
    arguments to child self.button attributes.

    Parameters:
    -----------
        parent : QWidget
            A button' parent.
        fill_space : bool, default True
            Defines if the label is inside the button layout or above.

    """

    button_name = "buttonFrame"
    title_name = "buttonTitle"

    def __init__(self, text, parent, fill_space=True):
        super().__init__(parent)
        self.button = ClickButton(self)
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button.setPopupMode(QToolButton.InstantPopup)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setObjectName(TitledButton.button_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title = QLabel(text, self)
        self.title.setObjectName(TitledButton.title_name)

        if fill_space:
            self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.title.move(4, -8)

        else:
            layout.addWidget(self.title)

        layout.addWidget(self.button)

    def menu(self):
        return self.button.menu()

    def data(self):
        return self.defaultAction().data()

    def setMenu(self, menu):
        self.button.setMenu(menu)

    def setEnabled(self, enabled):
        self.title.setEnabled(enabled)
        self.button.setEnabled(enabled)

    def setToolButtonStyle(self, style):
        self.button.setToolButtonStyle(style)

    def setDefaultAction(self, action):
        self.button.setDefaultAction(action)

    def setButtonObjectName(self, name):
        self.button.setObjectName(name)

    def setText(self, text):
        self.button.setText(text)

    def defaultAction(self):
        return self.button.defaultAction()

    def get_action(self, i=-1, data=""):
        """ Get an action based on index or action's data. """
        acts = self.button.menu().actions()

        if i > 0:
            return acts[i]

        elif data:
            for act in acts:
                if act.data() == data:
                    return act

    def filter_visible_actions(self, acts_dt):
        """ Show only actions on the given list(based on data). """
        acts = self.button.menu().actions()

        if self.data() not in acts_dt:
            self.update_state_internally(acts_dt[0])

        for act in acts:
            act.setVisible(act.data() in acts_dt)

    def update_state(self, act):
        """ Handle changing button actions. """
        current_act = self.defaultAction()
        changed = current_act != act

        if changed:
            current_act.setChecked(False)
            self.setDefaultAction(act)
        else:
            current_act.setChecked(True)

        return changed

    def update_state_internally(self, dt):
        """ Handle changing buttons state when handling internally. """
        act = self.get_action(data=dt)
        changed = self.update_state(act)

        if changed:
            act.setChecked(True)


class ToggleButton(QFrame):
    """
    A custom button to represent a toggle button.

    The appearance is handled by CSS. Default object name is 'toggleButton'
    ('toggleButtonContainer' for parent frame) and the appearance changes
    based on the current state.

    There can be tree states enabled unchecked ('toggleButton'), enabled
    checked ('toggleButtonChecked') and disabled ('toggleButtonDisabled').
    """

    object_name = "toggleButton"
    container_name = "toggleButtonContainer"
    stateChanged = Signal(int)  # camel case to follow qt rules

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setObjectName(ToggleButton.container_name)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.onValueChange)
        self.slider.setObjectName(ToggleButton.object_name)

        self.label = None

        layout.addWidget(self.slider)

    def onValueChange(self, val):
        """ Trigger slider stateChange signal. """
        self.setChecked(bool(val))
        self.stateChanged.emit(val)

    def isChecked(self):
        """ Get the current state of toggle button. """
        return bool(self.slider.value())

    def setText(self, text):
        """ Set toggle button label. """
        self.label = QLabel(self)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.label.setText(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.label.setIndent(0)
        self.layout().insertWidget(0, self.label)

    def setChecked(self, checked):
        """ Set toggle button checked. """
        self.slider.setValue(int(checked))
        self.slider.setProperty("checked", True if checked else "")
        refresh_css(self.slider)

    def setEnabled(self, enabled):
        """ Enable or disable the button. """
        self.slider.setEnabled(enabled)
        if self.isChecked():
            self.slider.setProperty("checked", True)
        else:
            self.slider.setProperty("enabled", "" if enabled else False)
        refresh_css(self.slider)


class MenuButton(QToolButton):
    """
    A button to mimic 'Action' behaviour.

    This is in place to allow resizing the
    icon as QAction does not allow that.

    """

    def __init__(self, text, parent, size=QSize(25, 25)):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setText(text)
        self.setIconSize(size)
        self.setPopupMode(QToolButton.InstantPopup)


class CheckableButton(QToolButton):
    """
    A button to allow changing icon color
    when checked.

    """

    def __init__(self, parent, icon_size=QSize(20, 20)):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(icon_size)
        self.setCheckable(True)
        self.toggled.connect(self._toggled)
        self.icons = {
            "primary": {"enabled": QIcon(), "disabled": QIcon()},
            "secondary": {"enabled": QIcon(), "disabled": QIcon()},
        }

    def _toggled(self, checked):
        """ Update icons state. """
        key = "secondary" if checked else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"

        try:
            self.setIcon(self.icons[key][enabled])
        except KeyError:
            pass

    def set_icons(self, icon1, icon1_disabled, icon2, icon2_disabled):
        """ Assign button icons. """
        self.icons["primary"]["enabled"] = icon1
        self.icons["primary"]["disabled"] = icon1_disabled

        self.icons["secondary"]["enabled"] = icon2
        self.icons["secondary"]["disabled"] = icon2_disabled

        key = "secondary" if self.isChecked() else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"

        self.setIcon(self.icons[key][enabled])

    def setEnabled(self, enabled):
        """ Override to adjust icon opacity. """
        super().setEnabled(enabled)

        # update icon appearance, if icons attr have not been
        # set before, this won't make any difference
        key = "secondary" if self.isChecked() else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"

        self.setIcon(self.icons[key][enabled])


class DualActionButton(QToolButton):
    """
    A button which allows registering two
    icons and actions.

    """

    def __init__(self, parent, icon_size=QSize(20, 20)):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(icon_size)
        self.icons = {
            "primary": {"enabled": QIcon(), "disabled": QIcon()},
            "secondary": {"enabled": QIcon(), "disabled": QIcon()},
        }
        self.actions = []
        self.texts = None
        self._state = 0

    def get_current_state(self):
        """ Retrieve current state. """
        return self._state

    def set_icons(self, icon1, icon1_disabled, icon2, icon2_disabled):
        """ Assign button icons. """
        self.icons["primary"]["enabled"] = icon1
        self.icons["primary"]["disabled"] = icon1_disabled

        self.icons["secondary"]["enabled"] = icon2
        self.icons["secondary"]["disabled"] = icon2_disabled

        icon = icon1 if self.isEnabled() else icon1_disabled
        self.setIcon(icon)

    def set_actions(self, primary, secondary):
        """ Assign button click actions. """
        self.actions = [primary, secondary]
        self.clicked.connect(primary)

    def set_texts(self, primary, secondary):
        """ Assign button click actions. """
        self.texts = [primary, secondary]
        self.setText(primary)

    def set_primary_state(self):
        """ Set button 'primary' state. """
        if self._state != 0:
            self.switch_state(0)

    def set_secondary_state(self):
        """ Set button 'secondary' state. """
        if self._state != 1:
            self.switch_state(1)

    def switch_state(self, i):
        """ Switch current state. """
        self.clicked.disconnect()
        self.clicked.connect(self.actions[i])

        key = "secondary" if bool(self._state) else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"

        self.setIcon(self.icons[key][enabled])
        self.setText(self.texts[i])

        self._state = i

    def setEnabled(self, enabled):
        """ Override to adjust icon opacity. """
        super().setEnabled(enabled)

        # update icon appearance, if icons attr have not been
        # set before, this won't make any difference
        key = "secondary" if bool(self._state) else "primary"
        enabled = "enabled" if self.isEnabled() else "disabled"

        self.setIcon(self.icons[key][enabled])


class StatusButton(QToolButton):
    """  A button which can display some information on hover. """

    def __init__(self, parent):
        super().__init__(parent)
        self.status_dialog = QDialog(self)
        self.status_dialog.setWindowFlag(Qt.FramelessWindowHint)
        self._status_label = QLabel(self.status_dialog)
        self._status_label.setObjectName("statusLabel")

    @property
    def status_label(self) -> QLabel:
        return self._status_label

    @status_label.setter
    def status_label(self, label: str) -> None:
        self._status_label.setText(label)
        self._status_label.resize(self._status_label.sizeHint())

    def show_status(self):
        p = self.mapToGlobal(QPoint(0, 0))
        p.setY(p.y() - self.status_label.height() - 5)
        self.status_dialog.move(p)
        self.status_dialog.setVisible(True)

    def hide_status(self):
        self.status_dialog.setVisible(False)

    def enterEvent(self, event: QEvent):
        self.show_status()
        print("Mouse Enter")

    def leaveEvent(self, event: QEvent):
        self.hide_status()
        print("Mouse leave")
