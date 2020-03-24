from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt
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
    simple_view.update_view_appearance()
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
    assert not simple_view.is_tree
    assert not simple_view.rate_to_energy
    assert simple_view.units_system == "SI"
    assert simple_view.energy_units == "J"
    assert not simple_view.next_update_forced


def test_initial_view_appearance(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    assert simple_view.header().sectionSize(0) == 330
    assert simple_view.header().sectionSize(1) == 70

    assert not simple_view.header().stretchLastSection()
    assert simple_view.header().sectionResizeMode(0) == QHeaderView.Stretch
    assert simple_view.header().sectionResizeMode(1) == QHeaderView.Fixed

    assert simple_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_view_resized_stretch(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    simple_view.update_view_appearance()
    with qtbot.assertNotEmitted(simple_view.viewSettingsChanged):
        simple_view.header().resizeSection(1, 125)


def test_on_section_moved(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def test_header(dct):
        return dct["header"] == ("units", "variable")

    with qtbot.wait_signal(simple_view.viewSettingsChanged, check_params_cb=test_header):
        simple_view.header().moveSection(0, 1)


def test_on_slider_moved(simple_view: SimpleView, hourly_df: pd.DataFrame):
    simple_view.verticalScrollBar().setSliderPosition(10)

    assert simple_view.verticalScrollBar().value() == 10


def test_on_double_clicked(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    def variable_data(index):
        test_data = VariableData(None, "Boiler Gas Rate", "W", "W")
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


def test_on_double_clicked_second_column(
        qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame
):
    def variable_data(index):
        test_data = VariableData(None, "Boiler Gas Rate", "W", "W")
        data = simple_view.model().data_at_index(index.siblingAtColumn(0))
        return test_data == data

    point = simple_view.visualRect(simple_view.model().index(1, 1)).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(simple_view.viewport(), pos=point)
    signals = [simple_view.doubleClicked, simple_view.itemDoubleClicked]
    callbacks = [variable_data, None]
    with  qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(simple_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(simple_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    test_data = VariableData(None, "Boiler Gas Rate", "W", "W")

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


def test_on_pressed_right_mb(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    index = simple_view.model().index(1, 0)
    point = simple_view.visualRect(index).center()
    qtbot.mouseMove(simple_view.viewport(), pos=point)
    with qtbot.assert_not_emitted(simple_view.pressed, ):
        qtbot.mousePress(simple_view.viewport(), Qt.RightButton, pos=point)


def test_is_tree_kwarg(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(
        variables_df=daily_df,
        interval="daily",
        is_tree=True
    )
    # simpleview is always plain table
    assert not simple_view.is_tree


def test_filter_view(simple_view: SimpleView):
    simple_view.filter_view(FilterTuple(key="block1:zonea", variable="temperature", units=""))

    assert simple_view.model().rowCount() == 5
    assert simple_view.model().sourceModel().rowCount() == 49

    test_data = [
        VariableData(None, "Site Outdoor Air Dewpoint Temperature", "C", "C"),
        VariableData(None, "Site Outdoor Air Drybulb Temperature", "C", "C"),
        VariableData(None, "Zone Mean Air Temperature", "C", "C"),
        VariableData(None, "Zone Mean Radiant Temperature", "C", "C"),
        VariableData(None, "Zone Operative Temperature", "C", "C"),
    ]

    for i, test_var in enumerate(test_data):
        index = simple_view.model().index(i, 0)
        data = simple_view.model().data_at_index(index)
        print(data)
        print(test_var)
        assert data == test_var


def test_get_visual_names(simple_view: SimpleView):
    assert simple_view.get_visual_names() == ("variable", "units")

    simple_view.reshuffle_columns(("units", "variable"))
    assert simple_view.get_visual_names() == ("units", "variable")


def test_get_visual_ixs(simple_view: SimpleView):
    assert simple_view.get_visual_indexes() == {"variable": 0, "units": 1}


def test_build_view_kwargs_rate_to_energy(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(daily_df, "daily", is_tree=True, rate_to_energy=True)
    simple_view.update_view_appearance()
    proxy_model = simple_view.model()
    test_data = VariableData(None, "Boiler Gas Rate", "W", "J")
    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 1)) == "J"


def test_build_view_kwargs_units_system(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(daily_df, "daily", is_tree=True, units_system="IP")
    simple_view.update_view_appearance()
    proxy_model = simple_view.model()
    test_data = VariableData(
        None, "Site Outdoor Air Dewpoint Temperature", "C", "F"
    )

    assert proxy_model.data_at_index(proxy_model.index(22, 0)) == test_data
    assert proxy_model.data(proxy_model.index(22, 1)) == "F"


def test_build_view_kwargs_energy_units(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(
        daily_df,
        "daily",
        is_tree=True,
        rate_to_energy=True,
        energy_units="MWh"
    )
    simple_view.update_view_appearance()
    proxy_model = simple_view.model()
    test_data = VariableData(None, "Boiler Gas Rate", "W", "MWh")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 1)) == "MWh"


def test_build_view_kwargs_power_units(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.populate_view(daily_df, "daily", is_tree=True, power_units="MW")
    simple_view.update_view_appearance()
    proxy_model = simple_view.model()
    test_data = VariableData(None, "Boiler Gas Rate", "W", "MW")

    assert proxy_model.data_at_index(proxy_model.index(1, 0)) == test_data
    assert proxy_model.data(proxy_model.index(1, 1)) == "MW"


def test_update_view_appearance(simple_view: SimpleView, daily_df: pd.DataFrame):
    header = ("units", "variable")
    simple_view.populate_view(
        daily_df,
        "daily",
        header=header,
    )

    widths = {"fixed": 50}
    simple_view.update_view_appearance(header=header, widths=widths)

    assert simple_view.header().sectionSize(0) == 50
    assert simple_view.header().sectionSize(1) == 350

    assert simple_view.get_visual_names() == ("units", "variable")


def test_update_view_appearance_default(simple_view: SimpleView, daily_df: pd.DataFrame):
    simple_view.update_view_appearance()

    assert simple_view.header().sectionSize(0) == 330
    assert simple_view.header().sectionSize(1) == 70

    assert simple_view.get_visual_names() == ("variable", "units")


def test_scroll_to(qtbot, simple_view: SimpleView, hourly_df: pd.DataFrame):
    v = VariableData(None, "Zone Infiltration Air Change Rate", "ach", "ach")
    with qtbot.wait_signal(simple_view.verticalScrollBar().valueChanged):
        simple_view.scroll_to(v, "variable")

    assert simple_view.verticalScrollBar().value() == 27


def test_deselect_variables(qtbot, simple_view: SimpleView, daily_df: pd.DataFrame):
    selected = [
        VariableData(None, "Boiler Ancillary Electric Power", "W", "kW"),
        VariableData(None, "Boiler Gas Rate", "W", "kW")
    ]
    simple_view.populate_view(
        daily_df,
        "daily",
        power_units="kW",
    )
    simple_view.update_view_appearance()
    simple_view.select_variables(selected)
    proxy_rows = simple_view.selectionModel().selectedRows()
    variables_data = [simple_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data

    with qtbot.wait_signal(simple_view.selectionCleared):
        simple_view.deselect_all_variables()

    assert not simple_view.selectionModel().selectedRows()


def test_select_variables(qtbot, simple_view: SimpleView):
    def variable_data(data):
        return data == selected

    selected = [
        VariableData(None, "Boiler Ancillary Electric Power", "W", "W"),
        VariableData(None, "Boiler Gas Rate", "W", "W")
    ]

    with qtbot.wait_signal(simple_view.selectionPopulated, check_params_cb=variable_data):
        simple_view.select_variables(selected)

    proxy_rows = simple_view.selectionModel().selectedRows()
    variables_data = [simple_view.model().data_at_index(index) for index in proxy_rows]

    assert selected == variables_data


def test_select_variables_invalid(qtbot, simple_view: SimpleView):
    selected = [
        VariableData(None, "FOO", "W", "W"),
        VariableData(None, "BAR", "W", "W")
    ]

    with qtbot.wait_signal(simple_view.selectionCleared):
        simple_view.select_variables(selected)


def test_drag(qtbot, simple_view: SimpleView):
    # difficult to test something properly as QTest mouse
    # actions do not have an impact on drag and drop
    import threading

    def drag():
        simple_view.startDrag(Qt.CopyAction)

    t = threading.Thread(target=drag)
    t.start()
    t.join(0.1)
