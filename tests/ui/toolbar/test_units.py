from tests.fixtures import *


def test_initial_units(mw):
    assert mw.toolbar.energy_btn.data() == "kWh"
    assert mw.toolbar.rate_btn.data() == "kW"
    assert mw.toolbar.units_system_button.data() == "SI"
    assert not mw.toolbar.rate_energy_btn.isChecked()


def test_change_energy_units_empty_view(qtbot, mw):
    mw.toolbar.energy_btn.menu().actions()[2].trigger()
    assert mw.toolbar.energy_btn.data() == "MWh"


def test_change_custom_units_to_default(qtbot, mw):
    mw.toolbar.custom_units_toggle.setChecked(False)
    assert mw.toolbar.energy_btn.data() == "J"
    assert mw.toolbar.rate_btn.data() == "W"
    assert mw.toolbar.units_system_button.data() == "SI"
    assert not mw.toolbar.rate_energy_btn.isChecked()
    assert not mw.toolbar.rate_energy_btn.isEnabled()


def test_change_custom_units_to_default_rate_to_energy_checked(qtbot, mw):
    mw.toolbar.rate_energy_btn.setChecked(True)
    mw.toolbar.custom_units_toggle.setChecked(False)
    assert not mw.toolbar.rate_energy_btn.isChecked()
    assert not mw.toolbar.rate_energy_btn.isEnabled()


def test_check_energy_btn_update(qtbot, mw):
    def cb(energy, rate, system, rate_to_energy):
        return energy == "Wh"

    with qtbot.wait_signal(mw.toolbar.unitsChanged, check_params_cb=cb):
        mw.toolbar.energy_btn.menu().actions()[0].trigger()


def test_check_rate_btn_update(qtbot, mw):
    def cb(energy, rate, system, rate_to_energy):
        return rate == "W"

    with qtbot.wait_signal(mw.toolbar.unitsChanged, check_params_cb=cb):
        mw.toolbar.rate_btn.menu().actions()[0].trigger()


def test_check_units_system_btn_update(qtbot, mw):
    def cb(energy, rate, system, rate_to_energy):
        return system == "IP"

    with qtbot.wait_signal(mw.toolbar.unitsChanged, check_params_cb=cb):
        mw.toolbar.units_system_button.menu().actions()[1].trigger()


def test_check_rate_to_energy_btn_update(qtbot, mw):
    def cb(energy, rate, system, rate_to_energy):
        return rate_to_energy is True

    with qtbot.wait_signal(mw.toolbar.unitsChanged, check_params_cb=cb):
        qtbot.mouseClick(mw.toolbar.rate_energy_btn, Qt.LeftButton)


def test_cached_units(qtbot, mw):
    mw.toolbar.rate_energy_btn.setChecked(True)
    mw.toolbar.custom_units_toggle.setChecked(False)
    mw.toolbar.custom_units_toggle.setChecked(True)
    assert mw.toolbar.energy_btn.data() == "kWh"
    assert mw.toolbar.rate_btn.data() == "kW"
    assert mw.toolbar.units_system_button.data() == "SI"
    assert mw.toolbar.rate_energy_btn.isChecked()


def test_rate_to_energy_when_rate_to_energy_not_allowed(qtbot, mw_combined_file):
    mw_combined_file.toolbar.rate_energy_btn.setChecked(True)
    mw_combined_file.on_table_change_requested("monthly-no-ndays")
    # assert not mw_combined_file.toolbar.rate_energy_btn.isChecked()
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()
    assert not Settings.RATE_TO_ENERGY


def test_custom_units_toggle_when_rate_to_energy_not_allowed(qtbot, mw_combined_file):
    mw_combined_file.toolbar.rate_energy_btn.setChecked(True)
    with qtbot.wait_signal(mw_combined_file.toolbar.tableChangeRequested):
        qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[8], Qt.LeftButton)
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()
    assert not Settings.RATE_TO_ENERGY
