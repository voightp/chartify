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
    QActionGroup,
)

from chartify.settings import Settings
from chartify.ui.buttons import TitledButton, ToggleButton


class Toolbar(QFrame):
    """
    A class to represent application toolbar.

    """

    tableChangeRequested = Signal(str)
    customUnitsToggled = Signal(str, str, str, bool)

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
        self.totals_btn = QToolButton(self.outputs_group)
        self.totals_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.totals_btn.setCheckable(True)
        self.totals_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.totals_btn.setText("totals")
        self.totals_btn.setEnabled(False)
        self.all_files_btn = QToolButton(self.outputs_group)
        self.all_files_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.all_files_btn.setCheckable(True)
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
        self.sum_btn = QToolButton(self.tools_group)
        self.sum_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.sum_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.sum_btn.setText("sum")
        self.mean_btn = QToolButton(self.tools_group)
        self.mean_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.mean_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.mean_btn.setText("mean")
        self.remove_btn = QToolButton(self.tools_group)
        self.remove_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.remove_btn.setIconSize(Settings.ICON_SMALL_SIZE)
        self.remove_btn.setText("remove")
        self.populate_group(self.tools_group, [self.sum_btn, self.mean_btn, self.remove_btn])
        self.layout.addWidget(self.tools_group)

        # ~~~~ Units group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.units_group = QGroupBox("Units", self)
        self.units_group.setObjectName("unitsGroup")
        self.custom_units_toggle = ToggleButton(self.units_group)
        self.custom_units_toggle.setText("Custom")
        self.custom_units_toggle.setChecked(Settings.CUSTOM_UNITS)
        self.custom_units_toggle.stateChanged.connect(self.custom_units_toggled)
        self.source_units_toggle = ToggleButton(self.units_group)
        self.source_units_toggle.setText("Source")
        self.source_units_toggle.setChecked(not Settings.HIDE_SOURCE_UNITS)
        self.energy_btn = TitledButton("energy", self.units_group)
        self.power_btn = TitledButton("power", self.units_group)
        self.units_system_button = TitledButton("system", self.units_group)
        self.rate_energy_btn = QToolButton(self.units_group)
        self.rate_energy_btn.setCheckable(True)
        self.rate_energy_btn.setObjectName("rateToEnergyBtn")
        self.rate_energy_btn.setText("rate to\n energy")
        self.rate_energy_btn.setChecked(Settings.RATE_TO_ENERGY)
        self.set_up_units()
        self.populate_group(
            self.units_group,
            [self.energy_btn, self.power_btn, self.units_system_button, self.rate_energy_btn],
        )
        self.units_group.layout().addWidget(self.custom_units_toggle, 2, 0, 1, 2)
        self.units_group.layout().addWidget(self.source_units_toggle, 3, 0, 1, 2)
        self.layout.addWidget(self.units_group)

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
            group = QActionGroup(self)
            acts = []
            for text in text_list:
                act = QAction(text, self)
                act.setCheckable(True)
                act.setData(text)
                group.addAction(act)
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

    def enable_rate_to_energy(self, can_convert: bool):
        """ Enable or disable rate to energy button. """
        if self.custom_units_toggle.isChecked():
            self.rate_energy_btn.setEnabled(can_convert)
        else:
            self.rate_energy_btn.setEnabled(False)

    def update_table_buttons(self, table_names: List[str], selected: str):
        """ Populate table group with current table names. """
        self.table_buttons.clear()
        for table in table_names:
            btn = QToolButton(self.table_group)
            btn.setText(table)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(self.on_table_button_clicked)
            if table == selected:
                btn.setChecked(True)
            self.table_buttons.append(btn)
        self.populate_group(self.table_group, self.table_buttons)

    def custom_units_toggled(self, checked: bool) -> None:
        """ Update units settings when custom units toggled. """
        if not checked:
            # set default EnergyPlus units
            energy = "J"
            power = "W"
            units_system = "SI"
            rate_to_energy = False
            # store original settings
            self.temp_settings["energy_units"] = self.energy_btn.data()
            self.temp_settings["power_units"] = self.power_btn.data()
            self.temp_settings["units_system"] = self.units_system_button.data()
            self.temp_settings["rate_to_energy"] = self.rate_energy_btn.isChecked()
        else:
            energy = self.temp_settings["energy_units"]
            power = self.temp_settings["power_units"]
            units_system = self.temp_settings["units_system"]
            rate_to_energy = self.temp_settings["rate_to_energy"]

        self.energy_btn.set_action(energy)
        self.power_btn.set_action(power)
        self.units_system_button.set_action(units_system)
        self.rate_energy_btn.setChecked(rate_to_energy)

        self.energy_btn.setEnabled(checked)
        self.power_btn.setEnabled(checked)
        self.units_system_button.setEnabled(checked)
        self.rate_energy_btn.setEnabled(checked)

        self.customUnitsToggled.emit(energy, power, units_system, rate_to_energy)

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

    def on_table_button_clicked(self):
        """ Request view update when interval changes. """
        table_name = next(btn.text() for btn in self.table_buttons if btn.isChecked())
        self.tableChangeRequested.emit(table_name)
