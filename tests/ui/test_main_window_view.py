from typing import List, Optional
from unittest.mock import patch

from PySide2.QtCore import Qt

from chartify.utils.utils import FilterTuple, VariableData
from tests.fixtures import *


def test_expand_all_empty(mw):
    try:
        mw.expand_all()
    except AttributeError:
        pytest.fail()


def test_expand_all(qtbot, eso_file_mw):
    eso_file_mw.on_table_change_requested("daily")
    qtbot.mouseClick(eso_file_mw.expand_all_btn, Qt.LeftButton)
    assert len(eso_file_mw.current_view.source_model.expanded) == 28


def test_collapse_all_empty(mw):
    try:
        mw.collapse_all()
    except AttributeError:
        pytest.fail()


def test_collapse_all(qtbot, eso_file_mw):
    eso_file_mw.on_table_change_requested("daily")
    qtbot.mouseClick(eso_file_mw.expand_all_btn, Qt.LeftButton)
    qtbot.mouseClick(eso_file_mw.collapse_all_btn, Qt.LeftButton)
    assert len(eso_file_mw.current_view.source_model.expanded) == 0


@pytest.mark.parametrize(
    "variables,enabled,rate_to_energy",
    [
        ([VariableData("A", "B", "C"), VariableData("C", "D", "kWh")], False, False,),
        ([VariableData("A", "B", "C"), VariableData("C", "D", "C")], True, False),
        ([VariableData("A", "B", "J"), VariableData("C", "D", "W")], False, False,),
        ([VariableData("A", "B", "J"), VariableData("C", "D", "W")], True, True),
    ],
)
def test_on_selection_populated(
    qtbot, eso_file_mw, variables: List[VariableData], enabled: bool, rate_to_energy: bool
):
    def cb(vd):
        return vd == variables

    qtbot.stop()

    with qtbot.wait_signal(eso_file_mw.selectionChanged, check_params_cb=cb):
        eso_file_mw.current_view.
        mw.on_selection_populated(variables)
        assert mw.remove_variables_act.isEnabled()
        assert mw.toolbar.remove_btn.isEnabled()
        assert mw.toolbar.sum_btn.isEnabled() == enabled
        assert mw.toolbar.mean_btn.isEnabled() == enabled


def test_on_selection_cleared(qtbot, mw):
    with qtbot.wait_signal(mw.selectionChanged, check_params_cb=lambda x: x == []):
        mw.on_selection_cleared()
        assert not mw.remove_variables_act.isEnabled()
        assert not mw.toolbar.sum_btn.isEnabled()
        assert not mw.toolbar.mean_btn.isEnabled()
        assert not mw.toolbar.remove_btn.isEnabled()


def test_on_tree_node_changed(qtbot, mw):
    with qtbot.wait_signal(mw.updateModelRequested):
        with patch("chartify.ui.main_window.Settings") as mock_settings:
            mw.on_tree_node_changed("foo")
            assert mock_settings.TREE_NODE == "foo"


def test_get_filter_tuple(qtbot, mw):
    mw.key_line_edit.setText("foo")
    mw.type_line_edit.setText("bar")
    mw.units_line_edit.setText("baz")
    assert FilterTuple("foo", "bar", "baz") == mw.get_filter_tuple()


@pytest.mark.parametrize("checked,tree_node", [(True, "type"), (False, None)])
def test_on_tree_btn_toggled(qtbot, mw, checked: bool, tree_node: Optional[str]):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mw.tree_act.setChecked(not checked)
        with qtbot.wait_signal(mw.updateModelRequested):
            qtbot.mouseClick(mw.tree_view_btn, Qt.LeftButton)
            assert mw.tree_act.isChecked() is checked
            assert mw.collapse_all_btn.isEnabled() is checked
            assert mw.expand_all_btn.isEnabled() is checked
            assert mock_settings.TREE_NODE == tree_node


def test_on_text_edited(qtbot, eso_file_mw):
    def cb():
        mock_view.filter_view.assert_called_once_with(FilterTuple("foo", "bar", "baz"))
        return True

    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        qtbot.wait_signal(eso_file_mw.timer.timeout, check_params_cb=cb)
        qtbot.keyClicks(eso_file_mw.key_line_edit, "foo")
        qtbot.keyClicks(eso_file_mw.type_line_edit, "bar")
        qtbot.keyClicks(eso_file_mw.units_line_edit, "baz")

    assert eso_file_mw.key_line_edit.text() == "foo"
    assert eso_file_mw.type_line_edit.text() == "bar"
    assert eso_file_mw.units_line_edit.text() == "baz"
    assert eso_file_mw.get_filter_tuple() == FilterTuple("foo", "bar", "baz")


def test_on_filter_timeout_empty(mw):
    mw.key_line_edit.setText("foo")
    mw.type_line_edit.setText("bar")
    mw.units_line_edit.setText("baz")
    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        mw.on_filter_timeout()
        assert not mock_view.filter_view.called


def test_on_filter_timeout(eso_file_mw):
    eso_file_mw.key_line_edit.setText("foo")
    eso_file_mw.type_line_edit.setText("bar")
    eso_file_mw.units_line_edit.setText("baz")
    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        eso_file_mw.on_filter_timeout()
        mock_view.filter_view.assert_called_once_with(FilterTuple("foo", "bar", "baz"))

def test_connect_type_line_edit(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_text_edited") as mock_func:
        qtbot.keyClicks(mw.type_line_edit, "foo")
        mock_func.assert_called_with()


def test_connect_key_line_edit(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_text_edited") as mock_func:
        qtbot.keyClicks(mw.key_line_edit, "foo")
        mock_func.assert_called_with()


def test_connect_units_line_edit(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_filter_timeout") as mock_func:
        mw.timer.timeout.emit()
        mock_func.assert_called_once_with()


def test_connect_timer(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_filter_timeout") as mock_func:
        mw.timer.timeout.emit()
        mock_func.assert_called_once_with()


