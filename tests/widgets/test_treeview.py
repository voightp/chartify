from copy import copy

import pytest
from PySide2.QtCore import QModelIndex, Qt
from PySide2.QtWidgets import QHeaderView
from esofile_reader import GenericFile
from esofile_reader.df.level_names import UNITS_LEVEL

from chartify.settings import OutputType
from chartify.ui.treeview import TreeView, ViewType, ViewMask
from chartify.ui.treeview_model import FilterModel, ViewModel
from chartify.utils.utils import VariableData, FilterTuple
from tests.conftest import ESO_FILE_EXCEL_PATH

default_units = dict(energy_units="J", rate_units="W", units_system="SI", rate_to_energy=False)


@pytest.fixture(scope="session")
def session_treeview_test_file():
    return GenericFile.from_excel(ESO_FILE_EXCEL_PATH)


@pytest.fixture(scope="function")
def treeview_test_file(session_treeview_test_file):
    copied_file = copy(session_treeview_test_file)
    copied_file.id_ = 0  # mock id attribute
    return copied_file


def _setup_treeview(qtbot, treeview_test_file, table_name):
    model = ViewModel(table_name, treeview_test_file)
    treeview = TreeView(model, OutputType.STANDARD)
    treeview.setFixedWidth(419)
    with ViewMask(treeview, show_source_units=False) as mask:
        mask.update_treeview(treeview, is_tree=True, units_kwargs=default_units)
    qtbot.addWidget(treeview)
    treeview.show()
    return treeview


@pytest.fixture(scope="function")
def monthly_no_ndays(qtbot, treeview_test_file):
    return _setup_treeview(qtbot, treeview_test_file, "monthly-no-ndays")


@pytest.fixture(scope="function")
def hourly(qtbot, treeview_test_file):
    return _setup_treeview(qtbot, treeview_test_file, "hourly")


@pytest.fixture(scope="function")
def daily(qtbot, treeview_test_file):
    return _setup_treeview(qtbot, treeview_test_file, "daily")


@pytest.fixture(scope="function")
def hourly_simple(qtbot, treeview_test_file):
    return _setup_treeview(qtbot, treeview_test_file, "hourly-simple")


@pytest.fixture(scope="function")
def daily_simple(qtbot, treeview_test_file):
    return _setup_treeview(qtbot, treeview_test_file, "daily-simple")


def test_init_hourly(hourly: TreeView):
    assert hourly.rootIsDecorated()
    assert hourly.uniformRowHeights()
    assert hourly.isSortingEnabled()
    assert hourly.hasMouseTracking()
    assert hourly.dragEnabled()

    assert not hourly.wordWrap()
    assert not hourly.alternatingRowColors()

    assert hourly.selectionBehavior() == TreeView.SelectRows
    assert hourly.selectionMode() == TreeView.ExtendedSelection
    assert hourly.editTriggers() == TreeView.NoEditTriggers
    assert hourly.defaultDropAction() == Qt.CopyAction
    assert hourly.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert hourly.focusPolicy() == Qt.NoFocus

    assert hourly.id_ == 0
    assert hourly.source_model.name == "hourly"
    assert hourly.output_type == OutputType.STANDARD

    assert hourly.proxy_model.sortCaseSensitivity() == Qt.CaseInsensitive
    assert hourly.proxy_model.isRecursiveFilteringEnabled()
    assert not hourly.proxy_model.dynamicSortFilter()


@pytest.mark.parametrize(
    "tree_view,view_type,is_tree,rate_to_energy",
    [
        (pytest.lazy_fixture("hourly"), ViewType.TREE, True, True),
        (pytest.lazy_fixture("monthly_no_ndays"), ViewType.TREE, True, False),
        (pytest.lazy_fixture("daily_simple"), ViewType.SIMPLE, False, True),
    ],
)
def test_view_properties(tree_view: TreeView, view_type, is_tree, rate_to_energy):
    assert isinstance(tree_view.source_model, ViewModel)
    assert isinstance(tree_view.proxy_model, FilterModel)
    assert tree_view.view_type == view_type
    assert tree_view.is_tree == is_tree
    assert tree_view.allow_rate_to_energy == rate_to_energy


