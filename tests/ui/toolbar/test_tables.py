from PySide2.QtCore import Qt


def test_table_change(qtbot, mw_combined_file):
    for button in mw_combined_file.toolbar.table_buttons:
        qtbot.mouseClick(button, Qt.LeftButton)
        assert (
            mw_combined_file.current_model
            is mw_combined_file.current_view.models[button.text()]
        )


def test_table_change_rate_to_energy_not_allowed(qtbot, mw_combined_file):
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[8], Qt.LeftButton)
    assert not mw_combined_file.toolbar.rate_energy_btn.isEnabled()


def test_table_change_rate_to_energy_allowed(qtbot, mw_combined_file):
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[8], Qt.LeftButton)
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[0], Qt.LeftButton)
    assert mw_combined_file.toolbar.rate_energy_btn.isEnabled()


def test_table_change_tree_action_simple_view(qtbot, mw_combined_file):
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[3], Qt.LeftButton)
    assert not mw_combined_file.tree_act.isEnabled()
    assert not mw_combined_file.expand_all_act.isEnabled()
    assert not mw_combined_file.collapse_all_act.isEnabled()


def test_table_change_tree_action(qtbot, mw_combined_file):
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[3], Qt.LeftButton)
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[4], Qt.LeftButton)

    assert mw_combined_file.tree_act.isEnabled()
    assert mw_combined_file.expand_all_act.isEnabled()
    assert mw_combined_file.collapse_all_act.isEnabled()


def test_table_change_empty_view(qtbot, mw_combined_file):
    qtbot.mouseClick(mw_combined_file.toolbar.totals_outputs_btn, Qt.LeftButton)
    assert mw_combined_file.tree_act.isEnabled()
    assert mw_combined_file.expand_all_act.isEnabled()
    assert mw_combined_file.collapse_all_act.isEnabled()
    assert mw_combined_file.toolbar.rate_energy_btn.isEnabled()
