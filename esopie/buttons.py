from PySide2.QtWidgets import (QToolButton, QVBoxLayout, QHBoxLayout, QLabel,
                               QSizePolicy, QFrame, QAction, QSlider)
from PySide2.QtCore import Qt, Signal, QSize
from esopie.misc_widgets import update_appearance


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
        fill_space : bool, default True
            Defines if the label is inside the button layout or above.
        title : str
            A title of the button.
        menu : QMenu, default None
            QToolButton menu component.
        items : list of str, default None
            A list of menu item names.
        default_action_index : int
            An index of the tool button default action.
        data : list of str, default None
            If specified, 'data' attribute is added for menu actions.
    """
    button_name = "buttonFrame"
    title_name = "buttonTitle"

    def __init__(self, parent, fill_space=True, title="",
                 menu=None, items=None, def_act_dt="", data=None):
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
            actions = []
            for text in items:
                act = QAction(text, menu)
                act.setCheckable(True)
                actions.append(act)

            if not data:
                data = items

            _ = [act.setData(d) for act, d in zip(actions, data)]

            if def_act_dt:
                def_act = next(act for act in actions
                               if act.data() == def_act_dt)
            else:
                def_act = actions[0]

            def_act.setChecked(True)

            menu.addActions(actions)
            self.button.setMenu(menu)
            self.button.setPopupMode(QToolButton.InstantPopup)
            self.button.setDefaultAction(def_act)

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


class ToolsButton(QToolButton):
    """
    A predefined button to be used when selecting
    intervals.

    Parameters
    ----------
    title : str
        A title on the button.
    args
        Args passed to 'super' QToolButton class.
    kwargs
        Kwargs passed to 'super' QToolButton class.

    """

    def __init__(self, title, icon, *args, checkable=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.setIcon(icon)
        self.setText(title)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setCheckable(checkable)
        self.setIconSize(QSize(20, 20))


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
        sl = self.slider
        sl.setValue(int(checked))

        nm = "true" if checked else ""
        sl.setProperty("checked", nm)
        update_appearance(sl)

    def setEnabled(self, enabled):
        """ Enable or disable the button. """
        sl = self.slider
        sl.setEnabled(enabled)

        if self.isChecked():
            sl.setProperty("checked", "true")
        else:
            nm = "" if enabled else "false"
            sl.setProperty("enabled", nm)
        update_appearance(sl)


class MenuButton(QToolButton):
    """
    A button to mimic 'Action' behaviour.

    """

    def __init__(self, icon, text, parent):
        super().__init__(parent)
        self.setIcon(icon)
        self.setText(text)