@pytest.mark.parametrize(
    "tree_view,row_count, source_row_count, total_row_count",
    [
        (pytest.lazy_fixture("hourly"), 49, 49, 105),
        (pytest.lazy_fixture("daily"), 49, 49, 105),
        (pytest.lazy_fixture("hourly_simple"), 49, 49, 49),
        (pytest.lazy_fixture("daily_simple"), 49, 49, 49),
    ],
)
def test_model_rows(qtbot, tree_view: TreeView, row_count, source_row_count, total_row_count):
    assert tree_view.model().rowCount() == row_count
    assert tree_view.model().sourceModel().rowCount() == source_row_count
    assert tree_view.model().sourceModel().count_rows() == total_row_count


def test_first_column_spanned(hourly: TreeView):
    proxy_model = hourly.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_proxy_index(index)
        if item.hasChildren():
            assert hourly.isFirstColumnSpanned(i, hourly.rootIndex())
            for j in range(item.rowCount()):
                assert not hourly.isFirstColumnSpanned(j, index)
        else:
            assert not hourly.isFirstColumnSpanned(i, hourly.rootIndex())


def test_initial_view_appearance_hidden_source(hourly: TreeView):
    assert hourly.header().sectionSize(0) == 200
    assert hourly.header().sectionSize(1) == 140
    assert hourly.header().sectionSize(2) == 0
    assert hourly.header().sectionSize(3) == 60

    assert not hourly.header().stretchLastSection()
    assert hourly.header().sectionResizeMode(0) == QHeaderView.Interactive
    assert hourly.header().sectionResizeMode(1) == QHeaderView.Stretch
    assert hourly.header().sectionResizeMode(2) == QHeaderView.Fixed
    assert hourly.header().sectionResizeMode(3) == QHeaderView.Fixed

    assert hourly.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_initial_view_appearance_simple_hidden_source(daily_simple: TreeView):
    assert daily_simple.header().sectionSize(0) == 340
    assert daily_simple.header().sectionSize(1) == 0
    assert daily_simple.header().sectionSize(2) == 60

    assert not daily_simple.header().stretchLastSection()
    assert daily_simple.header().sectionResizeMode(0) == QHeaderView.Stretch
    assert daily_simple.header().sectionResizeMode(1) == QHeaderView.Fixed
    assert daily_simple.header().sectionResizeMode(2) == QHeaderView.Fixed

    assert daily_simple.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_build_plain_view(qtbot, hourly: TreeView):
    hourly.update_model(tree_node=None, **default_units)

    assert hourly.model().rowCount() == 77
    assert hourly.model().sourceModel().rowCount() == 77

    assert hourly.source_model.name == "hourly"
    assert not hourly.is_tree
    assert hourly.allow_rate_to_energy


def test_first_column_not_spanned(hourly: TreeView):
    hourly.update_model(tree_node=None, **default_units)
    proxy_model = hourly.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_proxy_index(index)
        if item.hasChildren():
            assert False, "Plain model should not have any child items!"
        else:
            assert not hourly.isFirstColumnSpanned(i, hourly.rootIndex())


def test_resize_header_show_source_units(qtbot, hourly: TreeView):
    hourly.update_model(tree_node=None, **default_units)
    hourly.hide_section(UNITS_LEVEL, False)
    hourly.set_header_resize_mode({"interactive": 150, "fixed": 100})
    assert hourly.header().sectionSize(0) == 150
    assert hourly.header().sectionSize(1) == 67
    assert hourly.header().sectionSize(2) == 100
    assert hourly.header().sectionSize(3) == 100


def test_resize_header_hide_source_units(hourly: TreeView):
    hourly.update_model(tree_node=None, **default_units)
    hourly.hide_section(UNITS_LEVEL, True)
    hourly.set_header_resize_mode({"interactive": 250, "fixed": 100})
    assert hourly.header().sectionSize(0) == 250
    assert hourly.header().sectionSize(1) == 67
    assert hourly.header().sectionSize(2) == 0
    assert hourly.header().sectionSize(3) == 100


def test_on_tree_node_changed_build_tree(qtbot, hourly: TreeView):
    assert hourly.get_visual_column_data() == ("type", "key", "proxy_units", "units")
    with qtbot.wait_signal(hourly.treeNodeChanged, timeout=1000):
        hourly.header().moveSection(2, 0)
        assert hourly.get_visual_column_data() == ("proxy_units", "type", "key", "units")
        assert hourly.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_tree_node_changed_dont_build_tree(qtbot, hourly: TreeView):
    assert hourly.get_visual_column_data() == ("type", "key", "proxy_units", "units")
    with qtbot.assertNotEmitted(hourly.treeNodeChanged):
        hourly.header().moveSection(2, 1)


