from typing import List

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

from chartify.settings import Settings
from chartify.ui.buttons import TitledButton, ToggleButton, CheckableButton, ClickButton


class Toolbar(QFrame):
    """
    A class to represent application toolbar.

    """

    unitsChanged = Signal(str, str, str, bool)
    tableChangeRequested = Signal(str)

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

        # ~~~~ Tables group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.table_buttons = []
        self.table_group = QGroupBox("Tables", self)
        self.table_group.setObjectName("tablesGroup")
        table_buttons_layout = QGridLayout(self.table_group)
        table_buttons_layout.setSpacing(0)
        table_buttons_layout.setContentsMargins(0, 0, 0, 0)
        table_buttons_layout.setAlignment(Qt.AlignTop)
        self.layout.addWidget(self.table_group)

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
        outputs_buttons_layout = QGridLayout(self.outputs_group)
        outputs_buttons_layout.setSpacing(0)
        outputs_buttons_layout.setContentsMargins(0, 0, 0, 0)
        outputs_buttons_layout.setAlignment(Qt.AlignTop)
        self.populate_group(self.outputs_group, [self.totals_btn, self.all_files_btn])
        self.layout.addWidget(self.outputs_group)

        # ~~~~ Tools group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.tools_group = QGroupBox("Tools", self)
        self.tools_group.setObjectName("toolsGroup")
        tools_layout = QGridLayout(self.tools_group)
        tools_layout.setSpacing(0)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setAlignment(Qt.AlignTop)
        self.sum_btn = ClickButton(self.tools_group)
        self.sum_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.sum_btn.setEnabled(False)
        self.sum_btn.setText("sum")
        self.mean_btn = ClickButton(self.tools_group)
        self.mean_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.mean_btn.setEnabled(False)
        self.mean_btn.setText("mean")
        self.remove_btn = ClickButton(self.tools_group)
        self.remove_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.remove_btn.setEnabled(False)
        self.remove_btn.setText("remove")
        self.populate_group(self.tools_group, [self.sum_btn, self.mean_btn, self.remove_btn])
        self.layout.addWidget(self.tools_group)

        # ~~~~ Units group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.custom_units_toggle = ToggleButton(self)
        self.custom_units_toggle.setText("Custom Units")
        self.custom_units_toggle.setChecked(Settings.CUSTOM_UNITS)
        self.layout.addWidget(self.custom_units_toggle)
        self.units_group = QFrame(self)
        self.units_group.setObjectName("unitsGroup")
        self.energy_btn = TitledButton("energy", self.units_group)
        self.power_btn = TitledButton("power", self.units_group)
        self.units_system_button = TitledButton("system", self.units_group)
        self.rate_energy_btn = QToolButton(self.units_group)
        self.set_up_units()
        self.layout.addWidget(self.units_group)

        self.connect_actions()

    @staticmethod
    def clear_group(group):
        """ Delete all widgets from given group. """
        for _ in range(group.layout().count()):
            wgt = group.layout().itemAt(0).widget()
            group.layout().removeWidget(wgt)
            wgt.deleteLater()

    def populate_group(self, group, widgets, hide_disabled=False, n_cols=2):
        """ Populate given group with given widgets. """
        # remove all children of the interface
        self.clear_group(group)

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
            group.layout().addWidget(btn, *ix)

    def all_files_requested(self):
        """ Check if results from all eso files are requested. """
        return self.all_files_btn.isChecked() and self.all_files_btn.isEnabled()

    def totals_requested(self):
        """ Check if results from all eso files are requested. """
        return self.totals_btn.isChecked()

    def set_up_units(self):
        """ Set up units options. """

        def create_actions(text_list, default):
            acts = []
            for text in text_list:
                act = QAction(text, self)
                act.setCheckable(True)
                act.setData(text)
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
        actions, default_action = create_actions(
            Settings.SI_ENERGY_UNITS + Settings.IP_ENERGY_UNITS, Settings.ENERGY_UNITS
        )
        energy_menu = QMenu(self)
        energy_menu.setWindowFlags(QMenu().windowFlags() | Qt.NoDropShadowWindowHint)
        energy_menu.addActions(actions)

        self.energy_btn.setMenu(energy_menu)
        self.energy_btn.setDefaultAction(default_action)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        items = list(dict.fromkeys(Settings.SI_POWER_UNITS + Settings.IP_POWER_UNITS))
        actions, default_action = create_actions(items, Settings.POWER_UNITS)

        power_menu = QMenu(self)
        power_menu.setWindowFlags(QMenu().windowFlags() | Qt.NoDropShadowWindowHint)
        power_menu.addActions(actions)

        self.power_btn.setMenu(power_menu)
        self.power_btn.setDefaultAction(default_action)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        actions, default_action = create_actions(["SI", "IP"], Settings.UNITS_SYSTEM)

        units_system_menu = QMenu(self)
        units_system_menu.setWindowFlags(QMenu().windowFlags() | Qt.NoDropShadowWindowHint)
        units_system_menu.addActions(actions)

        self.units_system_button.setMenu(units_system_menu)
        self.units_system_button.setDefaultAction(default_action)

        # show only relevant units
        self.filter_energy_power_units(Settings.UNITS_SYSTEM)

        # ~~~~ Rate to energy set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_energy_btn.setCheckable(True)
        self.rate_energy_btn.setObjectName("rateToEnergyBtn")
        self.rate_energy_btn.setText("rate to\n energy")
        self.rate_energy_btn.setChecked(Settings.RATE_TO_ENERGY)
        self.populate_group(
            self.units_group,
            [self.energy_btn, self.power_btn, self.units_system_button, self.rate_energy_btn],
        )

    def set_initial_layout(self):
        """ Define an app layout when there isn't any file loaded. """
        self.all_files_btn.setEnabled(False)
        self.totals_btn.setEnabled(False)
        self.rate_energy_btn.setEnabled(True)
        self.clear_group(self.table_group)

    def update_rate_to_energy(self, can_convert: bool):
        """ Enable or disable rate to energy button. """
        if self.custom_units_toggle.isChecked():
            self.rate_energy_btn.setEnabled(can_convert)
        else:
            self.rate_energy_btn.setEnabled(False)

    def update_table_buttons(self, table_names: List[str], selected: str):
        """ Populate table group with current table names. """
        for table in table_names:
            btn = QToolButton(self.table_group)
            btn.setText(table)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setEnabled(False)
            btn.clicked.connect(self.table_changed)
            if table == selected:
                btn.setChecked(True)
            self.table_buttons.append(btn)
        self.populate_group(self.table_group, self.table_buttons)

    def units_changed(self):
        """ Notify main app that units settings have changed. """
        self.unitsChanged.emit(
            self.energy_btn.data(),
            self.power_btn.data(),
            self.units_system_button.data(),
            self.rate_energy_btn.isChecked(),
        )

    def set_default_units(self) -> None:
        """ Reset units to E+ default. """
        self.energy_btn.update_state_internally("J")
        self.power_btn.update_state_internally("W")
        self.units_system_button.update_state_internally("SI")
        self.energy_btn.setEnabled(False)
        self.power_btn.setEnabled(False)
        self.units_system_button.setEnabled(False)
        self.rate_energy_btn.setEnabled(False)
        self.rate_energy_btn.setChecked(False)
        self.units_changed()

    def custom_units_toggled(self, state: int) -> None:
        """ Update units settings when custom units toggled. """
        enabled = state == 1
        if not enabled:
            self.temp_settings["energy_units"] = self.energy_btn.data()
            self.temp_settings["power_units"] = self.power_btn.data()
            self.temp_settings["units_system"] = self.units_system_button.data()
            self.temp_settings["rate_to_energy"] = self.rate_energy_btn.isChecked()
            self.set_default_units()
        else:
            energy = self.temp_settings["energy_units"]
            power = self.temp_settings["power_units"]
            units_system = self.temp_settings["units_system"]
            checked = self.temp_settings["rate_to_energy"]

            self.energy_btn.update_state_internally(energy)
            self.power_btn.update_state_internally(power)
            self.units_system_button.update_state_internally(units_system)
            self.rate_energy_btn.setChecked(checked)

            self.energy_btn.setEnabled(enabled)
            self.power_btn.setEnabled(enabled)
            self.units_system_button.setEnabled(enabled)

        self.units_changed()

    def filter_energy_power_units(self, units_system: str):
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

    def units_system_changed(self, act):
        """ Request view update when energy units are changed. """
        changed = self.units_system_button.update_state(act)
        if changed:
            self.filter_energy_power_units(act.data())
            self.units_changed()

    def power_units_changed(self, act):
        """ Request view update when energy units are changed. """
        changed = self.power_btn.update_state(act)
        if changed:
            self.units_changed()

    def energy_units_changed(self, act):
        """ Request view update when energy units are changed. """
        changed = self.energy_btn.update_state(act)
        if changed:
            self.units_changed()

    def totals_toggled(self, state):
        """ Request view update when totals requested. """
        # TODO handle totals
        Settings.TOTALS = state

    def all_files_toggled(self, state):
        """ Request view update when totals requested. """
        # settings does not need to be updated as
        # this does not have an impact on the UI
        Settings.ALL_FILES = state

    def table_changed(self):
        """ Request view update when interval changes. """
        table_name = next(btn.text() for btn in self.table_buttons if btn.isChecked())
        self.tableChangeRequested.emit(table_name)

    def connect_actions(self):
        """ Connect toolbar actions. """
        # ~~~~ Totals Signal ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.totals_btn.toggled.connect(self.totals_toggled)

        # ~~~~ All Files Signal ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.all_files_btn.toggled.connect(self.all_files_toggled)

        # ~~~~ Units Signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_energy_btn.clicked.connect(self.unitsChanged.emit)
        self.custom_units_toggle.stateChanged.connect(self.custom_units_toggled)
        self.energy_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_btn.menu().triggered.connect(self.power_units_changed)
        self.units_system_button.menu().triggered.connect(self.units_system_changed)
