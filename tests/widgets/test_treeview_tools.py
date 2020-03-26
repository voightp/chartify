from unittest.mock import patch

import pytest
from PySide2.QtCore import QMargins, Qt
from PySide2.QtWidgets import QSizePolicy

from chartify.utils.utils import FilterTuple
from tests.mock_settings import MockSettings, TestTuple


@pytest.fixture
def view_tools_and_settings(qtbot):
    with patch("chartify.settings.Settings", MockSettings) as mock_settings:
        from chartify.ui.treeview_tools import ViewTools

        tools = ViewTools()
        tools.show()
        qtbot.add_widget(tools)
        tt = TestTuple(widget=tools, settings=mock_settings)
        return tt


@pytest.fixture
def view_tools(qtbot, view_tools_and_settings):
    return view_tools_and_settings.widget


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


def test_tree_requested(view_tools):
    assert not view_tools.tree_view_btn.isChecked()


def test_get_filter_tup(qtbot, view_tools):
    qtbot.keyClicks(view_tools.key_line_edit, "foo")
    qtbot.keyClicks(view_tools.variable_line_edit, "bar")
    qtbot.keyClicks(view_tools.units_line_edit, "baz")

    assert view_tools.key_line_edit.text() == "foo"
    assert view_tools.variable_line_edit.text() == "bar"
    assert view_tools.units_line_edit.text() == "baz"

    assert view_tools.get_filter_tup() == FilterTuple(key="foo", variable="bar", units="baz")


def test_toggle_tree_button(qtbot, view_tools_and_settings):
    view_tools = view_tools_and_settings.widget
    settings = view_tools_and_settings.settings

    def test_tree_btn_toggled(checked):
        assert view_tools.tree_view_btn.property("checked")
        assert view_tools.collapse_all_btn.isEnabled()
        assert view_tools.expand_all_btn.isEnabled()
        assert settings.TREE_VIEW

        return checked

    callbacks = [test_tree_btn_toggled, None]
    signals = [view_tools.tree_view_btn.toggled, view_tools.structureChanged]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        qtbot.mouseClick(view_tools.tree_view_btn, Qt.LeftButton)


def test_text_edited(view_tools):
    assert False


def test_request_filter(view_tools):
    assert False


def test_expand_all(view_tools):
    assert False


def test_collapse_all(view_tools):
    assert False
