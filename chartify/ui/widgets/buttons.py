from typing import List

from PySide2.QtCore import Qt, Signal, QEvent, QPoint
from PySide2.QtWidgets import (
    QToolButton,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFrame,
    QSlider,
    QAbstractButton,
    QWidget,
)

from chartify.ui.widgets.dialogs import StatusDialog
from chartify.ui.widgets.widget_functions import refresh_css


class TitledButton(QToolButton):
    """ A custom button to include a top left title label.  """

    def __init__(self, text, parent):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
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
            self.set_action(actions_data[0])
        for act in self.menu().actions():
            act.setVisible(act.data() in actions_data)

    def set_action(self, data: str) -> None:
        """ Handle changing buttons state when handling not internally. """
        for act in self.menu().actions():
            if act.data() == data:
                self.defaultAction().setChecked(False)
                act.setChecked(True)
                self.setDefaultAction(act)
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

    stateChanged = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setObjectName("toggleButton")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.onValueChange)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignCenter)
        self.label.setIndent(0)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.slider)

    def onValueChange(self, val: int) -> None:
        """ Trigger slider stateChange signal. """
        self.setChecked(bool(val))
        self.stateChanged.emit(bool(val))

    def isChecked(self) -> bool:
        """ Get the current state of toggle button. """
        return bool(self.slider.value())

    def isEnabled(self) -> bool:
        """ Check if the slider is enabled. """
        return self.slider.isEnabled()

    def setText(self, text: str) -> None:
        """ Set toggle button label. """
        self.label.setText(text)

    @refresh_css
    def setChecked(self, checked: bool) -> None:
        """ Set toggle button checked. """
        self.slider.setValue(int(checked))
        self.slider.setProperty("isChecked", True if checked else "")

    @refresh_css
    def setEnabled(self, enabled: bool) -> None:
        """ Enable or disable the button. """
        self.slider.setEnabled(enabled)
        if enabled:
            self.slider.setProperty("isChecked", True if self.isChecked() else "")
            self.slider.setProperty("isEnabled", "")
        else:
            self.slider.setProperty("isChecked", "")
            self.slider.setProperty("isEnabled", False)
        self.label.setEnabled(enabled)


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


class StatusButton(QToolButton):
    """  A tab_wgt_button which can display some information on hover. """

    def __init__(self, parent):
        super().__init__(parent)
        self.status_dialog = StatusDialog(self)
        self._status = ""

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, status: str) -> None:
        self._status = status
        self.status_dialog.set_text(status)
        self.status_dialog.resize(self.status_dialog.size())

    def enterEvent(self, event: QEvent):
        self.show_status()

    def leaveEvent(self, event: QEvent):
        self.hide_status()

    def show_status(self):
        """ Display status dialog. """
        p = self.mapToGlobal(QPoint(0, 0))
        p.setY(p.y() - self.status_dialog.height() - 5)
        self.status_dialog.move(p)
        self.status_dialog.setVisible(True)

    def hide_status(self):
        """ Hide status dialog. """
        self.status_dialog.setVisible(False)


class LabeledButton(QFrame):
    def __init__(self, parent: QWidget, button: QAbstractButton, text: str):
        super().__init__(parent)
        self.setObjectName("labeledButton")
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        button.setParent(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.button = button
        self.label = QLabel(self)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.label.setText(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignCenter)
        self.label.setIndent(0)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.button)