def test_on_section_moved_rebuild(qtbot, hourly: TreeView):
    def cb(treeview):
        return treeview is hourly

    with qtbot.wait_signal(hourly.treeNodeChanged, check_params_cb=cb):
        hourly.header().moveSection(0, 2)


@pytest.mark.parametrize(
    "tree_view,test_data, test_row, parent_row",
    [
        (
            pytest.lazy_fixture("hourly"),
            VariableData("BOILER", "Boiler Gas Rate", "W"),
            1,
            None,
        ),
        (pytest.lazy_fixture("daily"), VariableData("BOILER", "Boiler Gas Rate", "W"), 1, None),
        (
            pytest.lazy_fixture("hourly_simple"),
            VariableData("Boiler Gas Rate", None, "W"),
            1,
            None,
        ),
        (
            pytest.lazy_fixture("daily_simple"),
            VariableData("Boiler Gas Rate", None, "W"),
            1,
            None,
        ),
    ],
)
def test_on_double_clicked(qtbot, tree_view: TreeView, test_data, test_row, parent_row):
    def cb(treeview, row, parent, variable_data):
        test_parent_index = (
            treeview.source_model.index(parent_row, 0)
            if parent_row is not None
            else QModelIndex()
        )
        assert row == test_row
        assert treeview is tree_view
        assert parent == test_parent_index
        assert variable_data == test_data
        return True

    point = tree_view.visualRect(tree_view.model().index(1, 0)).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    with qtbot.wait_signal(tree_view.itemDoubleClicked, check_params_cb=cb):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_double_clicked_child(qtbot, hourly: TreeView):
    hourly.expandAll()

    def cb(treeview, row, parent, variable_data):
        assert row == 0
        assert treeview is hourly
        assert parent == treeview.source_model.index(7, 0)
        assert variable_data == VariableData(
            "BLOCK1:ZONEA FAN COIL UNIT COOLING COIL", "Cooling Coil Sensible Cooling Rate", "W"
        )
        return True

    parent_item = hourly.source_model.findItems("Cooling Coil Sensible Cooling Rate", column=0)[
        0
    ]
    parent_index = hourly.source_model.indexFromItem(parent_item)
    proxy_parent = hourly.proxy_model.mapFromSource(parent_index)
    point = hourly.visualRect(hourly.model().index(0, 1, parent=proxy_parent)).center()
    qtbot.mouseMove(hourly.viewport(), pos=point)
    with qtbot.wait_signal(hourly.itemDoubleClicked, check_params_cb=cb):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(hourly.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(hourly.viewport(), Qt.LeftButton, pos=point)


def test_on_double_clicked_parent(qtbot, hourly: TreeView):
    index = hourly.model().index(7, 0)
    point = hourly.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(hourly.viewport(), pos=point)
    with qtbot.assert_not_emitted(hourly.itemDoubleClicked):
        with qtbot.wait_signal(hourly.doubleClicked):
            # need to click first as single double click would emit only pressed signal
            qtbot.mouseClick(hourly.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(hourly.viewport(), Qt.LeftButton, pos=point)

    assert hourly.isExpanded(index)


def test_select_all_children_expanded_parent(qtbot, hourly: TreeView):
    index = hourly.model().index(7, 0)
    point = hourly.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(hourly.viewport(), pos=point)
    # need to click first as single double click would emit only pressed signal
    qtbot.mouseClick(hourly.viewport(), Qt.LeftButton, pos=point)
    qtbot.mouseDClick(hourly.viewport(), Qt.LeftButton, pos=point)
    assert hourly.isExpanded(index)

    def test_data(variable_data):
        dt = [
            VariableData(
                "BLOCK1:ZONEA FAN COIL UNIT COOLING COIL",
                "Cooling Coil Sensible Cooling Rate",
                "W",
            ),
            VariableData(
                "BLOCK1:ZONEB FAN COIL UNIT COOLING COIL",
                "Cooling Coil Sensible Cooling Rate",
                "W",
            ),
        ]
        return dt == variable_data

    with qtbot.wait_signal(hourly.selectionPopulated, check_params_cb=test_data):
        qtbot.mouseClick(hourly.viewport(), Qt.LeftButton, pos=point)


@pytest.mark.parametrize(
    "tree_view,test_data",
    [
        (pytest.lazy_fixture("hourly"), VariableData("BOILER", "Boiler Gas Rate", "W")),
        (pytest.lazy_fixture("daily"), VariableData("BOILER", "Boiler Gas Rate", "W")),
        (pytest.lazy_fixture("hourly_simple"), VariableData("Boiler Gas Rate", None, "W")),
        (pytest.lazy_fixture("daily_simple"), VariableData("Boiler Gas Rate", None, "W")),
    ],
)
def test_on_pressed(qtbot, tree_view: TreeView, test_data):
    def variable_data(vd):
        return vd == [test_data]

    index = tree_view.model().index(1, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    signals = [tree_view.pressed, tree_view.selectionPopulated]
    callbacks = [None, variable_data]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_pressed_collapsed_parent(qtbot, hourly: TreeView):
    def variable_data1(index):
        data = hourly.model().data(index)
        return data == "Cooling Coil Sensible Cooling Rate"

    index = hourly.model().index(7, 0)
    press_point = hourly.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(hourly.viewport(), pos=press_point)
    signals = [hourly.pressed, hourly.selectionCleared]
    callbacks = [variable_data1, None]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mousePress(hourly.viewport(), Qt.LeftButton, pos=press_point)

    assert not hourly.isExpanded(index)


def test_on_pressed_right_mb(qtbot, hourly: TreeView):
    index = hourly.model().index(1, 0)
    point = hourly.visualRect(index).center()
    qtbot.mouseMove(hourly.viewport(), pos=point)
    with qtbot.assert_not_emitted(hourly.pressed,):
        qtbot.mousePress(hourly.viewport(), Qt.RightButton, pos=point)


def test_get_visual_data(hourly: TreeView):
    assert hourly.get_visual_column_data() == ("type", "key", "proxy_units", "units")
    hourly.reorder_columns(("proxy_units", "type", "key", "units"))
    assert hourly.get_visual_column_data() == ("proxy_units", "type", "key", "units")


def test_get_visual_ixs(hourly: TreeView):
    assert hourly.get_visual_column_mapping() == {
        "type": 0,
        "key": 1,
        "proxy_units": 2,
        "units": 3,
    }


def test_update_model(hourly: TreeView):
    units = {
        "energy_units": "J",
        "rate_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    hourly.update_model(tree_node="key", **units)
    assert hourly.source_model.name == "hourly"
    assert hourly.source_model.energy_units == "J"
    assert hourly.source_model.rate_units == "MW"
    assert hourly.source_model.units_system == "IP"
    assert hourly.source_model.rate_to_energy
    assert hourly.source_model.tree_node == "key"


def test_update_units(hourly: TreeView,):
    units = {
        "energy_units": "J",
        "rate_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    hourly.update_units(**units)
    assert hourly.source_model.name == "hourly"
    assert hourly.source_model.energy_units == "J"
    assert hourly.source_model.rate_units == "MW"
    assert hourly.source_model.units_system == "IP"
    assert hourly.source_model.rate_to_energy
    assert hourly.source_model.tree_node == "type"


def test_update_units_proxy_tree_node(hourly: TreeView):
    units = {
        "energy_units": "J",
        "rate_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    hourly.update_units(**units)
    assert hourly.source_model.name == "hourly"
    assert hourly.source_model.energy_units == "J"
    assert hourly.source_model.rate_units == "MW"
    assert hourly.source_model.units_system == "IP"
    assert hourly.source_model.rate_to_energy
    assert hourly.source_model.tree_node == "type"


def test_scroll_to(qtbot, hourly: TreeView):
    v = VariableData("BLOCK1:ZONEA", "Zone Infiltration Air Change Rate", "ach")
    with qtbot.wait_signal(hourly.verticalScrollBar().valueChanged):
        hourly.scroll_to(v)
    assert hourly.verticalScrollBar().value() == 28


@pytest.mark.parametrize(
    "tree_view,test_data",
    [
        (
            pytest.lazy_fixture("hourly"),
            [
                VariableData("BOILER", "Boiler Gas Rate", "W"),
                VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
            ],
        ),
        (
            pytest.lazy_fixture("hourly_simple"),
            [
                VariableData("Boiler Gas Rate", None, "W"),
                VariableData("Boiler Ancillary Electric Power", None, "W"),
            ],
        ),
    ],
)
def test_deselect_variables(qtbot, tree_view: TreeView, test_data):
    tree_view.select_variables(test_data)
    with qtbot.wait_signal(tree_view.selectionCleared):
        tree_view.deselect_all_variables()
    assert not tree_view.selectionModel().selectedRows()


@pytest.mark.parametrize(
    "tree_view,test_data",
    [
        (
            pytest.lazy_fixture("hourly"),
            [
                VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
                VariableData("BOILER", "Boiler Gas Rate", "W"),
            ],
        ),
        (
            pytest.lazy_fixture("hourly_simple"),
            [
                VariableData("Boiler Ancillary Electric Power", None, "W"),
                VariableData("Boiler Gas Rate", None, "W"),
            ],
        ),
    ],
)
def test_select_variables(qtbot, tree_view: TreeView, test_data):
    def cb(variable_data):
        return set(test_data) == set(variable_data)

    with qtbot.wait_signal(tree_view.selectionPopulated, check_params_cb=cb):
        tree_view.select_variables(test_data)


def test_filter_view(qtbot, daily: TreeView):
    daily.filter_view(FilterTuple(key="block1:zonea", type="temperature", proxy_units=""))

    assert daily.model().rowCount() == 3
    assert daily.model().sourceModel().rowCount() == 49

    index0 = daily.model().index(0, 0)
    index1 = daily.model().index(1, 0)
    index2 = daily.model().index(2, 0)

    assert daily.isExpanded(index0)
    assert daily.isExpanded(index1)
    assert daily.isExpanded(index2)

    vd0 = VariableData("BLOCK1:ZONEA", "Zone Mean Air Temperature", "C")
    vd1 = VariableData("BLOCK1:ZONEA", "Zone Mean Radiant Temperature", "C")
    vd2 = VariableData("BLOCK1:ZONEA", "Zone Operative Temperature", "C")

    parent0 = daily.proxy_model.mapToSource(index0)
    parent1 = daily.proxy_model.mapToSource(index1)
    parent2 = daily.proxy_model.mapToSource(index2)

    row0 = daily.proxy_model.mapToSource(index0.child(0, 0)).row()
    row1 = daily.proxy_model.mapToSource(index1.child(0, 0)).row()
    row2 = daily.proxy_model.mapToSource(index2.child(0, 0)).row()

    assert daily.source_model.get_row_variable_data(row0, parent0) == vd0
    assert daily.source_model.get_row_variable_data(row1, parent1) == vd1
    assert daily.source_model.get_row_variable_data(row2, parent2) == vd2

    child_index_invalid = daily.model().index(1, 0, index0)
    assert child_index_invalid == QModelIndex()


@pytest.mark.parametrize(
    "tree_view, tree_node, rebuild",
    [
        (pytest.lazy_fixture("hourly_simple"), "type", False),
        (pytest.lazy_fixture("hourly_simple"), None, False),
        (pytest.lazy_fixture("hourly"), None, False),
        (pytest.lazy_fixture("hourly"), "type", True),
    ],
)
def test_needs_rebuild(tree_view, tree_node, rebuild):
    tree_view.update_model(tree_node=None, **default_units)
    assert tree_view.source_model.needs_rebuild(tree_node) is rebuild


@pytest.mark.parametrize(
    "tree_view, rate, energy, system, rate_to_energy, update",
    [
        (pytest.lazy_fixture("hourly_simple"), "J", "W", "SI", True, True),
        (pytest.lazy_fixture("hourly_simple"), "J", "W", "SI", False, False),
        (pytest.lazy_fixture("hourly_simple"), "kWh", "W", "SI", False, True),
        (pytest.lazy_fixture("hourly"), "J", "W", "SI", True, True),
        (pytest.lazy_fixture("hourly"), "J", "W", "SI", False, False),
        (pytest.lazy_fixture("hourly"), "J", "kW", "SI", False, True),
        (pytest.lazy_fixture("hourly"), "J", "W", "IP", False, True),
        (pytest.lazy_fixture("hourly"), "kWh", "W", "SI", False, True),
        (pytest.lazy_fixture("monthly_no_ndays"), "J", "W", "SI", True, False),
    ],
)
def test_needs_units_update(tree_view, rate, energy, system, rate_to_energy, update):
    tree_view.update_model(tree_node=None, **default_units)
    needs_update = tree_view.source_model.needs_units_update(
        rate, energy, system, rate_to_energy
    )
    assert needs_update is update
