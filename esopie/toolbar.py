from PySide2.QtWidgets import (QVBoxLayout, QGridLayout, QToolButton,
                               QGroupBox, QSpacerItem, QSizePolicy, QMenu, QFrame)
from PySide2.QtCore import QSize, Qt, Signal
from PySide2.QtGui import QPixmap, QFont, QColor

from esopie.icons import Pixmap, text_to_pixmap
from esopie.buttons import TitledButton, ToolsButton, ToggleButton, MenuButton

from eso_reader.constants import TS, D, H, M, A, RP

si_energy_units = ["Wh", "kWh", "MWh", "J", "MJ", "GJ"]
si_power_units = ["W", "kW", "MW"]

ip_energy_units = ["Btu", "kBtu", "MBtu"]
ip_power_units = ["Btu/h", "kBtu/h", "MBtu/h", "W"]

DEFAULTS = {
    "units_system": "SI",
    "energy_units": "kWh",
    "power_units": "kW",
}


def remove_children(layout):
    """ Remove all children of the interface. """
    for _ in range(layout.count()):
        wgt = layout.itemAt(0).widget()
        layout.removeWidget(wgt)


def populate_grid_layout(layout, wgts, n_cols):
    """ Place given widgets on a specified layout with 'n' columns. """
    # render only enabled buttons
    n_rows = (len(wgts) if len(wgts) % 2 == 0 else len(wgts) + 1) // n_cols
    ixs = [(x, y) for x in range(n_rows) for y in range(n_cols)]

    for btn, ix in zip(wgts, ixs):
        layout.addWidget(btn, *ix)


def hide_disabled_wgts(wgts):
    """ Hide disabled widgets from the interface. """
    enabled, disabled = filter_disabled(wgts)

    for wgt in disabled:
        wgt.hide()

    return enabled


def filter_disabled(wgts):
    """ Take a list and split it to 'enabled', 'disabled' sub-lists. """
    enabled = []
    disabled = []

    for wgt in wgts:
        if wgt.isEnabled():
            enabled.append(wgt)
        else:
            disabled.append(wgt)

    return enabled, disabled


def show_wgts(wgts):
    """ Display given widgets. """
    for wgt in wgts:
        wgt.show()


def populate_group(group, widgets, hide_disabled=False, n_cols=2):
    """ Populate given group with given widgets. """
    layout = group.layout()
    remove_children(layout)

    if hide_disabled:
        widgets = hide_disabled_wgts(widgets)
        show_wgts(widgets)

    populate_grid_layout(layout, widgets, n_cols)


