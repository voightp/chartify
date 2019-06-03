from PySide2.QtWidgets import QWidget, QToolButton, QApplication, QVBoxLayout, QHBoxLayout, QLabel, \
    QSizePolicy, QFrame, \
    QAction, QCheckBox
from PySide2.QtCore import QSize, Qt
import sys


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

    def __init__(self, parent, fill_space=True, title="",
                 menu=None, items=None, def_act_ix=0, data=None):
        super().__init__(parent)
        self.button = QToolButton(self)
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setObjectName("buttonFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title = QLabel(title, self)
        self.title.setObjectName("buttonTitle")

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

    def setChecked(self, checked):
        self.button.setChecked(checked)

    def setEnabled(self, enabled):
        self.title.setEnabled(enabled)
        self.button.setEnabled(enabled)

    def setToolButtonStyle(self, style):
        self.button.setToolButtonStyle(style)

    def setDefaultAction(self, action):
        self.button.setDefaultAction(action)

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

    def update_state_programmatically(self, act):
        """ Handle changing buttons state when handling internally. """
        changed = self.update_state(act)

        if changed:
            act.setChecked(True)

        self.setChecked(True)


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


class ToggleButton(QCheckBox):
    """
    A custom button to represent a toggle button.

    The appearance is handled by CSS.
    """

    def __init__(self, text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setText(text)
