from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt, QEvent
from PySide2.QtWidgets import QHeaderView, QSizePolicy
from esofile_reader import EsoFile

from chartify.utils.utils import FilterTuple, VariableData
from chartify.view.treeview_widget import View
from tests import ROOT

WIDTH = 402



@pytest.fixture(scope="module")
def eso_file():
    return EsoFile(Path(ROOT, "eso_files", "eplusout1.eso"))


@pytest.fixture
def hourly_df(eso_file):
    return eso_file.get_header_df("hourly")


@pytest.fixture
def daily_df(eso_file):
    return eso_file.get_header_df("daily")


@pytest.fixture
def tree_view(qtbot):
    tree_view = View(0, "test")
    tree_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    tree_view.setFixedWidth(WIDTH)
    tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tree_view.show()
    qtbot.addWidget(tree_view)
    return tree_view


def test_init_tree_view(tree_view: View):
    assert tree_view.rootIsDecorated()
    assert tree_view.uniformRowHeights()
    assert tree_view.isSortingEnabled()
    assert tree_view.hasMouseTracking()
    assert tree_view.dragEnabled()

    assert not tree_view.wordWrap()
    assert not tree_view.alternatingRowColors()

    assert tree_view.selectionBehavior() == View.SelectRows
    assert tree_view.selectionMode() == View.ExtendedSelection
    assert tree_view.editTriggers() == View.NoEditTriggers
    assert tree_view.defaultDropAction() == Qt.CopyAction
    assert tree_view.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert tree_view.focusPolicy() == Qt.NoFocus

    assert tree_view.id_ == 0
    assert tree_view.name == "test"


def test_build_tree_view(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.model().rowCount() == 49
    assert tree_view.model().sourceModel().rowCount() == 49

    assert tree_view.temp_settings["interval"] == "hourly"
    assert tree_view.temp_settings["is_tree"]
    assert tree_view.temp_settings["units"] == (False, "SI", "J", "W")
    assert tree_view.temp_settings["filter"] == FilterTuple("", "", "")
    assert not tree_view.temp_settings["force_update"]


def test_first_column_spanned(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_index(index)
        if item.hasChildren():
            assert tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())
            for j in range(item.rowCount()):
                assert not tree_view.isFirstColumnSpanned(j, index)
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_initial_view_appearance(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.header().sectionSize(0) == 200
    assert tree_view.header().sectionSize(1) == 130
    assert tree_view.header().sectionSize(2) == 70

    assert not tree_view.header().stretchLastSection()
    assert tree_view.header().sectionResizeMode(0) == QHeaderView.Interactive
    assert tree_view.header().sectionResizeMode(1) == QHeaderView.Stretch
    assert tree_view.header().sectionResizeMode(2) == QHeaderView.Fixed

    assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_build_plain_view(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)

    assert tree_view.model().rowCount() == 77
    assert tree_view.model().sourceModel().rowCount() == 77

    assert tree_view.temp_settings["interval"] == "hourly"
    assert not tree_view.temp_settings["is_tree"]
    assert tree_view.temp_settings["units"] == (False, "SI", "J", "W")
    assert tree_view.temp_settings["filter"] == FilterTuple("", "", "")
    assert not tree_view.temp_settings["force_update"]


def test_first_column_not_spanned(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_index(index)
        if item.hasChildren():
            assert False, "Plain model should not have any child items!"
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_resize_header(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    tree_view.resize_header({"interactive": 250, "fixed": 100})

    assert tree_view.header().sectionSize(0) == 250
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 100


def test_on_sort_order_changed_build_tree(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    assert tree_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.wait_signal(tree_view.treeNodeChanged, timeout=1000):
        tree_view.header().moveSection(2, 0)
        assert tree_view.get_visual_names() == ["units", "variable", "key"]
        assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_sort_order_changed_no_build_tree(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.assertNotEmitted(tree_view.treeNodeChanged):
        tree_view.header().moveSection(2, 1)


def test_on_view_resized(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def test_size(dct):
        return dct["interactive"] == 125

    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    with qtbot.wait_signal(tree_view.viewSettingsChanged, check_params_cb=test_size):
        tree_view.header().resizeSection(0, 125)


def test_on_view_resized_stretch(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    with qtbot.assertNotEmitted(tree_view.viewSettingsChanged):
        tree_view.header().resizeSection(1, 125)


def test_on_section_moved_rebuild(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def test_header(dct):
        return dct["header"] == ["key", "units", "variable"]

    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    signals = [(tree_view.viewSettingsChanged, "0"), (tree_view.treeNodeChanged, "1")]
    callbacks = [test_header, None]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        tree_view.header().moveSection(0, 2)


def test_on_section_moved_plain_view(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def test_header(dct):
        return dct["header"] == ["key", "units", "variable"]

    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    with qtbot.wait_signal(tree_view.viewSettingsChanged, check_params_cb=test_header):
        tree_view.header().moveSection(0, 2)


def test_on_slider_moved(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    tree_view.verticalScrollBar().setSliderPosition(10)

    assert tree_view.verticalScrollBar().value() == 10


def test_on_double_clicked(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def variable_data(index):
        test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")
        data = tree_view.model().data_at_index(index)
        return test_data == data

    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    rect = tree_view.visualRect(tree_view.model().index(1, 0))
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=rect.center())
    signals = [tree_view.doubleClicked, tree_view.itemDoubleClicked]
    callbacks = [variable_data, None]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=rect.center())
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=rect.center())


def test_on_double_clicked_parent(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    index = tree_view.model().index(7, 0)
    rect = tree_view.visualRect(index)
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=rect.center())
    with qtbot.assert_not_emitted(tree_view.itemDoubleClicked):
        with  qtbot.wait_signal(tree_view.doubleClicked):
            # need to click first as single double click would emit only pressed signal
            qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=rect.center())
            qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=rect.center())

    assert tree_view.isExpanded(index)


def test_on_pressed(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")

    def variable_data1(index):
        data = tree_view.model().data_at_index(index)
        return test_data == data

    def variable_data2(vd):
        return vd == [test_data]

    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)
    index = tree_view.model().index(1, 0)
    release_point = tree_view.visualRect(tree_view.model().index(3, 0)).center()
    press_point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=press_point)
    signals = [tree_view.pressed, tree_view.selectionPopulated]
    callbacks = [variable_data1, variable_data2]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(tree_view.viewport(), Qt.LeftButton, pos=press_point)
        qtbot.mousePress(tree_view.viewport(), Qt.LeftButton, pos=press_point)
        qtbot.mouseRelease(tree_view.viewport(), Qt.LeftButton, pos=release_point, delay=150)


def test_on_collapsed(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_on_expanded(tree_view: View, eso_file: EsoFile):
    pass


def test_filter_view(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_set_next_update_forced(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_get_visual_names(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_get_visual_ixs(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_reshuffle_columns(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_update_sort_order(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_expand_items(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_scroll_to(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_update_view_appearance(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_deselect_variables(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_select_variables(tree_view: View, hourly_df: pd.DataFrame):
    pass
