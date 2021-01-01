from unittest.mock import patch

from tests.fixtures import *


def test_on_custom_units_toggled(qtbot, mw_combined_file):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(mw_esofile.updateModelRequested):
            mw_esofile.on_custom_units_toggled("kBTU", "MW", "IP", True)
            assert mock_settings.ENERGY_UNITS == "kBTU"
            assert mock_settings.POWER_UNITS == "MW"
            assert mock_settings.UNITS_SYSTEM == "IP"
            assert mock_settings.RATE_TO_ENERGY is rate_to_energy
            assert mw_esofile.toolbar.rate_energy_btn.isEnabled() is rate_to_energy


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
