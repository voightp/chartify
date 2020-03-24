from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt, QModelIndex
from PySide2.QtWidgets import QHeaderView, QSizePolicy
from esofile_reader import EsoFile

from chartify.ui.simpleview import SimpleView
from chartify.utils.utils import FilterTuple, VariableData
from tests import ROOT

WIDTH = 402


@pytest.fixture(scope="module")
def eso_file():
    return EsoFile(Path(ROOT, "eso_files", "eplusout1.eso")).generate_totals()


@pytest.fixture
def hourly_df(eso_file):
    return eso_file.get_header_df("hourly")


@pytest.fixture
def daily_df(eso_file):
    return eso_file.get_header_df("daily")


@pytest.fixture
def simple_view(qtbot, hourly_df):
    simple_view = SimpleView(0, "test")
    simple_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    simple_view.setFixedWidth(WIDTH)
    simple_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    simple_view.populate_view(variables_df=hourly_df.copy(), interval="hourly", is_tree=True)
    simple_view.show()
    qtbot.addWidget(simple_view)
    return simple_view


def test_init_simple_view(simple_view: SimpleView):
    assert simple_view.rootIsDecorated()
    assert simple_view.uniformRowHeights()
    assert simple_view.isSortingEnabled()
    assert simple_view.hasMouseTracking()
    assert simple_view.dragEnabled()

    assert not simple_view.wordWrap()
    assert not simple_view.alternatingRowColors()

    assert simple_view.selectionBehavior() == SimpleView.SelectRows
    assert simple_view.selectionMode() == SimpleView.ExtendedSelection
    assert simple_view.editTriggers() == SimpleView.NoEditTriggers
    assert simple_view.defaultDropAction() == Qt.CopyAction
    assert simple_view.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert simple_view.focusPolicy() == Qt.NoFocus

    assert simple_view.id_ == 0
    assert simple_view.name == "test"


