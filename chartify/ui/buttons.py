from typing import List

from PySide2.QtCore import Qt, Signal, QEvent, QPoint
from PySide2.QtWidgets import (
    QToolButton,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFrame,
    QSlider,
    QDialog,
)

from chartify.ui.widget_functions import refresh_css


class TitledButton(QToolButton):
    """ A custom tab_wgt_button to include a top left title label.  """

    def __init__(self, text, parent):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setPopupMode(QToolButton.InstantPopup)
        self.title = QLabel(text, self)
        self.title.move(QPoint(4, 2))
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.triggered.connect(lambda act: self.setDefaultAction(act))

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
    """ A custom tab_wgt_button to represent a toggle tab_wgt_button.

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
        self.stateChanged.emit(bool(val))

    def isChecked(self) -> bool:
        """ Get the current state of toggle tab_wgt_button. """
        return bool(self.slider.value())

    def isEnabled(self) -> bool:
        """ Check if the slider is enabled. """
        return self.slider.isEnabled()

    def setText(self, text: str) -> None:
        """ Set toggle tab_wgt_button label. """
        self.label = QLabel(self)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.label.setText(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.label.setIndent(0)
        self.layout().insertWidget(0, self.label)

    @refresh_css
    def setChecked(self, checked: bool) -> None:
        """ Set toggle tab_wgt_button checked. """
        self.slider.setValue(int(checked))
        self.slider.setProperty("isChecked", True if checked else "")

    @refresh_css
    def setEnabled(self, enabled: bool) -> None:
        """ Enable or disable the tab_wgt_button. """
        self.slider.setEnabled(enabled)
        if enabled:
            self.slider.setProperty("isChecked", True if self.isChecked() else "")
            self.slider.setProperty("isEnabled", "")
        else:
            self.slider.setProperty("isChecked", "")
            self.slider.setProperty("isEnabled", False)


class MenuButton(QToolButton):
    """ A tab_wgt_button to mimic 'Action' behaviour.

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
