from PySide2.QtWidgets import QWidget, QToolButton, QApplication, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QFrame, \
    QAction
from PySide2.QtCore import QSize, Qt
import sys


class TitledButton(QFrame):
    """
    A custom button to include a top left title label.

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

    def __init__(self, parent, width=50, height=50, fill_space=True, title="",
                 menu=None, items=None, default_action_index=0, data=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(QSize(width, height))
        self.button = QToolButton(self)
        self.button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel(title, self, objectName="buttonTitle")

        if fill_space:
            self.title = label
            self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.title.move(4, -6)

        else:
            layout.addWidget(label)

        layout.addWidget(self.button)

        if menu and items:
            self.button.setMenu(menu)
            actions = [QAction(text, parent) for text in items]

            if data:
                _ = [act.setData(act.text()) for act in actions]

            menu.addActions(actions)
            self.button.setPopupMode(QToolButton.InstantPopup)
            self.button.setDefaultAction(actions[default_action_index])

    def menu(self):
        return self.button.menu()

    def setDefaultAction(self, action):
        self.button.setDefaultAction(action)

    def defaultAction(self):
        return self.button.defaultAction()