def test_build_simple_view(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    assert simple_view.model().rowCount() == 49
    assert simple_view.model().sourceModel().rowCount() == 49

    assert simple_view.interval == "hourly"
    assert simple_view.is_tree
    assert not simple_view.rate_to_energy
    assert simple_view.units_system == "SI"
    assert simple_view.energy_units == "J"
    assert not simple_view.next_update_forced


def test_first_column_spanned(simple_view: SimpleView, hourly_df: pd.DataFrame):
    proxy_model = simple_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_index(index)
        if item.hasChildren():
            assert simple_view.isFirstColumnSpanned(i, simple_view.rootIndex())
            for j in range(item.rowCount()):
                assert not simple_view.isFirstColumnSpanned(j, index)
        else:
            assert not simple_view.isFirstColumnSpanned(i, simple_view.rootIndex())


def test_initial_view_appearance(simple_view: SimpleView, hourly_df: pd.DataFrame):
    assert simple_view.header().sectionSize(0) == 200
    assert simple_view.header().sectionSize(1) == 130
    assert simple_view.header().sectionSize(2) == 70

    assert not simple_view.header().stretchLastSection()
    assert simple_view.header().sectionResizeMode(0) == QHeaderView.Interactive
    assert simple_view.header().sectionResizeMode(1) == QHeaderView.Stretch
    assert simple_view.header().sectionResizeMode(2) == QHeaderView.Fixed

    assert simple_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_build_plain_view(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    simple_view.populate_view(variables_df=hourly_df, interval="hourly", is_tree=False)

    assert simple_view.model().rowCount() == 77
    assert simple_view.model().sourceModel().rowCount() == 77

    assert simple_view.interval == "hourly"
    assert not simple_view.is_tree
    assert not simple_view.rate_to_energy
    assert simple_view.units_system == "SI"
    assert simple_view.energy_units == "J"
    assert not simple_view.next_update_forced


def test_first_column_not_spanned(simple_view: SimpleView, hourly_df: pd.DataFrame):
    simple_view.populate_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    proxy_model = simple_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_index(index)
        if item.hasChildren():
            assert False, "Plain model should not have any child items!"
        else:
            assert not simple_view.isFirstColumnSpanned(i, simple_view.rootIndex())


def test_resize_header(simple_view: SimpleView, hourly_df: pd.DataFrame):
    simple_view.populate_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    simple_view.resize_header({"interactive": 250, "fixed": 100})

    assert simple_view.header().sectionSize(0) == 250
    assert simple_view.header().sectionSize(1) == 50
    assert simple_view.header().sectionSize(2) == 100


def test_on_sort_order_changed_build_tree(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    assert simple_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.wait_signal(simple_view.treeNodeChanged, timeout=1000):
        simple_view.header().moveSection(2, 0)
        assert simple_view.get_visual_names() == ["units", "variable", "key"]
        assert simple_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_sort_order_changed_no_build_tree(qtbot, simple_view: SimpleView,
                                             hourly_df: pd.DataFrame):
    assert simple_view.get_visual_names() == ["variable", "key", "units"]

    with qtbot.assertNotEmitted(simple_view.treeNodeChanged):
        simple_view.header().moveSection(2, 1)


def test_on_view_resized(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def test_size(dct):
        return dct["interactive"] == 125

    with qtbot.wait_signal(simple_view.viewSettingsChanged, check_params_cb=test_size):
        simple_view.header().resizeSection(0, 125)


def test_on_view_resized_stretch(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    with qtbot.assertNotEmitted(simple_view.viewSettingsChanged):
        simple_view.header().resizeSection(1, 125)


def test_on_section_moved_rebuild(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def test_header(dct):
        return dct["header"] == ["key", "units", "variable"]

    signals = [(simple_view.viewSettingsChanged, "0"), (simple_view.treeNodeChanged, "1")]
    callbacks = [test_header, None]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        simple_view.header().moveSection(0, 2)


def test_on_section_moved_plain_view(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def test_header(dct):
        return dct["header"] == ["key", "units", "variable"]

    simple_view.populate_view(variables_df=hourly_df, interval="hourly", is_tree=False)
    with qtbot.wait_signal(simple_view.viewSettingsChanged, check_params_cb=test_header):
        simple_view.header().moveSection(0, 2)


def test_on_slider_moved(simple_view: SimpleView, hourly_df: pd.DataFrame):
    simple_view.verticalScrollBar().setSliderPosition(10)

    assert simple_view.verticalScrollBar().value() == 10


def test_on_double_clicked(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def variable_data(index):
        test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")
        data = simple_view.model().data_at_index(index)
        return test_data == data

    point = simple_view.visualRect(simple_view.model().index(1, 0)).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)
    signals = [simple_view.doubleClicked, simple_view.itemDoubleClicked]
    callbacks = [variable_data, None]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(simple_view.viewport(), Qt.LeftButton, pos=point)


def test_on_double_clicked_parent(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    index = simple_view.model().index(7, 0)
    point = simple_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)
    with qtbot.assert_not_emitted(simple_view.itemDoubleClicked):
        with  qtbot.wait_signal(simple_view.doubleClicked):
            # need to click first as single double click would emit only pressed signal
            qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(simple_view.viewport(), Qt.LeftButton, pos=point)

    assert simple_view.isExpanded(index)


def test_select_all_children_expanded_parent(qtbot, simple_view: SimpleView,
                                             hourly_df: pd.DataFrame):
    index = simple_view.model().index(7, 0)
    point = simple_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)
    # need to click first as single double click would emit only pressed signal
    qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)
    qtbot.mouseDClick(simple_view.viewport(), Qt.LeftButton, pos=point)

    assert simple_view.isExpanded(index)

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

    with qtbot.wait_signal(simple_view.selectionPopulated, check_params_cb=test_data):
        qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "W")

    def variable_data1(index):
        data = simple_view.model().data_at_index(index)
        return test_data == data

    def variable_data2(vd):
        return vd == [test_data]

    index = simple_view.model().index(1, 0)
    point = simple_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)
    signals = [simple_view.pressed, simple_view.selectionPopulated]
    callbacks = [variable_data1, variable_data2]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(simple_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed_collapsed_parent(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def variable_data1(index):
        data = simple_view.model().data(index)
        return data == "Cooling Coil Sensible Cooling Rate"

    index = simple_view.model().index(7, 0)
    press_point = simple_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=press_point)
    signals = [simple_view.pressed, simple_view.selectionCleared]
    callbacks = [variable_data1, None]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(simple_view.viewport(), Qt.LeftButton, pos=press_point)

    assert not simple_view.isExpanded(index)


def test_on_collapsed(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    index = simple_view.model().index(7, 0)
    simple_view.expand(index)
    point = simple_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)

    def test_collapsed(dct):
        return dct["collapsed"] == "Cooling Coil Sensible Cooling Rate"

    with qtbot.wait_signal(simple_view.viewSettingsChanged, check_params_cb=test_collapsed):
        qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(simple_view.viewport(), Qt.LeftButton, pos=point)

    assert not simple_view.isExpanded(index)


def test_on_expanded(qtbot, simple_view: SimpleView, eso_file: EsoFile):
    index = simple_view.model().index(7, 0)
    point = simple_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)

    def test_collapsed(dct):
        return dct["expanded"] == "Cooling Coil Sensible Cooling Rate"

    with qtbot.wait_signal(simple_view.viewSettingsChanged, check_params_cb=test_collapsed):
        qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(simple_view.viewport(), Qt.LeftButton, pos=point)

    assert simple_view.isExpanded(index)


def test_filter_view(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(
        variables_df=daily_df,
        interval="daily",
        is_tree=True,
    )
    simple_view.filter_view(FilterTuple(key="block1:zonea", variable="temperature", units=""))

    assert simple_view.model().rowCount() == 3
    assert simple_view.model().sourceModel().rowCount() == 49

    index0 = simple_view.model().index(0, 0)
    index1 = simple_view.model().index(1, 0)
    index2 = simple_view.model().index(2, 0)

    assert simple_view.isExpanded(index0)
    assert simple_view.isExpanded(index1)
    assert simple_view.isExpanded(index2)

    child_index0 = simple_view.model().index(0, 0, index0)
    child_index1 = simple_view.model().index(0, 0, index1)
    child_index2 = simple_view.model().index(0, 0, index2)

    vd0 = VariableData("BLOCK1:ZONEA", "Zone Mean Air Temperature", "C", "C")
    vd1 = VariableData("BLOCK1:ZONEA", "Zone Mean Radiant Temperature", "C", "C")
    vd2 = VariableData("BLOCK1:ZONEA", "Zone Operative Temperature", "C", "C")

    assert simple_view.model().data_at_index(child_index0) == vd0
    assert simple_view.model().data_at_index(child_index1) == vd1
    assert simple_view.model().data_at_index(child_index2) == vd2

    child_index_invalid = simple_view.model().index(1, 0, index0)
    assert child_index_invalid == QModelIndex()


def test_get_visual_names(simple_view: SimpleView):
    assert simple_view.get_visual_names() == ["variable", "key", "units"]

    simple_view.reshuffle_columns(["units", "variable", "key"])
    assert simple_view.get_visual_names() == ["units", "variable", "key"]


def test_get_visual_ixs(simple_view: SimpleView):
    assert simple_view.get_visual_indexes() == {"variable": 0, "key": 1, "units": 2}


def test_build_view_kwargs_rate_to_energy(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(daily_df, "daily", is_tree=True, rate_to_energy=True)
    proxy_model = simple_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "J")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "J"


def test_build_view_kwargs_units_system(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(daily_df, "daily", is_tree=True, units_system="IP")
    proxy_model = simple_view.model()
    test_data = VariableData(
        "Environment", "Site Outdoor Air Dewpoint Temperature", "C", "F"
    )

    assert proxy_model.data_at_index(proxy_model.index(22, 0)) == test_data
    assert proxy_model.data(proxy_model.index(22, 2)) == "F"


def test_build_view_kwargs_energy_units(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(
        daily_df,
        "daily",
        is_tree=True,
        rate_to_energy=True,
        energy_units="MWh"
    )
    proxy_model = simple_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "MWh")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "MWh"


def test_build_view_kwargs_power_units(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(daily_df, "daily", is_tree=True, power_units="MW")
    proxy_model = simple_view.model()
    test_data = VariableData("BOILER", "Boiler Gas Rate", "W", "MW")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 2)) == "MW"


def test_build_view_kwargs_settings(simple_view: SimpleView, daily_df: pd.DataFrame):
    widths = {"interactive": 150, "fixed": 50}
    header = ["variable", "units", "key"]
    expanded = {"Fan Electric Power", "Heating Coil Heating Rate"}
    simple_view.update_view_appearance(header, widths, expanded)
    simple_view.populate_view(
        daily_df,
        "daily",
        is_tree=True,
        widths=widths,
        header=header,
        expanded=expanded
    )

    assert simple_view.header().sectionSize(0) == 150
    assert simple_view.header().sectionSize(1) == 50
    assert simple_view.header().sectionSize(2) == 200

    assert simple_view.get_visual_names() == ["variable", "units", "key"]

    assert simple_view.isExpanded(simple_view.model().index(11, 0))
    assert simple_view.isExpanded(simple_view.model().index(13, 0))


def test_build_view_kwargs_default_settings(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(
        daily_df,
        "daily",
        is_tree=True,
    )

    assert simple_view.header().sectionSize(0) == 200
    assert simple_view.header().sectionSize(1) == 130
    assert simple_view.header().sectionSize(2) == 70

    assert simple_view.get_visual_names() == ["variable", "key", "units"]


def test_build_view_reversed_header(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(
        daily_df,
        "daily",
        is_tree=True,
        header=["units", "key", "variable"]
    )

    assert simple_view.header().sectionSize(0) == 70
    assert simple_view.header().sectionSize(1) == 200
    assert simple_view.header().sectionSize(2) == 130

    assert simple_view.get_visual_names() == ["units", "key", "variable"]


def test_scroll_to(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    v = VariableData("BLOCK1:ZONEA", "Zone Infiltration Air Change Rate", "ach", "ach")
    with qtbot.wait_signal(simple_view.verticalScrollBar().valueChanged):
        simple_view.scroll_to(v, "variable")

    assert simple_view.verticalScrollBar().value() == 29


def test_update_view_appearance(simple_view: SimpleView, hourly_df: pd.DataFrame):
    widths = {"interactive": 150, "fixed": 50}
    header = ["variable", "units", "key"]
    expanded = {"Fan Electric Power", "Heating Coil Heating Rate"}
    simple_view.update_view_appearance(header, widths, expanded)

    assert simple_view.header().sectionSize(0) == 150
    assert simple_view.header().sectionSize(2) == 50
    assert simple_view.header().sectionSize(1) == 200

    assert simple_view.get_visual_names() == ["variable", "units", "key"]

    assert simple_view.isExpanded(simple_view.model().index(11, 0))
    assert simple_view.isExpanded(simple_view.model().index(13, 0))


def test_deselect_variables(qtbot, simple_view: SimpleView, daily_df: pd.DataFrame):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "kW"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "kW")
    ]
    simple_view.populate_view(
        daily_df,
        "daily",
        is_tree=True,
        power_units="kW",
    )
    simple_view.select_variables(selected)
    proxy_rows = simple_view.selectionModel().selectedRows()
    variables_data = [simple_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data

    with qtbot.wait_signal(simple_view.selectionCleared):
        simple_view.deselect_all_variables()

    assert not simple_view.selectionModel().selectedRows()


def test_select_variables(simple_view: SimpleView):
    selected = [
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W", "W"),
        VariableData("BOILER", "Boiler Gas Rate", "W", "W")
    ]
    simple_view.select_variables(selected)

    proxy_rows = simple_view.selectionModel().selectedRows()
    variables_data = [simple_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data
