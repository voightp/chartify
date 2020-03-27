from unittest.mock import patch

import pytest
from PySide2.QtCore import QMargins, Qt
from PySide2.QtWidgets import QSizePolicy

from chartify.ui.treeview_tools import ViewTools
from chartify.utils.utils import FilterTuple


@pytest.fixture
def view_tools(qtbot):
    with patch("chartify.ui.treeview_tools.Settings") as mock_settings:
        mock_settings.TREE_VIEW = False
        tools = ViewTools()
        tools.show()
        qtbot.add_widget(tools)
        return tools


def test_init_view_tools(view_tools):
    assert view_tools.objectName() == "viewTools"
    assert view_tools.layout().spacing() == 6
    assert view_tools.contentsMargins() == QMargins(0, 0, 0, 0)

    assert view_tools.tree_view_btn.objectName() == "treeButton"
    assert not view_tools.tree_view_btn.isChecked()
    assert view_tools.collapse_all_btn.objectName() == "collapseButton"
    assert not view_tools.collapse_all_btn.isChecked()
    assert view_tools.expand_all_btn.objectName() == "expandButton"
    assert not view_tools.expand_all_btn.isChecked()
    assert view_tools.filter_icon.objectName() == "filterIcon"

    assert view_tools.variable_line_edit.placeholderText() == "variable..."
    assert view_tools.variable_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    )
    assert view_tools.variable_line_edit.width() == 100

    assert view_tools.key_line_edit.placeholderText() == "key..."
    assert view_tools.key_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert view_tools.key_line_edit.width() == 100

    assert view_tools.units_line_edit.placeholderText() == "units..."
    assert view_tools.units_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert view_tools.units_line_edit.width() == 50


def test_tree_requested(qtbot, view_tools):
    with patch("chartify.ui.treeview_tools.Settings") as mock_settings:
        assert not view_tools.tree_requested()

        qtbot.mouseClick(view_tools.tree_view_btn, Qt.LeftButton)
        assert view_tools.tree_requested()
        assert mock_settings.TREE_VIEW


def test_get_filter_tup(qtbot, view_tools):
    test_filter = FilterTuple(key="foo", variable="bar", units="baz")
    signals = [view_tools.timer.timeout, view_tools.textFiltered]
    callbacks = [None, lambda x: x == test_filter]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        qtbot.keyClicks(view_tools.key_line_edit, "foo")
        qtbot.keyClicks(view_tools.variable_line_edit, "bar")
        qtbot.keyClicks(view_tools.units_line_edit, "baz")

    assert view_tools.key_line_edit.text() == "foo"
    assert view_tools.variable_line_edit.text() == "bar"
    assert view_tools.units_line_edit.text() == "baz"

    assert view_tools.get_filter_tup() == test_filter


def test_toggle_tree_button(qtbot, view_tools):
    with patch("chartify.ui.treeview_tools.Settings") as mock_settings:

        def test_tree_btn_toggled(checked):
            assert view_tools.tree_view_btn.property("checked")
            assert view_tools.collapse_all_btn.isEnabled()
            assert view_tools.expand_all_btn.isEnabled()
            assert mock_settings.TREE_VIEW

            return checked

        callbacks = [test_tree_btn_toggled, None]
        signals = [view_tools.tree_view_btn.toggled, view_tools.structureChanged]
        with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
            qtbot.mouseClick(view_tools.tree_view_btn, Qt.LeftButton)


def test_expand_all(qtbot, view_tools):
    view_tools.expand_all_btn.setEnabled(True)
    with qtbot.wait_signal(view_tools.expandRequested):
        qtbot.mouseClick(view_tools.expand_all_btn, Qt.LeftButton)


def test_collapse_all(qtbot, view_tools):
    view_tools.collapse_all_btn.setEnabled(True)
    with qtbot.wait_signal(view_tools.collapseRequested):
        qtbot.mouseClick(view_tools.collapse_all_btn, Qt.LeftButton)
