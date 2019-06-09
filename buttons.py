from PySide2.QtWidgets import QWidget, QToolButton, QApplication, QVBoxLayout, QHBoxLayout, QLabel, \
    QSizePolicy, QFrame, \
    QAction, QCheckBox, QSlider
from PySide2.QtCore import QSize, Qt, Signal
import sys


def update_appearance(wgt):
    """ Refresh CSS of the widget. """
    wgt.style().unpolish(wgt)
    wgt.style().polish(wgt)


class TitledButton(QFrame):
    """
    A custom button to include a top left title label.

    Menu and its actions can be added via kwargs.
    Note that when extending QToolButton behaviour,
    it's required to ad wrapping functions to pass
    arguments to child self.button attributes.

    Parameters:
    -----------
        parent : QWidget
            A button' parent.
        width : int, default 50
            A width of the container.
        height : int, default 50
            A height of the container.
        fill_space : bool, default True
            Defines if the label is inside the button layout or above.
        title : str
            A title of the button.
        menu : QMenu
            QToolButton menu component.
        items : list of str
            A list of menu item names.
        default_action_index : int
            An index of the tool button default action.
        data : list of str, default None
            If specified, 'data' attribute is added for menu actions.
    """
    button_name = "buttonFrame"
    title_name = "buttonTitle"

    def __init__(self, parent, fill_space=True, title="",
                 menu=None, items=None, def_act_ix=0, data=None):
        super().__init__(parent)
        self.button = QToolButton(self)
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setObjectName(TitledButton.button_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title = QLabel(title, self)
        self.title.setObjectName(TitledButton.title_name)

        if fill_space:
            self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.title.move(4, -8)

        else:
            layout.addWidget(self.title)

        layout.addWidget(self.button)

        if menu and items:
            actions = [QAction(text, menu, checkable=True) for text in items]
            actions[def_act_ix].setChecked(True)

            if data:
                _ = [act.setData(d) for act, d in zip(actions, data)]

            menu.addActions(actions)

            self.button.setMenu(menu)
            self.button.setPopupMode(QToolButton.InstantPopup)
            self.button.setDefaultAction(actions[def_act_ix])

    def menu(self):
        return self.button.menu()

    def data(self):
        return self.defaultAction().data()

    def setEnabled(self, enabled):
        self.title.setEnabled(enabled)
        self.button.setEnabled(enabled)

    def setToolButtonStyle(self, style):
        self.button.setToolButtonStyle(style)

    def setDefaultAction(self, action):
        self.button.setDefaultAction(action)

    def setButtonObjectName(self,name):
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

    def update_state_internally(self, act):
        """ Handle changing buttons state when handling internally. """
        changed = self.update_state(act)

        if changed:
            act.setChecked(True)


class IntervalButton(QToolButton):
    """
    A predefined button to be used when selecting
    intervals.

    Parameters
    ----------
    title : str
        A title on the button.
    args
        Args passed to 'super' QtoolButton class.
    kwargs
        Kwargs passed to 'super' QtoolButton class.

    """

    def __init__(self, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEnabled(False)
        self.setText(title)
        self.setCheckable(True)
        self.setAutoExclusive(True)


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
        self.label.setText(text)
        self.layout().addWidget(self.label)

    def setChecked(self, checked):
        """ Set toggle button checked. """
        sl = self.slider
        sl.setValue(int(checked))

        obj_name = ToggleButton.object_name + ("Checked" if checked else "")
        sl.setObjectName(obj_name)
        update_appearance(sl)

    def setEnabled(self, enabled):
        """ Enable or disable the button. """
        sl = self.slider
        sl.setEnabled(enabled)

        plc = ("Checked" if self.isChecked() else "")
        obj_name = ToggleButton.object_name + (plc if enabled else "Disabled")
        sl.setObjectName(obj_name)
        update_appearance(sl)
