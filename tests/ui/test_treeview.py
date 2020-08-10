from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt, QModelIndex
from PySide2.QtWidgets import QHeaderView, QSizePolicy
from esofile_reader import EsoFile

from chartify.ui.treeview import TreeView, ViewModel
from chartify.utils.utils import FilterTuple, VariableData
from tests import ROOT

WIDTH = 402


@pytest.fixture(scope="module")
def eso_file():
    return EsoFile(Path(ROOT, "eso_files", "eplusout1.eso"))


@pytest.fixture
def hourly_df(eso_file):
    return eso_file.get_header_df("hourly").copy()


@pytest.fixture
def daily_df(eso_file):
    return eso_file.get_header_df("daily").copy()


@pytest.fixture
def tree_view(qtbot, hourly_df):
    model = ViewModel("hourly", is_simple=False, allow_rate_to_energy=False)
    tree_view = TreeView(0, {"hourly": model})
    tree_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    tree_view.setFixedWidth(WIDTH)
    tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tree_view.update_model("hourly", header_df=hourly_df, tree_node="type")
    tree_view.update_appearance()
    tree_view.show()
    qtbot.addWidget(tree_view)
    return tree_view


def test_init_tree_view(tree_view: TreeView):
    assert tree_view.rootIsDecorated()
    assert tree_view.uniformRowHeights()
    assert tree_view.isSortingEnabled()
    assert tree_view.hasMouseTracking()
    assert tree_view.dragEnabled()

    assert not tree_view.wordWrap()
    assert not tree_view.alternatingRowColors()

    assert tree_view.selectionBehavior() == TreeView.SelectRows
    assert tree_view.selectionMode() == TreeView.ExtendedSelection
    assert tree_view.editTriggers() == TreeView.NoEditTriggers
    assert tree_view.defaultDropAction() == Qt.CopyAction
    assert tree_view.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert tree_view.focusPolicy() == Qt.NoFocus

    assert tree_view.id_ == 0


