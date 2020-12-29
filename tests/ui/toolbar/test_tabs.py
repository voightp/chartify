from tests.fixtures import *


def test_on_tab_changed_first_tab():
    pytest.fail()


def test_on_tab_changed_same_table_available():
    pytest.fail()


def test_on_tab_changed_same_table_not_available():
    pytest.fail()


def test_on_tab_changed_empty_view(qtbot, mw_esofile):
    qtbot.mouseClick(mw_esofile.toolbar.totals_outputs_btn, Qt.LeftButton)
    mw_esofile.totals_tab_wgt.removeTab(0)
    assert Settings.CURRENT_FILE_ID is None
    assert mw_esofile.toolbar.rate_energy_btn.isEnabled()
    assert not mw_esofile.toolbar.table_buttons
    assert mw_esofile.toolbar.table_group.layout().isEmpty()
