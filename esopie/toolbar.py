from PySide2.QtWidgets import (QVBoxLayout, QGridLayout, QToolButton,
                               QGroupBox, QSpacerItem, QSizePolicy, QMenu,
                               QFrame)
from PySide2.QtCore import QSize, Qt, Signal, QSettings
from PySide2.QtGui import QPixmap, QFont, QColor

from esopie.icons import Pixmap, text_to_pixmap
from esopie.buttons import (TitledButton, ToggleButton, MenuButton,
                            CheckableButton, DualActionButton, ClickButton)

from eso_reader.constants import TS, D, H, M, A, RP

si_energy_units = ["Wh", "kWh", "MWh", "J", "MJ", "GJ"]
si_power_units = ["W", "kW", "MW"]

ip_energy_units = ["Btu", "kBtu", "MBtu"]
ip_power_units = ["Btu/h", "kBtu/h", "MBtu/h", "W"]


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
    totalsChanged = Signal(bool)

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
        self.hide_btn = DualActionButton(self.tools_group)
        self.remove_btn = ClickButton(self.tools_group)
        self.set_up_tools()
        self.layout.addWidget(self.tools_group)

        # ~~~~ Units group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.cstm_uni_tgl = ToggleButton(self)
        self.cstm_uni_tgl.setText("Custom Units")
        self.cstm_uni_tgl.setChecked(True)
        self.layout.addWidget(self.cstm_uni_tgl)

        self.uni_grp = QFrame(self)
        self.uni_grp.setObjectName("unitsGroup")
        self.energy_btn = None
        self.power_btn = None
        self.units_sys_btn = None
        self.rate_ene_btn = None
        self.set_up_units()
        self.layout.addWidget(self.uni_grp)

        spacer = QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addSpacerItem(spacer)

        # ~~~~ Settings group ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.stngs_btn = MenuButton("Settings", self, QSize(40, 40),
                                    icon=QPixmap("../icons/gear.png"))

        self.layout.addWidget(self.stngs_btn)

        self.connect_actions()

    @property
    def units_btns(self):
        """ A shorthand to get all units buttons."""
        return [self.energy_btn,
                self.power_btn,
                self.units_sys_btn,
                self.rate_ene_btn]

    @property
    def tools_btns(self):
        """ A shorthand to get all tools buttons."""
        return [self.sum_btn,
                self.mean_btn,
                self.hide_btn,
                self.remove_btn]

    @property
    def outputs_btns(self):
        """ A shorthand to get all outputs buttons. """
        return [self.totals_btn,
                self.all_files_btn]

    def store_settings(self):
        """ Store toolbar settings. """
        settings = QSettings()

        settings.setValue("Toolbar/energyUnits", self.energy_btn.data())
        settings.setValue("Toolbar/powerUnits", self.power_btn.data())
        settings.setValue("Toolbar/unitsSystem", self.units_sys_btn.data())

        checked = self.rate_ene_btn.isChecked()
        settings.setValue("Toolbar/rateToEnergy", int(checked))

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

        self.hide_btn.set_icons(Pixmap(root + "visibility.png", *c1),
                                Pixmap(root + "visibility.png", *c1, a=0.5),
                                Pixmap(root + "hide.png", *c1),
                                Pixmap(root + "hide.png", *c1, a=0.5))

    def all_files_requested(self):
        """ Check if results from all eso files are requested. """
        btn = self.all_files_btn
        return btn.isChecked() and btn.isEnabled()

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
        populate_group(self.uni_grp, self.units_btns)

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
        settings = QSettings()
        # ~~~~ Layout to hold options  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        units_layout = QGridLayout(self.uni_grp)
        units_layout.setSpacing(0)
        units_layout.setContentsMargins(0, 0, 0, 0)
        units_layout.setAlignment(Qt.AlignLeft)

        # ~~~~ Energy units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        energy_menu = QMenu(self)
        items = si_energy_units + ip_energy_units
        dt = settings.value("Toolbar/energyUnits", "kWh")
        self.energy_btn = TitledButton(self.uni_grp, fill_space=True,
                                       title="energy", menu=energy_menu,
                                       items=items, data=items, def_act_dt=dt)

        # ~~~~ Power units set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        power_menu = QMenu(self)
        items = list(dict.fromkeys(si_power_units + ip_power_units))
        dt = settings.value("Toolbar/powerUnits", "kW")
        self.power_btn = TitledButton(self.uni_grp, fill_space=True,
                                      title="power", menu=power_menu,
                                      items=items, data=items, def_act_dt=dt)

        # ~~~~ Units system set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        un_syst_menu = QMenu(self)
        items = ["SI", "IP"]
        dt = settings.value("Toolbar/unitsSystem", "SI")
        self.units_sys_btn = TitledButton(self.uni_grp, fill_space=True,
                                          title="system", menu=un_syst_menu,
                                          items=items, data=items, def_act_dt=dt)
        self.toggle_units(dt)

        # ~~~~ Rate to energy set up ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.rate_ene_btn = QToolButton(self.uni_grp)
        self.rate_ene_btn.setCheckable(True)
        self.rate_ene_btn.setObjectName("rateToEnergyBtn")
        self.rate_ene_btn.setText("rate to\n energy")
        checked = settings.value("Toolbar/rateToEnergy", 0)
        self.rate_ene_btn.setChecked(bool(checked))

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

        # ~~~~ Mean variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.hide_btn.setEnabled(False)
        self.hide_btn.set_texts("show", "hide")

        # ~~~~ Mean variables button ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.remove_btn.setEnabled(False)
        self.remove_btn.setText("remove")

        self.populate_tools_group()

    def disable_interval_btns(self):
        """ Disable all interval buttons. """
        for btn in self.interval_btns.values():
            btn.setHidden(False)
            btn.setChecked(False)
            btn.setEnabled(False)

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
        self.rate_ene_btn.setEnabled(True)

        self.disable_interval_btns()
        self.populate_intervals_group(hide_disabled=False)

    def update_rate_ene_state(self):
        """ Enable or disable rate to energy button. """
        # handle changing the state on rt_to_ene_btn
        # as this is allowed only for daily+ intervals
        if self.cstm_uni_tgl.isChecked():
            b = self.get_selected_interval() not in [TS, H]
            self.rate_ene_btn.setEnabled(b)
        else:
            self.rate_ene_btn.setEnabled(False)

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
        btn = self.rate_ene_btn
        rate_to_energy = btn.isEnabled() and btn.isChecked()

        units_system = self.units_sys_btn.data()
        energy_units = self.energy_btn.data()
        power_units = self.power_btn.data()

        return rate_to_energy, units_system, energy_units, power_units

    def store_units_settings(self):
        """ Store intermediate units settings. """
        self.temp_settings["energy_units"] = self.energy_btn.data()
        self.temp_settings["power_units"] = self.power_btn.data()
        self.temp_settings["units_system"] = self.units_sys_btn.data()

        checked = self.rate_ene_btn.isChecked()
        self.temp_settings["rate_to_energy"] = checked

    def restore_units_settings(self):
        """ Restore units settings. """
        ene = self.temp_settings["energy_units"]
        pw = self.temp_settings["power_units"]
        us = self.temp_settings["units_system"]

        self.energy_btn.update_state_internally(ene)
        self.power_btn.update_state_internally(pw)
        self.units_sys_btn.update_state_internally(us)

        checked = self.temp_settings["rate_to_energy"]
        self.rate_ene_btn.setChecked(checked)

    def enable_units_buttons(self, enabled):
        """ Enable or disable units settings buttons. """
        for btn in self.units_btns[:3]:
            btn.setEnabled(enabled)

        self.update_rate_ene_state()

    def reset_units_to_default(self):
        """ Reset units to E+ default. """
        self.energy_btn.update_state_internally("J")
        self.power_btn.update_state_internally("W")
        self.units_sys_btn.update_state_internally("SI")

        self.rate_ene_btn.setEnabled(False)
        self.rate_ene_btn.setChecked(False)

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

        self.energy_btn.filter_visible_actions(en_acts)
        self.power_btn.filter_visible_actions(pw_acts)

    def units_system_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.units_sys_btn.update_state(act)

        dt = act.data()
        self.toggle_units(dt)

        if changed:
            self.updateView.emit()

    def power_units_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.power_btn.update_state(act)

        if changed:
            self.updateView.emit()

    def energy_units_changed(self, act):
        """ Update view when energy units are changed. """
        changed = self.energy_btn.update_state(act)

        if changed:
            self.updateView.emit()

    def connect_actions(self):
        """ Connect toolbar actions. """
        # ~~~~ Interval buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        btns = self.interval_btns.values()
        _ = [btn.clicked.connect(self.interval_changed) for btn in btns]

        # ~~~~ Options buttons actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.totals_btn.toggled.connect(self.totals_toggled)

        # ~~~~ Options Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.cstm_uni_tgl.stateChanged.connect(self.units_settings_toggled)
        self.rate_ene_btn.clicked.connect(self.rate_to_energy_toggled)

        # ~~~~ Settings Actions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.energy_btn.menu().triggered.connect(self.energy_units_changed)
        self.power_btn.menu().triggered.connect(self.power_units_changed)
        self.units_sys_btn.menu().triggered.connect(self.units_system_changed)
