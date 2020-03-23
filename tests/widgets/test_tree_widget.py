from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt, QModelIndex
from PySide2.QtWidgets import QHeaderView, QSizePolicy
from esofile_reader import EsoFile

from chartify.ui.treeview_widget import View
from chartify.utils.utils import FilterTuple, VariableData
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
def tree_view(qtbot, hourly_df):
    tree_view = View(0, "test")
    tree_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    tree_view.setFixedWidth(WIDTH)
    tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tree_view.build_view(variables_df=hourly_df.copy(), interval="hourly", is_tree=True)
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
    assert tree_view.model().rowCount() == 49
    assert tree_view.model().sourceModel().rowCount() == 49

    assert tree_view.temp_settings["interval"] == "hourly"
    assert tree_view.temp_settings["is_tree"]
    assert tree_view.temp_settings["units"] == (False, "SI", "J", "W")
    assert not tree_view.temp_settings["force_update"]


def test_first_column_spanned(tree_view: View, hourly_df: pd.DataFrame):
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
    assert tree_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.wait_signal(tree_view.treeNodeChanged, timeout=1000):
        tree_view.header().moveSection(2, 0)
        assert tree_view.get_visual_names() == ["units", "variable", "key"]
        assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_sort_order_changed_no_build_tree(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    assert tree_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.assertNotEmitted(tree_view.treeNodeChanged):
        tree_view.header().moveSection(2, 1)


def test_on_view_resized(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def test_size(dct):
        return dct["interactive"] == 125

    with qtbot.wait_signal(tree_view.viewSettingsChanged, check_params_cb=test_size):
        tree_view.header().resizeSection(0, 125)


def test_on_view_resized_stretch(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    with qtbot.assertNotEmitted(tree_view.viewSettingsChanged):
        tree_view.header().resizeSection(1, 125)


def test_on_section_moved_rebuild(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def test_header(dct):
        return dct["header"] == ["key", "units", "variable"]

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
    tree_view.verticalScrollBar().setSliderPosition(10)

    assert tree_view.verticalScrollBar().value() == 10


def test_on_double_clicked(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def variable_data(index):
        test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")
        data = tree_view.model().data_at_index(index)
        return test_data == data

    point = tree_view.visualRect(tree_view.model().index(1, 0)).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    signals = [tree_view.doubleClicked, tree_view.itemDoubleClicked]
    callbacks = [variable_data, None]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_double_clicked_parent(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    index = tree_view.model().index(7, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    with qtbot.assert_not_emitted(tree_view.itemDoubleClicked):
        with  qtbot.wait_signal(tree_view.doubleClicked):
            # need to click first as single double click would emit only pressed signal
            qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert tree_view.isExpanded(index)


def test_select_all_children_expanded_parent(qtbot, tree_view: View, hourly_df: pd.DataFrame):
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
                "W"
            ),
            VariableData(
                "BLOCK1:ZONEA FAN COIL UNIT COOLING COIL",
                "Cooling Coil Sensible Cooling Rate",
                "W",
                "W")
        ]
        return dt == variable_data

    with qtbot.wait_signal(tree_view.selectionPopulated, check_params_cb=test_data):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed(qtbot, tree_view: View, hourly_df: pd.DataFrame):
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


def test_on_pressed_collapsed_parent(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    def variable_data1(index):
        data = tree_view.model().data(index)
        return data == "Cooling Coil Sensible Cooling Rate"

    index = tree_view.model().index(7, 0)
    press_point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=press_point)
    signals = [tree_view.pressed, tree_view.selectionCleared]
    callbacks = [variable_data1, None]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(tree_view.viewport(), Qt.LeftButton, pos=press_point)

    assert not tree_view.isExpanded(index)


def test_on_collapsed(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    index = tree_view.model().index(7, 0)
    tree_view.expand(index)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)

    def test_collapsed(dct):
        return dct["collapsed"] == "Cooling Coil Sensible Cooling Rate"

    with qtbot.wait_signal(tree_view.viewSettingsChanged, check_params_cb=test_collapsed):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert not tree_view.isExpanded(index)


def test_on_expanded(qtbot, tree_view: View, eso_file: EsoFile):
    index = tree_view.model().index(7, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)

    def test_collapsed(dct):
        return dct["expanded"] == "Cooling Coil Sensible Cooling Rate"

    with qtbot.wait_signal(tree_view.viewSettingsChanged, check_params_cb=test_collapsed):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert tree_view.isExpanded(index)


def test_filter_view(tree_view: View, daily_df: pd.DataFrame):
    tree_view.build_view(
        variables_df=daily_df,
        interval="daily",
        is_tree=True,
    )
    tree_view.filter_view(FilterTuple(key="block1:zonea", variable="temperature", units=""))

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


def test_set_next_update_forced(tree_view: View):
    tree_view.set_next_update_forced()
    assert tree_view.temp_settings["force_update"]


def test_get_visual_names(tree_view: View):
    assert tree_view.get_visual_names() == ["variable", "key", "units"]

    tree_view.reshuffle_columns(["units", "variable", "key"])
    assert tree_view.get_visual_names() == ["units", "variable", "key"]


def test_get_visual_ixs(tree_view: View):
    assert tree_view.get_visual_indexes() == {"variable": 0, "key": 1, "units": 2}


def test_build_view_kwargs_rate_to_energy(tree_view: View, daily_df: pd.DataFrame):
    tree_view.build_view(daily_df, "daily", is_tree=True, rate_to_energy=True)
    proxy_model = tree_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "J")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "J"


def test_build_view_kwargs_units_system(tree_view: View, daily_df: pd.DataFrame):
    tree_view.build_view(daily_df, "daily", is_tree=True, units_system="IP")
    proxy_model = tree_view.model()
    test_data = VariableData(
        "Environment", "Site Outdoor Air Dewpoint Temperature", "C", "F"
    )

    assert proxy_model.data_at_index(proxy_model.index(22, 0)) == test_data
    assert proxy_model.data(proxy_model.index(22, 2)) == "F"


def test_build_view_kwargs_energy_units(tree_view: View, daily_df: pd.DataFrame):
    tree_view.build_view(
        daily_df,
        "daily",
        is_tree=True,
        rate_to_energy=True,
        energy_units="MWh"
    )
    proxy_model = tree_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "MWh")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "MWh"


def test_build_view_kwargs_power_units(tree_view: View, daily_df: pd.DataFrame):
    tree_view.build_view(daily_df, "daily", is_tree=True, power_units="MW")
    proxy_model = tree_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "MW")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "MW"


def test_build_view_kwargs_selected(tree_view: View, daily_df: pd.DataFrame):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "kW"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "kW")
    ]
    tree_view.build_view(daily_df, "daily", is_tree=True, power_units="kW", selected=selected)
    proxy_rows = tree_view.selectionModel().selectedRows()
    variables_data = [tree_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data


def test_build_view_kwargs_scroll_to(qtbot, tree_view: View, daily_df: pd.DataFrame):
    v = VariableData("BLOCK1:ZONEA", "Zone Infiltration Air Change Rate", "ach", "ach")
    with qtbot.wait_signal(tree_view.verticalScrollBar().valueChanged):
        tree_view.build_view(daily_df, "daily", is_tree=True, scroll_to=v)

    assert tree_view.verticalScrollBar().value() == 29


def test_build_view_kwargs_settings(tree_view: View, daily_df: pd.DataFrame):
    settings = {
        "widths": {"interactive": 150, "fixed": 50},
        "header": ["variable", "units", "key"],
        "expanded": {"Fan Electric Power", "Heating Coil Heating Rate"},
    }
    tree_view.build_view(daily_df, "daily", is_tree=True, settings=settings)

    assert tree_view.header().sectionSize(0) == 150
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 200

    assert tree_view.get_visual_names() == ["variable", "units", "key"]

    assert tree_view.isExpanded(tree_view.model().index(11, 0))
    assert tree_view.isExpanded(tree_view.model().index(13, 0))


def test_scroll_to(qtbot, tree_view: View, hourly_df: pd.DataFrame):
    v = VariableData("BLOCK1:ZONEA", "Zone Infiltration Air Change Rate", "ach", "ach")
    with qtbot.wait_signal(tree_view.verticalScrollBar().valueChanged):
        tree_view.scroll_to(v, "variable")

    assert tree_view.verticalScrollBar().value() == 29


def test_update_view_appearance(tree_view: View, hourly_df: pd.DataFrame):
    settings = {
        "widths": {"interactive": 150, "fixed": 50},
        "header": ["variable", "units", "key"],
        "expanded": {"Fan Electric Power", "Heating Coil Heating Rate"},
    }
    tree_view.update_view_appearance(settings)

    assert tree_view.header().sectionSize(0) == 150
    assert tree_view.header().sectionSize(2) == 50
    assert tree_view.header().sectionSize(1) == 200

    assert tree_view.get_visual_names() == ["variable", "units", "key"]

    assert tree_view.isExpanded(tree_view.model().index(11, 0))
    assert tree_view.isExpanded(tree_view.model().index(13, 0))


def test_deselect_variables(qtbot, tree_view: View, daily_df: pd.DataFrame):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "kW"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "kW")
    ]
    tree_view.build_view(
        daily_df,
        "daily",
        is_tree=True,
        power_units="kW",
        selected=selected
    )
    proxy_rows = tree_view.selectionModel().selectedRows()
    variables_data = [tree_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data

    with qtbot.wait_signal(tree_view.selectionCleared):
        tree_view.deselect_all_variables()

    assert not tree_view.selectionModel().selectedRows()


def test_select_variables(tree_view: View):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "W"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "W")
    ]
    tree_view.select_variables(selected)

    proxy_rows = tree_view.selectionModel().selectedRows()
    variables_data = [tree_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data
