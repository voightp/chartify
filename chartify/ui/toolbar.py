from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (
    QVBoxLayout,
    QGridLayout,
    QToolButton,
    QGroupBox,
    QSizePolicy,
    QMenu,
    QFrame,
    QAction,
)
from esofile_reader.constants import TS, D, H, M, A, RP

from chartify.settings import Settings
from chartify.ui.buttons import TitledButton, ToggleButton, CheckableButton, ClickButton


class Toolbar(QFrame):
    """
    A class to represent application toolbar.

    """

    settingsUpdated = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_settings = {
            "energy_units": Settings.ENERGY_UNITS,
            "power_units": Settings.POWER_UNITS,
            "units_system": Settings.UNITS_SYSTEM,
            "rate_to_energy": Settings.RATE_TO_ENERGY,
        }

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
        self.totals_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.totals_btn.setText("totals")
        self.totals_btn.setEnabled(False)

        self.all_files_btn = CheckableButton(self.outputs_group)
        self.all_files_btn.setText("all files")
        self.all_files_btn.setChecked(Settings.ALL_FILES)
        self.all_files_btn.setEnabled(False)

        self.set_up_outputs_btns()
        self.layout.addWidget(self.outputs_group)

        # ~~~~ Tools group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tools_group = QGroupBox("Tools", self)
        self.tools_group.setObjectName("toolsGroup")

        self.sum_btn = ClickButton(self.tools_group)
        self.sum_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.mean_btn = ClickButton(self.tools_group)
        self.mean_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.remove_btn = ClickButton(self.tools_group)
        self.remove_btn.setIconSize(Settings.ICON_SMALL_SIZE)
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
        self.units_system_button = None
        self.rate_energy_btn = None
        self.set_up_units()

        self.layout.addWidget(self.units_group)

        self.connect_actions()

    @property
    def units_btns(self):
        """ A shorthand to get all units buttons."""
        return [self.energy_btn, self.power_btn, self.units_system_button, self.rate_energy_btn]

    @property
    def tools_btns(self):
        """ A shorthand to get all tools buttons."""
        return [self.sum_btn, self.mean_btn, self.remove_btn]

    @property
    def outputs_btns(self):
        """ A shorthand to get all outputs buttons. """
        return [self.totals_btn, self.all_files_btn]

    @staticmethod
    def populate_group(group, widgets, hide_disabled=False, n_cols=2):
        """ Populate given group with given widgets. """
        layout = group.layout()

        # remove all children of the interface
        for _ in range(layout.count()):
            wgt = layout.itemAt(0).widget()
            layout.removeWidget(wgt)

        if hide_disabled:
            enabled = []
            for wgt in widgets:
                if not wgt.isEnabled():
                    wgt.hide()
                else:
                    wgt.show()
                    enabled.append(wgt)
            widgets = enabled

        n_rows = (len(widgets) if len(widgets) % 2 == 0 else len(widgets) + 1) // n_cols
        ixs = [(x, y) for x in range(n_rows) for y in range(n_cols)]

        for btn, ix in zip(widgets, ixs):
            layout.addWidget(btn, *ix)

    def all_files_requested(self):
        """ Check if results from all eso files are requested. """
        return self.all_files_btn.isChecked() and self.all_files_btn.isEnabled()

    def totals_requested(self):
        """ Check if results from all eso files are requested. """
        return self.totals_btn.isChecked()

    def populate_outputs_group(self):
        """ Populate outputs buttons. """
        self.populate_group(self.outputs_group, self.outputs_btns)

    def populate_intervals_group(self, hide_disabled=True):
        """ Populate interval buttons based on a current state. """
        btns = self.interval_btns.values()
        self.populate_group(self.intervals_group, btns, hide_disabled=hide_disabled)

    def populate_tools_group(self):
        """ Populate tools group layout. """
        self.populate_group(self.tools_group, self.tools_btns)

    def populate_units_group(self):
        """ Populate units group layout. """
        self.populate_group(self.units_group, self.units_btns)

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
        for ivl in [TS, H, D, M, A, RP]:
            btn = QToolButton(self.intervals_group)
            btn.setText(ivl)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setEnabled(False)
            self.interval_btns[ivl] = btn

        self.populate_intervals_group(hide_disabled=False)

    def set_up_units(self):
        """ Set up units options. """

        def create_actions(items, default):
            acts = []
            for item in items:
                act = QAction(item, self)
                act.setCheckable(True)
                act.setData(item)
                acts.append(act)

            def_act = next(act for act in acts if act.data() == default)
            def_act.setChecked(True)
            return acts, def_act

        # ~~~~ Layout to hold options  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_layout = QGridLayout(self.units_group)
        units_layout.setSpacing(0)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        acts, def_act = create_actions(
            Settings.SI_ENERGY_UNITS + Settings.IP_ENERGY_UNITS, Settings.ENERGY_UNITS
        )
        energy_menu = QMenu(self)
        energy_menu.setWindowFlags(QMenu().windowFlags() | Qt.NoDropShadowWindowHint)
        energy_menu.addActions(acts)

        self.energy_btn = TitledButton("energy", self.units_group)
        self.energy_btn.setMenu(energy_menu)
        self.energy_btn.setDefaultAction(def_act)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        items = list(dict.fromkeys(Settings.SI_POWER_UNITS + Settings.IP_POWER_UNITS))
        acts, def_act = create_actions(items, Settings.POWER_UNITS)

        power_menu = QMenu(self)
        power_menu.setWindowFlags(QMenu().windowFlags() | Qt.NoDropShadowWindowHint)
        power_menu.addActions(acts)

        self.power_btn = TitledButton("power", self.units_group)
        self.power_btn.setMenu(power_menu)
        self.power_btn.setDefaultAction(def_act)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        acts, def_act = create_actions(["SI", "IP"], Settings.UNITS_SYSTEM)

        units_system_menu = QMenu(self)
        units_system_menu.setWindowFlags(QMenu().windowFlags() | Qt.NoDropShadowWindowHint)
        units_system_menu.addActions(acts)

        self.units_system_button = TitledButton("system", self.units_group)
        self.units_system_button.setMenu(units_system_menu)
        self.units_system_button.setDefaultAction(def_act)

        # show only relevant units
        self.filter_energy_power_units(Settings.UNITS_SYSTEM)

        # ~~~~ Rate to energy set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_energy_btn = QToolButton(self.units_group)
        self.rate_energy_btn.setCheckable(True)
        self.rate_energy_btn.setObjectName("rateToEnergyBtn")
        self.rate_energy_btn.setText("rate to\n energy")
        self.rate_energy_btn.setChecked(Settings.RATE_TO_ENERGY)

        if Settings.CUSTOM_UNITS == 0:
            self.set_default_units()

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

    def update_rate_to_energy_state(self, interval):
        """ Enable or disable rate to energy button. """
        # rate to energy should be enabled only for daily+ intervals
        if self.custom_units_toggle.isChecked():
            self.rate_energy_btn.setEnabled(interval not in [TS, H])
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
            k, btn = next((k, btn) for k, btn in self.interval_btns.items() if btn.isEnabled())

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
        self.temp_settings["units_system"] = self.units_system_button.data()
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
        self.units_system_button.update_state_internally(us)
        self.rate_energy_btn.setChecked(checked)

    def set_default_units(self):
        """ Reset units to E+ default. """
        self.energy_btn.update_state_internally("J")
        self.power_btn.update_state_internally("W")
        self.units_system_button.update_state_internally("SI")

        Settings.ENERGY_UNITS = "J"
        Settings.POWER_UNITS = "W"
        Settings.UNITS_SYSTEM = "SI"
        Settings.RATE_TO_ENERGY = False

        self.energy_btn.setEnabled(False)
        self.power_btn.setEnabled(False)
        self.units_system_button.setEnabled(False)

        self.rate_energy_btn.setEnabled(False)
        self.rate_energy_btn.setChecked(False)

    def custom_units_toggled(self, state):
        """ Update units settings when custom units toggled. """
        enabled = state == 1

        if not enabled:
            self.store_temp_units()
            self.set_default_units()
        else:
            self.restore_temp_units()
            for btn in self.units_btns[:3]:
                btn.setEnabled(enabled)

        Settings.CUSTOM_UNITS = enabled

        self.update_rate_to_energy_state(Settings.INTERVAL)
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
        changed = self.units_system_button.update_state(act)

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

    def all_files_toggled(self, state):
        """ Request view update when totals requested. """
        # settings does not need to be updated as
        # this does not have an impact on the UI
        Settings.ALL_FILES = state

    def rate_to_energy_clicked(self, state):
        """ Request view update when rate to energy button clicked. """
        Settings.RATE_TO_ENERGY = state
        self.settingsUpdated.emit()

    def interval_changed(self):
        """ Request view update when interval changes. """
        interval = self.get_selected_interval()
        Settings.INTERVAL = interval
        self.update_rate_to_energy_state(interval)
        self.settingsUpdated.emit()

    def connect_actions(self):
        """ Connect toolbar actions. """
        # ~~~~ Interval buttons Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for btn in self.interval_btns.values():
            btn.clicked.connect(self.interval_changed)

        # ~~~~ Totals Signal ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.totals_btn.toggled.connect(self.totals_toggled)

        # ~~~~ All Files Signal ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.all_files_btn.toggled.connect(self.all_files_toggled)

        # ~~~~ Units Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_energy_btn.clicked.connect(self.rate_to_energy_clicked)
        self.custom_units_toggle.stateChanged.connect(self.custom_units_toggled)
        self.energy_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_btn.menu().triggered.connect(self.power_units_changed)
        self.units_system_button.menu().triggered.connect(self.units_system_changed)
