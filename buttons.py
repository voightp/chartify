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

        label = QLabel(title, self, objectName="buttonTitle")

        if fill_space:
            self.title = label
            self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.title.move(4, -8)

        else:
            layout.addWidget(label)

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

    def setToolButtonStyle(self, style):
        self.button.setToolButtonStyle(style)

    def menu(self):
        return self.button.menu()

    def setDefaultAction(self, act):
        self.button.setDefaultAction(act)

    def defaultAction(self):
        return self.button.defaultAction()


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