class Toolbar(QFrame):
    """
    A class to represent an application toolbar.

    """
    updateView = Signal()
    xlsxRequested = Signal()
    sumRequested = Signal()
    meanRequested = Signal()
    removeRequested = Signal()
    totalsChanged = Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("toolbar")
        self.layout = QVBoxLayout(self)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignTop)

        self._units_settings = {"energy_units": "",
                                "power_units": "",
                                "units_system": "",
                                "rate_to_energy": False}

        self.interval_btns = {}
        self.intervals_group = QGroupBox("Intervals", self)
        self.intervals_group.setObjectName("intervalsGroup")
        self.set_up_interval_btns()
        self.layout.addWidget(self.intervals_group)

        self.outputs_group = QGroupBox("Outputs", self)
        self.outputs_group.setObjectName("outputsGroup")
        self.totals_btn = ToolsButton("totals", QPixmap("../icons/building_grey.png"),
                                      checkable=True, parent=self.outputs_group)
        self.totals_btn.setEnabled(False)

        self.all_files_btn = ToolsButton("all files", QPixmap("../icons/all_files_grey.png"),
                                         checkable=True, parent=self)
        self.all_files_btn.setEnabled(False)
        self.set_up_outputs_btns()
        self.layout.addWidget(self.outputs_group)

        self.tools_group = QGroupBox("Tools", self)
        self.tools_group.setObjectName("toolsGroup")
        self.export_xlsx_btn = QToolButton(self.tools_group)
        self.sum_vars_btn = QToolButton(self.tools_group)
        self.mean_vars_btn = QToolButton(self.tools_group)
        self.remove_vars_btn = QToolButton(self.tools_group)
        self.set_up_tools()
        self.layout.addWidget(self.tools_group)

        self.custom_units_toggle = ToggleButton(self)
        self.custom_units_toggle.setText("Units")
        self.custom_units_toggle.setChecked(True)
        self.layout.addWidget(self.custom_units_toggle)

        self.units_group = QFrame(self)
        self.units_group.setObjectName("unitsGroup")
        self.energy_units_btn = None
        self.power_units_btn = None
        self.units_system_btn = None
        self.rate_to_energy_btn = None
        self.set_up_units()
        self.layout.addWidget(self.units_group)

        spacer = QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addSpacerItem(spacer)

        self.settings_btn = MenuButton(QPixmap("../icons/gear_grey.png", ), "Settings", self)
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setIconSize(QSize(40, 40))
        self.layout.addWidget(self.settings_btn)

        self.connect_actions()

    @property
    def units_btns(self):
        """ A shorthand to get all units buttons."""
        return [self.energy_units_btn,
                self.power_units_btn,
                self.units_system_btn,
                self.rate_to_energy_btn]

    @property
    def tools_btns(self):
        """ A shorthand to get all tools buttons."""
        return [self.export_xlsx_btn,
                self.remove_vars_btn,
                self.sum_vars_btn,
                self.mean_vars_btn]

    def all_files_requested(self):
        """ Check if results from all eso files are requested. """
        btn = self.all_files_btn
        return btn.isChecked() and btn.isEnabled()

    def totals_requested(self):
        """ Check if results from all eso files are requested. """
        return self.totals_btn.isChecked()

    def populate_outputs_group(self):
        """ Populate outputs buttons. """
        outputs_btns = [self.totals_btn,
                        self.all_files_btn]

        populate_group(self.outputs_group, outputs_btns)

    def populate_intervals_group(self, hide_disabled=True):
        """ Populate interval buttons based on a current state. """
        btns = self.interval_btns.values()
        populate_group(self.intervals_group, btns, hide_disabled=hide_disabled)

    def populate_tools_group(self):
        """ Populate tools group layout. """
        populate_group(self.tools_group, self.tools_btns)

    def populate_units_group(self):
        """ Populate units group layout. """
        populate_group(self.units_group, self.units_btns)

    def set_up_outputs_btns(self):
        """ Create interval buttons and a parent container. """
        # ~~~~ Layout to hold interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        outputs_btns_layout = QGridLayout(self.outputs_group)
        outputs_btns_layout.setSpacing(0)
        outputs_btns_layout.setContentsMargins(0, 0, 0, 0)
        outputs_btns_layout.setAlignment(Qt.AlignTop)

        outputs_btns_layout.addWidget(self.totals_btn)
        outputs_btns_layout.addWidget(self.all_files_btn)

        self.populate_outputs_group()

    def set_up_interval_btns(self):
        """ Create interval buttons and a parent container. """
        # ~~~~ Layout to hold interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        interval_btns_layout = QGridLayout(self.intervals_group)
        interval_btns_layout.setSpacing(0)
        interval_btns_layout.setContentsMargins(0, 0, 0, 0)
        interval_btns_layout.setAlignment(Qt.AlignTop)

        # ~~~~ Generate interval buttons ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        p = self.intervals_group
        ids = {TS: "TS", H: "H", D: "D", M: "M", A: "A", RP: "RP"}
        font = QFont("Roboto", 40)
        color = QColor(112, 112, 112)

        for k, v in ids.items():
            pix = text_to_pixmap(v, font, color)
            btn = ToolsButton(k, pix, checkable=True, parent=p)
            btn.setAutoExclusive(True)
            btn.setEnabled(False)
            self.interval_btns[k] = btn

        self.populate_intervals_group(hide_disabled=False)

    def set_up_units(self):
        """ Set up units options. . """
        # ~~~~ Layout to hold options  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_layout = QGridLayout(self.units_group)
        units_layout.setSpacing(0)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        energy_units_menu = QMenu(self)
        items = si_energy_units + ip_energy_units
        ix = items.index(DEFAULTS["energy_units"])
        self.energy_units_btn = TitledButton(self.units_group, fill_space=True,
                                             title="energy", menu=energy_units_menu,
                                             items=items, data=items, def_act_ix=ix)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        power_units_menu = QMenu(self)
        items = list(dict.fromkeys(si_power_units + ip_power_units))  # remove duplicate 'W'
        ix = items.index(DEFAULTS["power_units"])
        self.power_units_btn = TitledButton(self.units_group, fill_space=True,
                                            title="power", menu=power_units_menu,
                                            items=items, data=items, def_act_ix=ix)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_system_menu = QMenu(self)
        items = ["SI", "IP"]
        ix = items.index(DEFAULTS["units_system"])
        self.units_system_btn = TitledButton(self.units_group, fill_space=True,
                                             title="system", menu=units_system_menu,
                                             items=items, data=items, def_act_ix=ix)
        self.toggle_units(DEFAULTS["units_system"])

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_to_energy_btn = QToolButton(self.units_group)
        self.rate_to_energy_btn.setCheckable(True)
        self.rate_to_energy_btn.setObjectName("rateToEnergyBtn")
        self.rate_to_energy_btn.setText("rate to\n energy")

        self.populate_units_group()

    def set_up_tools(self):
        """ Create a general set of tools. """
        # ~~~~ Layout to hold tools settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        tools_layout = QGridLayout(self.tools_group)
        tools_layout.setSpacing(0)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setAlignment(Qt.AlignTop)

        # ~~~~ Export xlsx button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.export_xlsx_btn.setEnabled(False)
        self.export_xlsx_btn.setText("save xlsx")
        self.export_xlsx_btn.setCheckable(False)

        # ~~~~ Sum variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.sum_vars_btn.setEnabled(False)
        self.sum_vars_btn.setText("sum")
        self.sum_vars_btn.setCheckable(False)

        # ~~~~ Mean variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.mean_vars_btn.setEnabled(False)
        self.mean_vars_btn.setText("mean")
        self.mean_vars_btn.setCheckable(False)

        # ~~~~ Remove variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.remove_vars_btn.setEnabled(False)
        self.remove_vars_btn.setText("remove")
        self.remove_vars_btn.setCheckable(False)

        self.populate_tools_group()

    def disable_interval_btns(self):
        """ Disable all interval buttons. """
        for btn in self.interval_btns.values():
            btn.setHidden(False)
            btn.setChecked(False)
            btn.setEnabled(False)

    def enable_tools_btns(self, enable=True, exclude=None):
        """ Disable all tool buttons with given exceptions. """
        exclude = [exclude] if isinstance(exclude, list) else exclude
        pairs = [("sum", self.sum_vars_btn),
                 ("mean", self.mean_vars_btn),
                 ("remove", self.remove_vars_btn),
                 ("xlsx", self.export_xlsx_btn)]

        btns = [btn for s, btn in pairs if s not in exclude]

        for btn in btns:
            btn.setEnabled(enable)

    def set_initial_layout(self):
        """ Define an app layout when there isn't any file loaded. """
        self.all_files_btn.setEnabled(False)
        self.totals_btn.setEnabled(False)
        self.rate_to_energy_btn.setEnabled(True)

        self.disable_interval_btns()
        self.populate_intervals_group(hide_disabled=False)
        self.populate_units_group()
        self.populate_outputs_group()
        self.populate_tools_group()

    def update_rate_ene_state(self):
        """ Enable or disable rate to energy button. """
        # handle changing the state on rate_to_energy_btn
        # as this is allowed only for daily+ intervals
        if self.custom_units_toggle.isChecked():
            b = self.get_selected_interval() not in [TS, H]
            self.rate_to_energy_btn.setEnabled(b)
        else:
            self.rate_to_energy_btn.setEnabled(False)

    def interval_changed(self):
        """ Update view when an interval is changed. """
        self.update_rate_ene_state()
        self.updateView.emit()

    def get_selected_interval(self):
        btns = self.interval_btns
        try:
            return next(k for k, btn in btns.items() if btn.isChecked())
        except StopIteration:
            pass

    def update_intervals_state(self, available_intervals):
        """ Deactivate interval buttons if they are not applicable. """
        selected_interval = self.get_selected_interval()
        all_btns_dct = self.interval_btns

        for key, btn in all_btns_dct.items():
            if key in available_intervals:
                btn.setEnabled(True)
            else:
                # interval is not applicable for current eso file
                btn.setEnabled(False)
                btn.setChecked(False)

        # when there isn't any previously selected interval applicable,
        # the first available button is selected
        if selected_interval not in available_intervals:
            btn = next(btn for btn in all_btns_dct.values() if btn.isEnabled())
            btn.setChecked(True)

        self.update_rate_ene_state()

    def get_units_settings(self):
        """ Get currently selected units. """
        btn = self.rate_to_energy_btn
        rate_to_energy = btn.isEnabled() and btn.isChecked()

        units_system = self.units_system_btn.data()
        energy_units = self.energy_units_btn.data()
        power_units = self.power_units_btn.data()

        return rate_to_energy, units_system, energy_units, power_units

    def store_units_settings(self):
        """ Store intermediate units settings. """
        btns = self.units_btns[:3]

        for s, btn in zip(self._units_settings.keys(), btns):
            self._units_settings[s] = btn.data()

        checked = self.rate_to_energy_btn.isChecked()
        self._units_settings["rate_to_energy"] = checked

    def restore_units_settings(self):
        """ Restore units settings. """
        btns = self.units_btns[:3]

        for s, btn in zip(self._units_settings.keys(), btns):
            data = self._units_settings[s]
            act = btn.get_action(data=data)
            btn.update_state_internally(act)

        checked = self._units_settings["rate_to_energy"]
        self.rate_to_energy_btn.setChecked(checked)

    def enable_units_buttons(self, enabled):
        """ Enable or disable units settings buttons. """
        for btn in self.units_btns[:3]:
            btn.setEnabled(enabled)

        self.update_rate_ene_state()

    def reset_units_to_default(self):
        """ Reset units to E+ default. """
        data = ["J", "W", "SI"]
        btns = self.units_btns[:3]

        for dt, btn in zip(data, btns):
            act = btn.get_action(data=dt)
            btn.update_state_internally(act)

        self.rate_to_energy_btn.setEnabled(False)
        self.rate_to_energy_btn.setChecked(False)

    def units_settings_toggled(self, state):
        """ Update units settings when custom units toggled. """
        disabled = state == 0
        if disabled:
            self.store_units_settings()
            self.reset_units_to_default()
        else:
            self.restore_units_settings()

        self.enable_units_buttons(not disabled)
        self.updateView.emit()

    def rate_to_energy_toggled(self):
        """ Update view when rate_to_energy changes. """
        self.updateView.emit()

    def totals_toggled(self, checked):
        """ Toggle standard outputs and totals. """
        self.totalsChanged.emit(checked)

    def toggle_units(self, units_system):
        """ Handle displaying allowed units for given units system. """
        if units_system == "IP":
            en_acts = ip_energy_units
            pw_acts = ip_power_units

        else:
            en_acts = si_energy_units
            pw_acts = si_power_units

        self.energy_units_btn.filter_visible_actions(en_acts)
        self.power_units_btn.filter_visible_actions(pw_acts)

    def units_system_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.units_system_btn.update_state(act)

        dt = act.data()
        self.toggle_units(dt)

        if changed:
            self.updateView.emit()

    def power_units_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.power_units_btn.update_state(act)

        if changed:
            self.updateView.emit()

    def energy_units_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.energy_units_btn.update_state(act)

        if changed:
            self.updateView.emit()

    def connect_actions(self):
        """ Connect toolbar actions. """
        # ~~~~ Interval buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btns = self.interval_btns.values()
        _ = [btn.clicked.connect(self.interval_changed) for btn in btns]

        # ~~~~ Options buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.export_xlsx_btn.clicked.connect(self.xlsxRequested.emit)
        self.mean_vars_btn.clicked.connect(self.meanRequested.emit)
        self.remove_vars_btn.clicked.connect(self.removeRequested.emit)
        self.sum_vars_btn.clicked.connect(self.sumRequested.emit)
        self.totals_btn.clicked.connect(self.totals_toggled)

        # ~~~~ Options Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.custom_units_toggle.stateChanged.connect(self.units_settings_toggled)
        self.rate_to_energy_btn.clicked.connect(self.rate_to_energy_toggled)

        # ~~~~ Settings Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.energy_units_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_units_btn.menu().triggered.connect(self.power_units_changed)
        self.units_system_btn.menu().triggered.connect(self.units_system_changed)
