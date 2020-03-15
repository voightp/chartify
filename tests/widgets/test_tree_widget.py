from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QHeaderView, QSizePolicy
from esofile_reader import EsoFile

from chartify.utils.utils import FilterTuple
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
def tree_view(qtbot):
    tree_view = View(0, "test")
    tree_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    tree_view.setFixedWidth(WIDTH)
    tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tree_view.show()

    qtbot.addWidget(tree_view)
    return tree_view


def test_00_class_attributes(tree_view: View):
    assert tree_view.settings["widths"]["interactive"] == 200
    assert tree_view.settings["widths"]["fixed"] == 70
    assert tree_view.settings["order"] == ("variable", Qt.AscendingOrder)
    assert tree_view.settings["header"] == ["variable", "key", "units"]
    assert tree_view.settings["expanded"] == set()


def test_01_init_tree_view(tree_view: View):
    assert tree_view.rootIsDecorated()
    assert tree_view.uniformRowHeights()
    assert tree_view.isSortingEnabled()
    assert tree_view.hasMouseTracking()

    assert not tree_view.dragEnabled()
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


def test_02_build_tree_view(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.model().rowCount() == 49
    assert tree_view.model().sourceModel().rowCount() == 49

    assert tree_view.temp_settings["interval"] == "hourly"
    assert tree_view.temp_settings["is_tree"]
    assert tree_view.temp_settings["units"] == (False, "SI", "J", "W")
    assert tree_view.temp_settings["filter"] == FilterTuple("", "", "")
    assert not tree_view.temp_settings["force_update"]


def test_02a_first_column_spanned(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_from_index(index)
        if item.hasChildren():
            assert tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())
            for j in range(item.rowCount()):
                assert not tree_view.isFirstColumnSpanned(j, index)
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_02b_initial_view_appearance(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.header().sectionSize(0) == 200
    assert tree_view.header().sectionSize(1) == 130
    assert tree_view.header().sectionSize(2) == 70

    assert not tree_view.header().stretchLastSection()
    assert tree_view.header().sectionResizeMode(0) == QHeaderView.Interactive
    assert tree_view.header().sectionResizeMode(1) == QHeaderView.Stretch
    assert tree_view.header().sectionResizeMode(2) == QHeaderView.Fixed

    assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_03_build_plain_view(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)

    assert tree_view.model().rowCount() == 77
    assert tree_view.model().sourceModel().rowCount() == 77

    assert tree_view.temp_settings["interval"] == "hourly"
    assert not tree_view.temp_settings["is_tree"]
    assert tree_view.temp_settings["units"] == (False, "SI", "J", "W")
    assert tree_view.temp_settings["filter"] == FilterTuple("", "", "")
    assert not tree_view.temp_settings["force_update"]


def test_03a_first_column_not_spanned(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_from_index(index)
        if item.hasChildren():
            assert False, "Plain model should not have any child items!"
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_04_resize_header(tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    tree_view.resize_header({"interactive": 250, "fixed": 100})

    assert tree_view.header().sectionSize(0) == 250
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 100


def test_05a_on_sort_order_changed_build_tree(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.wait_signal(tree_view.treeNodeChanged, timeout=1000):
        tree_view.header().moveSection(2, 0)
        assert tree_view.get_visual_names() == ["units", "variable", "key"]
        assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_06a_on_sort_order_changed_no_build_tree(
    qtbot, tree_view: View, hourly_df: pd.DataFrame
):
    tree_view.build_view(variables_df=hourly_df, interval="hourly", is_tree=True)

    assert tree_view.get_visual_names() == ["units", "variable", "key"]

    with qtbot.assertNotEmitted(tree_view.treeNodeChanged):
        tree_view.header().moveSection(2, 1)


def test_0x_on_view_resized(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_0x_on_section_moved(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_0x_on_slider_moved(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_0x_on_double_clicked(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_0x_on_pressed(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_0x_on_collapsed(tree_view: View, hourly_df: pd.DataFrame):
    pass


def test_0x_on_expanded(tree_view: View, eso_file: EsoFile):
    pass
