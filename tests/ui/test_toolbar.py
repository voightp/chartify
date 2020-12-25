from unittest.mock import patch

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QAction

from tests.fixtures import *


def test_output_types(mw, qtbot):
    expected = [mw.standard_tab_wgt, mw.totals_tab_wgt, mw.diff_tab_wgt]
    buttons = [
        mw.toolbar.standard_outputs_btn,
        mw.toolbar.totals_outputs_btn,
        mw.toolbar.diff_outputs_btn,
    ]
    for i in range(mw.tab_stacked_widget.count()):
        qtbot.mouseClick(buttons[i], Qt.LeftButton)
        assert mw.current_tab_widget is expected[i]


def test_table_change(eso_file_mw, qtbot):
    buttons = [btn for btn in eso_file_mw.toolbar.table_buttons]
    for button in buttons:
        qtbot.mouseClick(button, Qt.LeftButton)
        assert eso_file_mw.current_model is eso_file_mw.current_view.models[button.text()]


def test_table_change_requested(mw):
    with patch("chartify.ui.main_window.MainWindow.on_table_change_requested") as func_mock:
        mw.toolbar.tableChangeRequested.emit("test")
        func_mock.assert_called_once_with("test")


def test_on_rate_energy_btn_checked(qtbot, mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(mw.updateModelRequested):
            mw.on_rate_energy_btn_checked(True)
            assert mock_settings.RATE_TO_ENERGY is True


def test_on_source_units_toggled(mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
            mw.on_source_units_toggled(True)
            assert mock_settings.HIDE_SOURCE_UNITS is False
            mock_view.hide_section.assert_called_once_with("units", False)


@pytest.mark.parametrize("allow_rate_to_energy,rate_to_energy", [(True, True), (False, False)])
def test_on_custom_units_toggled(
    qtbot, eso_file_mw, allow_rate_to_energy: bool, rate_to_energy: bool
):
    eso_file_mw.current_view.source_model.allow_rate_to_energy = allow_rate_to_energy
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(eso_file_mw.updateModelRequested):
            eso_file_mw.on_custom_units_toggled("kBTU", "MW", "IP", True)
            assert mock_settings.ENERGY_UNITS == "kBTU"
            assert mock_settings.POWER_UNITS == "MW"
            assert mock_settings.UNITS_SYSTEM == "IP"
            assert mock_settings.RATE_TO_ENERGY is rate_to_energy
            assert eso_file_mw.toolbar.rate_energy_btn.isEnabled() is rate_to_energy


def test_on_energy_units_changed(qtbot, mw):
    act = QAction()
    act.setData("FOO")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mock_settings.ENERGY_UNITS = "FOO"


def test_on_power_units_changed(qtbot, mw):
    act = QAction()
    act.setData("FOO")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mock_settings.POWER_UNITS = "FOO"


def test_on_units_system_changed(qtbot, mw):
    act = QAction()
    act.setData("FOO")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mw.on_units_system_changed(act)
        mock_settings.UNITS_SYSTEM = "FOO"


def test_connect_totals_btn(qtbot, mw):
    mw.toolbar.totals_outputs_btn.setEnabled(True)
    with patch("chartify.ui.main_window.MainWindow.on_totals_checked") as mock_func:
        qtbot.mouseClick(mw.toolbar.totals_toggle, Qt.LeftButton)
        mock_func.assert_called_once_with(True)


def test_connect_all_files_btn(qtbot, mw):
    mw.toolbar.all_files_btn.setEnabled(True)
    with patch("chartify.ui.main_window.MainWindow.on_all_files_toggled") as mock_func:
        qtbot.mouseClick(mw.toolbar.all_files_toggle, Qt.LeftButton)
        mock_func.assert_called_once_with(True)


def test_connect_tableChangeRequested(mw):
    with patch("chartify.ui.main_window.MainWindow.on_table_change_requested") as mock_func:
        mw.toolbar.tableChangeRequested.emit("foo")
        mock_func.assert_called_once_with("foo")


def test_connect_customUnitsToggled(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_custom_units_toggled") as mock_func:
        mw.toolbar.customUnitsToggled.emit("foo", "bar", "baz", True)
        mock_func.assert_called_once_with("foo", "bar", "baz", True)


def test_connect_source_units_toggle(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_source_units_toggled") as mock_func:
        mw.toolbar.source_units_toggle.stateChanged.emit(True)
        mock_func.assert_called_once_with(True)


def test_connect_rate_energy_btn(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_rate_energy_btn_checked") as mock_func:
        qtbot.mouseClick(mw.toolbar.rate_energy_btn, Qt.LeftButton)
        mock_func.assert_called_once_with(True)


def test_connect_energy_btn(mw):
    with patch("chartify.ui.main_window.MainWindow.on_energy_units_changed") as mock_func:
        act = mw.toolbar.energy_btn.menu().actions()[0]
        act.trigger()
        mock_func.assert_called_once_with(act)


def test_connect_power_btn(mw):
    with patch("chartify.ui.main_window.MainWindow.on_power_units_changed") as mock_func:
        act = mw.toolbar.power_btn.menu().actions()[0]
        act.trigger()
        mock_func.assert_called_once_with(act)


def test_connect_units_system_button(mw):
    with patch("chartify.ui.main_window.MainWindow.on_units_system_changed") as mock_func:
        act = mw.toolbar.units_system_button.menu().actions()[0]
        act.trigger()
        mock_func.assert_called_once_with(act)


def test_connect_rate_energy_toggle(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_rate_energy_btn_checked") as func_mock:
        qtbot.mouseClick(mw.toolbar.rate_energy_btn, Qt.LeftButton)
        func_mock.assert_called_once_with(True)
