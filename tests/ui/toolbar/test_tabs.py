from PySide2.QtCore import Qt

from chartify.settings import Settings


def test_on_tab_changed_first_tab(qtbot, mw, eso_file1):
    eso_file1.id_ = 1
    mw.add_file_widget(eso_file1)
    buttons = [btn.text() for btn in mw.toolbar.table_buttons_group.buttons()]
    assert buttons == ["hourly", "daily", "monthly", "runperiod"]
    assert mw.current_model.tree_node == "type"


def test_on_tab_changed_same_table_available(qtbot, mw_esofile):
    qtbot.mouseClick(mw_esofile.toolbar.get_table_button_by_name("daily"), Qt.LeftButton)
    mw_esofile.standard_tab_wgt.setCurrentIndex(2)
    assert mw_esofile.current_model.name == "daily"


def test_on_tab_changed_same_table_not_available_first_change(qtbot, mw_esofile, eso_file2):
    mw_esofile.standard_tab_wgt.setCurrentIndex(1)
    assert mw_esofile.current_model.name == "hourly"


def test_on_tab_changed_same_table_not_available(qtbot, mw_esofile):
    qtbot.mouseClick(mw_esofile.toolbar.get_table_button_by_name("monthly"), Qt.LeftButton)
    mw_esofile.standard_tab_wgt.setCurrentIndex(1)
    mw_esofile.standard_tab_wgt.setCurrentIndex(0)
    qtbot.mouseClick(mw_esofile.toolbar.get_table_button_by_name("timestep"), Qt.LeftButton)
    mw_esofile.standard_tab_wgt.setCurrentIndex(1)
    assert mw_esofile.current_model.name == "monthly"


def test_on_tab_changed_empty_view(qtbot, mw_esofile):
    qtbot.mouseClick(mw_esofile.toolbar.totals_outputs_btn, Qt.LeftButton)
    mw_esofile.totals_tab_wgt.removeTab(0)
    assert Settings.CURRENT_FILE_ID is None
    assert mw_esofile.toolbar.rate_energy_btn.isEnabled()
    assert len(mw_esofile.toolbar.table_buttons_group.buttons()) == 0
    assert mw_esofile.toolbar.table_group.layout().isEmpty()
