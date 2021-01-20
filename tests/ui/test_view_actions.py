from unittest.mock import patch

import pytest
from PySide2.QtCore import Qt


def test_expand_all_empty(qtbot, mw):
    try:
        qtbot.mouseClick(mw.expand_all_btn, Qt.LeftButton)
    except AttributeError:
        pytest.fail()


def test_expand_all(qtbot, mw_esofile):
    mw_esofile.on_table_change_requested("daily")
    qtbot.mouseClick(mw_esofile.expand_all_btn, Qt.LeftButton)
    assert len(mw_esofile.current_view.get_expanded_labels()) == 4


def test_collapse_all_empty(qtbot, mw):
    try:
        qtbot.mouseClick(mw.collapse_all_btn, Qt.LeftButton)
    except AttributeError:
        pytest.fail()


def test_collapse_all(qtbot, mw_esofile):
    mw_esofile.on_table_change_requested("daily")
    qtbot.mouseClick(mw_esofile.expand_all_btn, Qt.LeftButton)
    qtbot.mouseClick(mw_esofile.collapse_all_btn, Qt.LeftButton)
    assert len(mw_esofile.current_view.get_expanded_labels()) == 0


def test_on_text_edited(qtbot, mw_esofile):
    def cb():
        mock_view.filter_view.assert_called_once_with(
            {"key": "foo", "type": "bar", "proxy_units": "baz"}
        )
        return True

    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        qtbot.wait_signal(mw_esofile.timer.timeout, check_params_cb=cb)
        qtbot.keyClicks(mw_esofile.key_line_edit, "foo")
        qtbot.keyClicks(mw_esofile.type_line_edit, "bar")
        qtbot.keyClicks(mw_esofile.units_line_edit, "baz")

    assert mw_esofile.key_line_edit.text() == "foo"
    assert mw_esofile.type_line_edit.text() == "bar"
    assert mw_esofile.units_line_edit.text() == "baz"
    assert mw_esofile.get_filter_dict() == {"key": "foo", "type": "bar", "proxy_units": "baz"}


def test_on_filter_timeout_empty(qtbot, mw):
    with qtbot.wait_signal(mw.timer.timeout):
        try:
            qtbot.keyClicks(mw.key_line_edit, "foo")
            qtbot.keyClicks(mw.type_line_edit, "bar")
            qtbot.keyClicks(mw.units_line_edit, "baz")
        except AttributeError:
            pytest.fail()


@pytest.mark.parametrize("init_checked, tree_node", [(True, None), (False, "type")])
def test_on_tree_btn_toggled(qtbot, mw_esofile, init_checked, tree_node):
    mw_esofile.tree_act.setChecked(init_checked)
    qtbot.mouseClick(mw_esofile.tree_view_btn, Qt.LeftButton)
    assert mw_esofile.tree_act.isChecked() is not init_checked
    assert mw_esofile.collapse_all_btn.isEnabled() is not init_checked
    assert mw_esofile.expand_all_btn.isEnabled() is not init_checked
    assert mw_esofile.current_model.tree_node == tree_node
