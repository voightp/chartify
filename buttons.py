from PySide2.QtWidgets import QWidget, QToolButton, QApplication, QVBoxLayout, QHBoxLayout, QLabel, \
    QSizePolicy, QFrame, \
    QAction
from PySide2.QtCore import QSize, Qt
import sys


class TitledButton(QToolButton):
    """
    A custom button to include a top left title label.

    Menu and its actions can be added via kwargs.
    Note that when adding this component layout, it's
    needed to add btn.container for a correct behaviour.

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
        self.container = QFrame(parent)
        self.container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel(title, self.container, objectName="buttonTitle")
        super().__init__(self.container)

        if fill_space:
            self.title = label
            self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.title.move(4, -8)

        else:
            layout.addWidget(label)

        layout.addWidget(self)

        if menu and items:
            self.setMenu(menu)
            actions = [QAction(text, parent) for text in items]

            if data:
                _ = [act.setData(d) for act, d in zip(actions, data)]

            menu.addActions(actions)
            self.setPopupMode(QToolButton.InstantPopup)
            self.setDefaultAction(actions[def_act_ix])


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


