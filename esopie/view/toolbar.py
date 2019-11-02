from PySide2.QtWidgets import (QVBoxLayout, QGridLayout, QToolButton,
                               QGroupBox, QSizePolicy, QMenu,
                               QFrame)
from PySide2.QtCore import Qt, Signal

from esopie.settings import Settings
from esopie.view.icons import Pixmap
from esopie.view.buttons import (TitledButton, ToggleButton, CheckableButton, DualActionButton, ClickButton)

from eso_reader.constants import TS, D, H, M, A, RP


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
    A class to represent application toolbar.

    """
    settingsUpdated = Signal()
    temp_settings = {"energy_units": "",
                     "power_units": "",
                     "units_system": "",
                     "rate_to_energy": False}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("toolbar")
        self.layout = QVBoxLayout(self)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignTop)

        # ~~~~ Intervals group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.interval_btns = {}
        self.intervals_group = QGroupBox("Intervals", self)
        self.intervals_group.setObjectName("intervalsGroup")
        self.set_up_interval_btns()

        self.layout.addWidget(self.intervals_group)

        # ~~~~ Outputs group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.outputs_group = QGroupBox("Outputs", self)
        self.outputs_group.setObjectName("outputsGroup")

        self.totals_btn = CheckableButton(self.outputs_group)
        self.totals_btn.setText("totals")
        self.totals_btn.setEnabled(False)

        self.all_files_btn = CheckableButton(self.outputs_group)
        self.all_files_btn.setText("all files")
        self.all_files_btn.setEnabled(False)

        self.set_up_outputs_btns()
        self.layout.addWidget(self.outputs_group)

        # ~~~~ Tools group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tools_group = QGroupBox("Tools", self)
        self.tools_group.setObjectName("toolsGroup")

        self.sum_btn = ClickButton(self.tools_group)
        self.mean_btn = ClickButton(self.tools_group)
        self.remove_btn = ClickButton(self.tools_group)
        self.set_up_tools()

        self.layout.addWidget(self.tools_group)

        # ~~~~ Units group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.custom_units_toggle = ToggleButton(self)
        self.custom_units_toggle.setText("Custom Units")
        self.custom_units_toggle.setChecked(Settings.CUSTOM_UNITS)
        self.layout.addWidget(self.custom_units_toggle)

        self.units_group = QFrame(self)
        self.units_group.setObjectName("unitsGroup")

        self.energy_btn = None
        self.power_btn = None
        self.units_sys_btn = None
        self.rate_energy_btn = None
        self.set_up_units()

        self.layout.addWidget(self.units_group)

        self.connect_actions()

    @property
    def units_btns(self):
        """ A shorthand to get all units buttons."""
        return [self.energy_btn,
                self.power_btn,
                self.units_sys_btn,
                self.rate_energy_btn]

    @property
    def tools_btns(self):
        """ A shorthand to get all tools buttons."""
        return [self.sum_btn,
                self.mean_btn,
                self.remove_btn]

    @property
    def outputs_btns(self):
        """ A shorthand to get all outputs buttons. """
        return [self.totals_btn,
                self.all_files_btn]

    def load_icons(self, root, c1, c2):
        """ Load toolbar buttons icons. """
        self.totals_btn.set_icons(Pixmap(root + "building.png", *c1),
                                  Pixmap(root + "building.png", *c1, a=0.5),
                                  Pixmap(root + "building.png", *c2),
                                  Pixmap(root + "building.png", *c2, a=0.5))

        self.all_files_btn.set_icons(Pixmap(root + "all_files.png", *c1),
                                     Pixmap(root + "all_files.png", *c1, a=0.5),
                                     Pixmap(root + "all_files.png", *c2),
                                     Pixmap(root + "all_files.png", *c2, a=0.5))

        self.sum_btn.set_icons(Pixmap(root + "sigma.png", *c1),
                               Pixmap(root + "sigma.png", *c1, a=0.5))
        self.mean_btn.set_icons(Pixmap(root + "mean.png", *c1),
                                Pixmap(root + "mean.png", *c1, a=0.5))

        self.remove_btn.set_icons(Pixmap(root + "remove.png", *c1),
                                  Pixmap(root + "remove.png", *c1, a=0.5))



    def all_files_requested(self):
        """ Check if results from all eso files are requested. """
        return self.all_files_btn.isChecked() and self.all_files_btn.isEnabled()

    def totals_requested(self):
        """ Check if results from all eso files are requested. """
        return self.totals_btn.isChecked()

    def populate_outputs_group(self):
        """ Populate outputs buttons. """
        populate_group(self.outputs_group, self.outputs_btns)

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
        outputs_btns_layout = QGridLayout(self.outputs_group)
        outputs_btns_layout.setSpacing(0)
        outputs_btns_layout.setContentsMargins(0, 0, 0, 0)
        outputs_btns_layout.setAlignment(Qt.AlignTop)

        self.populate_outputs_group()

    def set_up_interval_btns(self):
        """ Create interval buttons and a parent container. """
        interval_btns_layout = QGridLayout(self.intervals_group)
        interval_btns_layout.setSpacing(0)
        interval_btns_layout.setContentsMargins(0, 0, 0, 0)
        interval_btns_layout.setAlignment(Qt.AlignTop)

        # ~~~~ Interval buttons set up~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        invervals = [TS, H, D, M, A, RP]

        for ivl in invervals:
            btn = QToolButton(self.intervals_group)
            btn.setText(ivl)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setEnabled(False)
            self.interval_btns[ivl] = btn

        self.populate_intervals_group(hide_disabled=False)

    def set_up_units(self):
        """ Set up units options. . """
        # ~~~~ Layout to hold options  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_layout = QGridLayout(self.units_group)
        units_layout.setSpacing(0)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        energy_menu = QMenu(self)
        items = Settings.SI_ENERGY_UNITS + Settings.IP_ENERGY_UNITS
        self.energy_btn = TitledButton(self.units_group, fill_space=True,
                                       title="energy", menu=energy_menu,
                                       items=items, data=items,
                                       def_act_dt=Settings.ENERGY_UNITS)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        power_menu = QMenu(self)
        items = list(dict.fromkeys(Settings.SI_POWER_UNITS
                                   + Settings.IP_POWER_UNITS))
        self.power_btn = TitledButton(self.units_group, fill_space=True,
                                      title="power", menu=power_menu,
                                      items=items, data=items,
                                      def_act_dt=Settings.POWER_UNITS)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        un_syst_menu = QMenu(self)
        items = ["SI", "IP"]
        self.units_sys_btn = TitledButton(self.units_group, fill_space=True,
                                          title="system", menu=un_syst_menu,
                                          items=items, data=items,
                                          def_act_dt=Settings.UNITS_SYSTEM)
        # show only relevant units
        self.filter_energy_power_units(Settings.UNITS_SYSTEM)

        # ~~~~ Rate to energy set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_energy_btn = QToolButton(self.units_group)
        self.rate_energy_btn.setCheckable(True)
        self.rate_energy_btn.setObjectName("rateToEnergyBtn")
        self.rate_energy_btn.setText("rate to\n energy")
        self.rate_energy_btn.setChecked(Settings.RATE_TO_ENERGY)

        self.populate_units_group()

    def set_up_tools(self):
        """ Create a general set of tools. """
        # ~~~~ Layout to hold tools settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        tools_layout = QGridLayout(self.tools_group)
        tools_layout.setSpacing(0)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setAlignment(Qt.AlignTop)

        # ~~~~ Sum variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.sum_btn.setEnabled(False)
        self.sum_btn.setText("sum")

        # ~~~~ Mean variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.mean_btn.setEnabled(False)
        self.mean_btn.setText("mean")

        # ~~~~ Remove variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.remove_btn.setEnabled(False)
        self.remove_btn.setText("remove")

        self.populate_tools_group()

    def get_selected_interval(self):
        """ Get currently selected interval. """
        try:
            return next(k for k, btn in self.interval_btns.items() if btn.isChecked())
        except StopIteration:
            pass

    def set_tools_btns_enabled(self, *args, enabled=True):
        """ Enable tool buttons specified as args. """
        btns = self.tools_btns
        if args:
            # enable all when not explicitly defined
            btns = [btn for btn in btns if btn.text() in args]

        _ = [btn.setEnabled(enabled) for btn in btns]

    def set_initial_layout(self):
        """ Define an app layout when there isn't any file loaded. """
        self.all_files_btn.setEnabled(False)
        self.totals_btn.setEnabled(False)
        self.rate_energy_btn.setEnabled(True)

        for btn in self.interval_btns.values():
            btn.setHidden(False)
            btn.setChecked(False)
            btn.setEnabled(False)

        self.populate_intervals_group(hide_disabled=False)

    def update_rate_to_energy_state(self):
        """ Enable or disable rate to energy button. """
        # rate to energy should be enabled only for daily+ intervals
        if self.custom_units_toggle.isChecked():
            b = self.get_selected_interval() not in [TS, H]
            self.rate_energy_btn.setEnabled(b)
        else:
            self.rate_energy_btn.setEnabled(False)

    def update_intervals_state(self, available_intervals):
        """ Deactivate interval buttons if not applicable. """
        for key, btn in self.interval_btns.items():
            if key in available_intervals:
                btn.setEnabled(True)
            else:
                # interval is not applicable for current eso file
                btn.setEnabled(False)
                btn.setChecked(False)

        # when there isn't any previously selected interval, or the interval
        # is not applicable for current file the first available button will
        # be selected
        interval = self.get_selected_interval()
        if not interval or interval not in available_intervals:
            # select a first enabled interval
            k, btn = next((k, btn) for k, btn in self.interval_btns.items()
                          if btn.isEnabled())

            # store the newly selected interval
            # settingsUpdated signal is deliberately NOT triggered
            btn.setChecked(True)
            Settings.INTERVAL = k

        # display only enabled interval buttons
        self.populate_intervals_group(hide_disabled=True)

    def store_temp_units(self):
        """ Store intermediate units settings. """
        self.temp_settings["energy_units"] = self.energy_btn.data()
        self.temp_settings["power_units"] = self.power_btn.data()
        self.temp_settings["units_system"] = self.units_sys_btn.data()
        self.temp_settings["rate_to_energy"] = self.rate_energy_btn.isChecked()

    def restore_temp_units(self):
        """ Restore units settings. """
        ene = self.temp_settings["energy_units"]
        pw = self.temp_settings["power_units"]
        us = self.temp_settings["units_system"]
        checked = self.temp_settings["rate_to_energy"]

        Settings.ENERGY_UNITS = ene
        Settings.POWER_UNITS = pw
        Settings.UNITS_SYSTEM = us
        Settings.RATE_TO_ENERGY = checked

        self.energy_btn.update_state_internally(ene)
        self.power_btn.update_state_internally(pw)
        self.units_sys_btn.update_state_internally(us)
        self.rate_energy_btn.setChecked(checked)

    def set_units_btns_enabled(self, enabled):
        """ Enable or disable units settings buttons. """

    def set_eplus_units(self):
        """ Reset units to E+ default. """
        self.energy_btn.update_state_internally("J")
        self.power_btn.update_state_internally("W")
        self.units_sys_btn.update_state_internally("SI")

        Settings.ENERGY_UNITS = "J"
        Settings.POWER_UNITS = "W"
        Settings.UNITS_SYSTEM = "SI"
        Settings.RATE_TO_ENERGY = False

        self.rate_energy_btn.setEnabled(False)
        self.rate_energy_btn.setChecked(False)

    def custom_units_toggled(self, state):
        """ Update units settings when custom units toggled. """
        enabled = state == 1

        if not enabled:
            self.store_temp_units()
            self.set_eplus_units()
        else:
            self.restore_temp_units()

        Settings.CUSTOM_UNITS = enabled

        # handle state of energy, power and units system buttons
        for btn in self.units_btns[:3]:
            btn.setEnabled(enabled)

        self.update_rate_to_energy_state()
        self.settingsUpdated.emit()

    def filter_energy_power_units(self, units_system):
        """ Handle displaying allowed units for given units system. """
        if units_system == "IP":
            en_acts = Settings.IP_ENERGY_UNITS
            pw_acts = Settings.IP_POWER_UNITS

        else:
            en_acts = Settings.SI_ENERGY_UNITS
            pw_acts = Settings.SI_POWER_UNITS

        # SI and IP use different energy and power units
        self.energy_btn.filter_visible_actions(en_acts)
        self.power_btn.filter_visible_actions(pw_acts)

        Settings.ENERGY_UNITS = self.energy_btn.data()
        Settings.POWER_UNITS = self.power_btn.data()

    def units_system_changed(self, act):
        """ Request view update when energy units are changed. """
        changed = self.units_sys_btn.update_state(act)

        if changed:
            Settings.UNITS_SYSTEM = act.data()
            self.filter_energy_power_units(act.data())
            self.settingsUpdated.emit()

    def power_units_changed(self, act):
        """ Request view update when energy units are changed. """
        changed = self.power_btn.update_state(act)

        if changed:
            Settings.POWER_UNITS = act.data()
            self.settingsUpdated.emit()

    def energy_units_changed(self, act):
        """ Request view update when energy units are changed. """
        changed = self.energy_btn.update_state(act)

        if changed:
            Settings.ENERGY_UNITS = act.data()
            self.settingsUpdated.emit()

    def totals_toggled(self, state):
        """ Request view update when totals requested. """
        Settings.TOTALS = state
        self.settingsUpdated.emit()

    def rate_to_energy_clicked(self, state):
        """ Request view update when rate to energy button clicked. """
        Settings.RATE_TO_ENERGY = state
        self.settingsUpdated.emit()

    def interval_changed(self):
        """ Request view update when interval changes. """
        Settings.INTERVAL = self.get_selected_interval()
        self.update_rate_to_energy_state()
        self.settingsUpdated.emit()

    def connect_actions(self):
        """ Connect toolbar actions. """
        # ~~~~ Interval buttons Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for btn in self.interval_btns.values():
            btn.clicked.connect(self.settingsUpdated.emit)

        # ~~~~ Totals Signal ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.totals_btn.toggled.connect(self.totals_toggled)

        # ~~~~ Units Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_energy_btn.clicked.connect(self.rate_to_energy_clicked)
        self.custom_units_toggle.stateChanged.connect(self.custom_units_toggled)
        self.energy_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_btn.menu().triggered.connect(self.power_units_changed)
        self.units_sys_btn.menu().triggered.connect(self.units_system_changed)