def test_build_tree_view(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    assert tree_view.model().rowCount() == 49
    assert tree_view.model().sourceModel().rowCount() == 49

    assert tree_view.is_tree
    assert not tree_view.rate_to_energy
    assert tree_view.units_system == "SI"
    assert tree_view.energy_units == "J"
    assert not tree_view.next_update_forced


def test_first_column_spanned(tree_view: TreeView, hourly_df: pd.DataFrame):
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


def test_initial_view_appearance(tree_view: TreeView, hourly_df: pd.DataFrame):
    assert tree_view.header().sectionSize(0) == 200
    assert tree_view.header().sectionSize(1) == 130
    assert tree_view.header().sectionSize(2) == 70

    assert not tree_view.header().stretchLastSection()
    assert tree_view.header().sectionResizeMode(0) == QHeaderView.Interactive
    assert tree_view.header().sectionResizeMode(1) == QHeaderView.Stretch
    assert tree_view.header().sectionResizeMode(2) == QHeaderView.Fixed

    assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_build_plain_view(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model("hourly", header_df=hourly_df, tree_node=None)

    assert tree_view.model().rowCount() == 77
    assert tree_view.model().sourceModel().rowCount() == 77

    assert tree_view.interval == "hourly"
    assert not tree_view.is_tree
    assert not tree_view.rate_to_energy
    assert tree_view.units_system == "SI"
    assert tree_view.energy_units == "J"
    assert not tree_view.next_update_forced


def test_first_column_not_spanned(tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model("hourly", header_df=hourly_df, tree_node=None)
    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_index(index)
        if item.hasChildren():
            assert False, "Plain model should not have any child items!"
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_resize_header(tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model("hourly", header_df=hourly_df, tree_node=None)
    tree_view.resize_header({"interactive": 250, "fixed": 100})

    assert tree_view.header().sectionSize(0) == 250
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 100


def test_on_tree_node_changed_build_tree(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    assert tree_view.get_visual_names() == ("type", "key", "units")

    with qtbot.wait_signal(tree_view.treeNodeChanged, timeout=1000):
        tree_view.header().moveSection(2, 0)
        assert tree_view.get_visual_names() == ("units", "type", "key")
        assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_tree_node_changed_dont_build_tree(
    qtbot, tree_view: TreeView, hourly_df: pd.DataFrame
):
    assert tree_view.get_visual_names() == ("type", "key", "units")

    with qtbot.assertNotEmitted(tree_view.treeNodeChanged):
        tree_view.header().moveSection(2, 1)


def test_on_view_resized(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def test_size(cls, dct):
        return cls == "treeview" and dct["interactive"] == 125

    with qtbot.wait_signal(tree_view.viewAppearanceChanged, check_params_cb=test_size):
        tree_view.header().resizeSection(0, 125)


def test_on_view_resized_stretch(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    with qtbot.assertNotEmitted(tree_view.viewAppearanceChanged):
        tree_view.header().resizeSection(1, 125)


def test_on_section_moved_rebuild(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def test_header(cls, dct):
        return cls == "treeview" and dct["header"] == ("key", "units", "type")

    signals = [(tree_view.viewAppearanceChanged, "0"), (tree_view.treeNodeChanged, "1")]
    callbacks = [test_header, None]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        tree_view.header().moveSection(0, 2)


def test_on_section_moved_plain_view(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def test_header(cls, dct):
        return cls == "treeview" and dct["header"] == ("key", "units", "type")

    tree_view.update_model("hourly", header_df=hourly_df, tree_node=None)
    with qtbot.wait_signal(tree_view.viewAppearanceChanged, check_params_cb=test_header):
        tree_view.header().moveSection(0, 2)


def test_on_slider_moved(tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.verticalScrollBar().setSliderPosition(10)

    assert tree_view.verticalScrollBar().value() == 10


def test_on_double_clicked(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def variable_data(index):
        test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")
        data = tree_view.model().data_at_index(index)
        return test_data == data

    point = tree_view.visualRect(tree_view.model().index(1, 0)).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    signals = [tree_view.doubleClicked, tree_view.itemDoubleClicked]
    callbacks = [variable_data, None]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_double_clicked_parent(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    index = tree_view.model().index(7, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    with qtbot.assert_not_emitted(tree_view.itemDoubleClicked):
        with qtbot.wait_signal(tree_view.doubleClicked):
            # need to click first as single double click would emit only pressed signal
            qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert tree_view.isExpanded(index)


def test_select_all_children_expanded_parent(
    qtbot, tree_view: TreeView, hourly_df: pd.DataFrame
):
    index = tree_view.model().index(7, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    # need to click first as single double click would emit only pressed signal
    qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
    qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert tree_view.isExpanded(index)

    def test_data(variable_data):
        dt = [
            VariableData(
                "BLOCK1:ZONEB FAN COIL UNIT COOLING COIL",
                "Cooling Coil Sensible Cooling Rate",
                "W",
                "W",
            ),
            VariableData(
                "BLOCK1:ZONEA FAN COIL UNIT COOLING COIL",
                "Cooling Coil Sensible Cooling Rate",
                "W",
                "W",
            ),
        ]
        return dt == variable_data

    with qtbot.wait_signal(tree_view.selectionPopulated, check_params_cb=test_data):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")

    def variable_data1(index):
        data = tree_view.model().data_at_index(index)
        return test_data == data

    def variable_data2(vd):
        return vd == [test_data]

    index = tree_view.model().index(1, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    signals = [tree_view.pressed, tree_view.selectionPopulated]
    callbacks = [variable_data1, variable_data2]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed_collapsed_parent(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def variable_data1(index):
        data = tree_view.model().data(index)
        return data == "Cooling Coil Sensible Cooling Rate"

    index = tree_view.model().index(7, 0)
    press_point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=press_point)
    signals = [tree_view.pressed, tree_view.selectionCleared]
    callbacks = [variable_data1, None]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(tree_view.viewport(), Qt.LeftButton, pos=press_point)

    assert not tree_view.isExpanded(index)


def test_on_collapsed(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    index = tree_view.model().index(7, 0)
    tree_view.expand(index)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)

    def test_collapsed(cls, dct):
        return cls == "treeview" and dct["collapsed"] == "Cooling Coil Sensible Cooling Rate"

    with qtbot.wait_signal(tree_view.viewAppearanceChanged, check_params_cb=test_collapsed):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert not tree_view.isExpanded(index)


def test_on_expanded(qtbot, tree_view: TreeView, eso_file: EsoFile):
    index = tree_view.model().index(7, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)

    def test_collapsed(cls, dct):
        return cls == "treeview" and dct["expanded"] == "Cooling Coil Sensible Cooling Rate"

    with qtbot.wait_signal(tree_view.viewAppearanceChanged, check_params_cb=test_collapsed):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert tree_view.isExpanded(index)


def test_filter_view(tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_model("daily", header_df=daily_df, tree_node=None)
    tree_view.filter_view(FilterTuple(key="block1:zonea", type="temperature", units=""))

    assert tree_view.model().rowCount() == 3
    assert tree_view.model().sourceModel().rowCount() == 49

    index0 = tree_view.model().index(0, 0)
    index1 = tree_view.model().index(1, 0)
    index2 = tree_view.model().index(2, 0)

    assert tree_view.isExpanded(index0)
    assert tree_view.isExpanded(index1)
    assert tree_view.isExpanded(index2)

    child_index0 = tree_view.model().index(0, 0, index0)
    child_index1 = tree_view.model().index(0, 0, index1)
    child_index2 = tree_view.model().index(0, 0, index2)

    vd0 = VariableData("BLOCK1:ZONEA", "Zone Mean Air Temperature", "C", "C")
    vd1 = VariableData("BLOCK1:ZONEA", "Zone Mean Radiant Temperature", "C", "C")
    vd2 = VariableData("BLOCK1:ZONEA", "Zone Operative Temperature", "C", "C")

    assert tree_view.model().data_at_index(child_index0) == vd0
    assert tree_view.model().data_at_index(child_index1) == vd1
    assert tree_view.model().data_at_index(child_index2) == vd2

    child_index_invalid = tree_view.model().index(1, 0, index0)
    assert child_index_invalid == QModelIndex()


def test_get_visual_names(tree_view: TreeView):
    assert tree_view.get_visual_names() == ("type", "key", "units")

    tree_view.reorder_columns(("units", "type", "key"))
    assert tree_view.get_visual_names() == ("units", "type", "key")


def test_get_visual_ixs(tree_view: TreeView):
    assert tree_view.get_visual_indexes() == {"type": 0, "key": 1, "units": 2}


def test_build_view_kwargs_rate_to_energy(qtbot, tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_model(daily_df, "daily", is_tree=True, rate_to_energy=True)
    tree_view.update_appearance()
    proxy_model = tree_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "J")
    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "J"


def test_build_view_kwargs_units_system(tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_model(daily_df, "daily", is_tree=True, units_system="IP")
    proxy_model = tree_view.model()
    test_data = VariableData("Environment", "Site Outdoor Air Dewpoint Temperature", "C", "F")

    assert proxy_model.data_at_index(proxy_model.index(22, 0)) == test_data
    assert proxy_model.data(proxy_model.index(22, 2)) == "F"


def test_build_view_kwargs_energy_units(tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_model(
        daily_df, "daily", is_tree=True, rate_to_energy=True, energy_units="MWh"
    )
    proxy_model = tree_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "MWh")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "MWh"


def test_build_view_kwargs_power_units(tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_model(daily_df, "daily", is_tree=True, power_units="MW")
    proxy_model = tree_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "MW")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "MW"


def test_update_view_model_appearance(tree_view: TreeView, daily_df: pd.DataFrame):
    header = ("type", "units", "key")
    tree_view.update_model(
        daily_df, "daily", is_tree=True, header=header,
    )

    widths = {"interactive": 150, "fixed": 50}
    expanded = {"Fan Electric Power", "Heating Coil Heating Rate"}
    tree_view.update_appearance(header, widths, expanded)

    assert tree_view.header().sectionSize(0) == 150
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 200

    assert tree_view.get_visual_names() == ("type", "units", "key")

    assert tree_view.isExpanded(tree_view.model().index(11, 0))
    assert tree_view.isExpanded(tree_view.model().index(13, 0))


def test_update_view_model_appearance_default(tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_appearance()

    assert tree_view.header().sectionSize(0) == 200
    assert tree_view.header().sectionSize(1) == 130
    assert tree_view.header().sectionSize(2) == 70

    assert tree_view.get_visual_names() == ("type", "key", "units")


def test_build_view_reversed_header(tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.update_model(daily_df, "daily", is_tree=True, header=("units", "key", "type"))
    tree_view.update_appearance(("units", "key", "type"))

    assert tree_view.get_visual_names() == ("units", "key", "type")


def test_scroll_to(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    v = VariableData("BLOCK1:ZONEA", "Zone Infiltration Air Change Rate", "ach", "ach")
    with qtbot.wait_signal(tree_view.verticalScrollBar().valueChanged):
        tree_view.scroll_to(v)

    assert tree_view.verticalScrollBar().value() == 29


def test_deselect_variables(qtbot, tree_view: TreeView, daily_df: pd.DataFrame):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "kW"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "kW"),
    ]
    tree_view.update_model(
        daily_df, "daily", is_tree=True, power_units="kW",
    )
    tree_view.select_variables(selected)
    proxy_rows = tree_view.selectionModel().selectedRows()
    variables_data = [tree_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data

    with qtbot.wait_signal(tree_view.selectionCleared):
        tree_view.deselect_all_variables()

    assert not tree_view.selectionModel().selectedRows()


def test_select_variables(tree_view: TreeView):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "W"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "W"),
    ]
    tree_view.select_variables(selected)

    proxy_rows = tree_view.selectionModel().selectedRows()
    variables_data = [tree_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data
