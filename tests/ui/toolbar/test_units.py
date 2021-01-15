from PySide2.QtCore import Qt


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
    with qtbot.wait_signal(mw.toolbar.unitsChanged):
        mw.toolbar.energy_btn.menu().actions()[0].trigger()
    assert mw.toolbar.current_units["energy_units"] == "Wh"


def test_check_energy_btn_view(qtbot, mw_combined_file):
    mw_combined_file.toolbar.energy_btn.menu().actions()[0].trigger()
    units = mw_combined_file.current_model.data(mw_combined_file.current_model.index(9, 2))
    assert "Wh" == units


def test_check_rate_btn_update(qtbot, mw):
    with qtbot.wait_signal(mw.toolbar.unitsChanged):
        mw.toolbar.rate_btn.menu().actions()[0].trigger()
    assert "W" == mw.toolbar.current_units["rate_units"]


def test_check_rate_btn_view(qtbot, mw_combined_file):
    mw_combined_file.toolbar.rate_btn.menu().actions()[0].trigger()
    units = mw_combined_file.current_model.data(mw_combined_file.current_model.index(0, 2))
    assert "W" == units


def test_check_units_system_btn_update(qtbot, mw):
    with qtbot.wait_signal(mw.toolbar.unitsChanged):
        mw.toolbar.units_system_button.menu().actions()[1].trigger()
    assert mw.toolbar.current_units["units_system"] == "IP"


def test_check_units_system_btn_view(qtbot, mw_combined_file):
    mw_combined_file.toolbar.units_system_button.menu().actions()[1].trigger()
    units = mw_combined_file.current_model.data(mw_combined_file.current_model.index(22, 2))
    assert "F" == units


def test_check_rate_to_energy_btn_update(qtbot, mw):
    with qtbot.wait_signal(mw.toolbar.unitsChanged):
        qtbot.mouseClick(mw.toolbar.rate_energy_btn, Qt.LeftButton)
    assert mw.toolbar.current_units["rate_to_energy"] is True


def test_check_rate_to_energy_btn_view(qtbot, mw_combined_file):
    qtbot.mouseClick(mw_combined_file.toolbar.rate_energy_btn, Qt.LeftButton)
    mw_combined_file.toolbar.rate_btn.menu().actions()[0].trigger()
    units = mw_combined_file.current_model.data(mw_combined_file.current_model.index(10, 2))
    assert "kWh" == units


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
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()


def test_rate_to_energy_not_allowed_on_table_change(qtbot, mw_combined_file):
    mw_combined_file.toolbar.rate_energy_btn.setChecked(True)
    with qtbot.wait_signal(mw_combined_file.toolbar.tableChangeRequested):
        qtbot.mouseClick(
            mw_combined_file.toolbar.get_table_button_by_name("monthly-no-ndays"), Qt.LeftButton
        )
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()


def test_custom_units_toggle_when_rate_to_energy_not_allowed(qtbot, mw_combined_file):
    mw_combined_file.toolbar.custom_units_toggle.setChecked(False)
    with qtbot.wait_signal(mw_combined_file.toolbar.tableChangeRequested):
        qtbot.mouseClick(
            mw_combined_file.toolbar.get_table_button_by_name("monthly-no-ndays"), Qt.LeftButton
        )
    mw_combined_file.toolbar.custom_units_toggle.setChecked(True)
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()


def test_custom_units_toggle_when_(qtbot, mw_combined_file):
    mw_combined_file.toolbar.rate_energy_btn.setChecked(True)
    with qtbot.wait_signal(mw_combined_file.toolbar.tableChangeRequested):
        qtbot.mouseClick(
            mw_combined_file.toolbar.get_table_button_by_name("monthly-no-ndays"), Qt.LeftButton
        )
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()


def test_show_source_units(qtbot, mw_combined_file):
    mw_combined_file.toolbar.source_units_toggle.setChecked(True)
    source_units_column = mw_combined_file.current_model.get_logical_column_number("units")
    assert not mw_combined_file.current_view.header().isSectionHidden(source_units_column)
