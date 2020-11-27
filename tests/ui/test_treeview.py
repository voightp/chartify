from pathlib import Path

import pandas as pd
import pytest
from PySide2.QtCore import Qt, QModelIndex
from PySide2.QtWidgets import QHeaderView, QSizePolicy
from esofile_reader import EsoFile, GenericFile
from esofile_reader.constants import UNITS_LEVEL

from chartify.ui.treeview import TreeView, ViewModel, FilterModel
from chartify.utils.utils import VariableData, FilterTuple
from tests import ROOT

WIDTH = 402


@pytest.fixture(scope="module")
def eso_file():
    return EsoFile(Path(ROOT, "eso_files", "eplusout1.eso"))


@pytest.fixture(scope="module")
def excel_file():
    return GenericFile.from_excel(Path(ROOT, "eso_files", "simple_view.xlsx"))


@pytest.fixture
def hourly_df(eso_file):
    return eso_file.get_header_df("hourly").copy()


@pytest.fixture
def daily_df(eso_file):
    return eso_file.get_header_df("daily").copy()


@pytest.fixture
def hourly_df_simple(excel_file):
    return excel_file.get_header_df("hourly-simple").copy()


@pytest.fixture
def daily_df_simple(excel_file):
    return excel_file.get_header_df("daily-simple").copy()


@pytest.fixture
def tree_view(qtbot, hourly_df, daily_df, hourly_df_simple, daily_df_simple):
    hourly_model = ViewModel(
        "hourly", hourly_df, is_simple=False, allow_rate_to_energy=False, tree_node="type"
    )
    daily_model = ViewModel(
        "daily", daily_df, is_simple=False, allow_rate_to_energy=True, tree_node="type"
    )
    hourly_model_simple = ViewModel(
        "hourly-simple",
        hourly_df_simple,
        is_simple=True,
        allow_rate_to_energy=False,
        tree_node=None,
    )
    daily_model_simple = ViewModel(
        "daily-simple",
        daily_df_simple,
        is_simple=True,
        allow_rate_to_energy=True,
        tree_node=None,
    )
    tree_view = TreeView(
        0,
        {
            "hourly": hourly_model,
            "daily": daily_model,
            "hourly-simple": hourly_model_simple,
            "daily-simple": daily_model_simple,
        },
    )
    tree_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    tree_view.setFixedWidth(WIDTH)
    tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tree_view.set_and_update_model(header_df=hourly_df, table_name="hourly", tree_node="type")
    tree_view.update_appearance(
        widths={"interactive": 200, "fixed": 70}, hide_source_units=True
    )
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
    assert list(tree_view.models.keys()) == ["hourly", "daily", "hourly-simple", "daily-simple"]

    assert tree_view.proxy_model.sortCaseSensitivity() == Qt.CaseInsensitive
    assert tree_view.proxy_model.isRecursiveFilteringEnabled()
    assert not tree_view.proxy_model.dynamicSortFilter()


@pytest.mark.parametrize(
    "table,view_type,is_tree,rate_to_energy",
    [
        ("hourly", "tree", True, False),
        ("daily", "tree", True, True),
        ("hourly-simple", "simple", False, False),
        ("daily-simple", "simple", False, True),
    ],
)
def test_view_properties(tree_view: TreeView, table, view_type, is_tree, rate_to_energy):
    tree_view.set_model(table)
    assert isinstance(tree_view.source_model, ViewModel)
    assert isinstance(tree_view.proxy_model, FilterModel)
    assert tree_view.view_type == view_type
    assert tree_view.is_tree == is_tree
    assert tree_view.allow_rate_to_energy == rate_to_energy


@pytest.mark.parametrize(
    "table,row_count, source_row_count, total_row_count",
    [
        ("hourly", 49, 49, 105),
        ("daily", 49, 49, 105),
        ("hourly-simple", 49, 49, 49),
        ("daily-simple", 49, 49, 49),
    ],
)
def test_model_rows(
    qtbot, tree_view: TreeView, table, row_count, source_row_count, total_row_count
):
    tree_view.set_model(table)
    assert tree_view.model().rowCount() == row_count
    assert tree_view.model().sourceModel().rowCount() == source_row_count
    assert tree_view.model().sourceModel().count_rows() == total_row_count


def test_simple_model_note_stays_none(tree_view: TreeView, daily_df_simple: pd.DataFrame):
    tree_view.set_and_update_model(daily_df_simple, "daily-simple", tree_node="key")
    assert tree_view.source_model.tree_node is None


def test_first_column_spanned(tree_view: TreeView):
    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_proxy_index(index)
        if item.hasChildren():
            assert tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())
            for j in range(item.rowCount()):
                assert not tree_view.isFirstColumnSpanned(j, index)
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_initial_view_appearance_hidden_source(tree_view: TreeView):
    assert tree_view.header().sectionSize(0) == 200
    assert tree_view.header().sectionSize(1) == 130
    assert tree_view.header().sectionSize(2) == 0
    assert tree_view.header().sectionSize(3) == 70

    assert not tree_view.header().stretchLastSection()
    assert tree_view.header().sectionResizeMode(0) == QHeaderView.Interactive
    assert tree_view.header().sectionResizeMode(1) == QHeaderView.Stretch
    assert tree_view.header().sectionResizeMode(2) == QHeaderView.Fixed
    assert tree_view.header().sectionResizeMode(3) == QHeaderView.Fixed

    assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_initial_view_appearance_simple_hidden_source(tree_view: TreeView):
    tree_view.set_model("daily-simple")
    tree_view.update_appearance(
        widths={"fixed": 70}, header=("key", "proxy_units", "units"), hide_source_units=True
    )
    assert tree_view.header().sectionSize(0) == 330
    assert tree_view.header().sectionSize(1) == 0
    assert tree_view.header().sectionSize(2) == 70

    assert not tree_view.header().stretchLastSection()
    assert tree_view.header().sectionResizeMode(0) == QHeaderView.Stretch
    assert tree_view.header().sectionResizeMode(1) == QHeaderView.Fixed
    assert tree_view.header().sectionResizeMode(2) == QHeaderView.Fixed

    assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_build_plain_view(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model(header_df=hourly_df, tree_node=None)

    assert tree_view.model().rowCount() == 77
    assert tree_view.model().sourceModel().rowCount() == 77

    assert tree_view.source_model.name == "hourly"
    assert not tree_view.is_tree
    assert not tree_view.allow_rate_to_energy


def test_first_column_not_spanned(tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model(header_df=hourly_df, tree_node=None)
    proxy_model = tree_view.model()
    for i in range(proxy_model.rowCount()):
        index = proxy_model.index(i, 0)
        item = proxy_model.item_at_proxy_index(index)
        if item.hasChildren():
            assert False, "Plain model should not have any child items!"
        else:
            assert not tree_view.isFirstColumnSpanned(i, tree_view.rootIndex())


def test_resize_header_show_source_units(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model(header_df=hourly_df, tree_node=None)
    tree_view.hide_section(UNITS_LEVEL, False)
    tree_view.set_header_resize_mode({"interactive": 150, "fixed": 100})
    assert tree_view.header().sectionSize(0) == 150
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 100
    assert tree_view.header().sectionSize(3) == 100


def test_resize_header_hide_source_units(tree_view: TreeView, hourly_df: pd.DataFrame):
    tree_view.update_model(header_df=hourly_df, tree_node=None)
    tree_view.hide_section(UNITS_LEVEL, True)
    tree_view.set_header_resize_mode({"interactive": 250, "fixed": 100})
    assert tree_view.header().sectionSize(0) == 250
    assert tree_view.header().sectionSize(1) == 50
    assert tree_view.header().sectionSize(2) == 0
    assert tree_view.header().sectionSize(3) == 100


def test_on_tree_node_changed_build_tree(qtbot, tree_view: TreeView):
    assert tree_view.get_visual_column_data() == ("type", "key", "proxy_units", "units")
    with qtbot.wait_signal(tree_view.viewTreeNodeChanged, timeout=1000):
        tree_view.header().moveSection(2, 0)
        assert tree_view.get_visual_column_data() == ("proxy_units", "type", "key", "units")
        assert tree_view.header().sortIndicatorOrder() == Qt.AscendingOrder


def test_on_tree_node_changed_dont_build_tree(qtbot, tree_view: TreeView):
    assert tree_view.get_visual_column_data() == ("type", "key", "proxy_units", "units")
    with qtbot.assertNotEmitted(tree_view.viewTreeNodeChanged):
        tree_view.header().moveSection(2, 1)


def test_on_view_resized(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def test_size(view_type, width):
        return view_type == "tree" and width == 125

    with qtbot.wait_signal(tree_view.viewColumnResized, check_params_cb=test_size):
        tree_view.header().resizeSection(0, 125)


def test_on_view_resized_stretch(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    with qtbot.assertNotEmitted(tree_view.viewColumnResized):
        tree_view.header().resizeSection(1, 125)


def test_on_section_moved_rebuild(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def test_header(view_type, header):
        return view_type == "tree" and header == ("key", "proxy_units", "type", "units")

    signals = [(tree_view.viewColumnOrderChanged, "0"), (tree_view.viewTreeNodeChanged, "1")]
    callbacks = [test_header, None]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        tree_view.header().moveSection(0, 2)


def test_on_section_moved_plain_view(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    def test_header(view_type, header):
        return view_type == "tree" and header == ("key", "proxy_units", "type", "units")

    tree_view.update_model(header_df=hourly_df, tree_node=None)
    tree_view.reorder_columns(("type", "key", "proxy_units", "units"))
    with qtbot.wait_signal(tree_view.viewColumnOrderChanged, check_params_cb=test_header):
        tree_view.header().moveSection(0, 2)


def test_on_slider_moved(tree_view: TreeView):
    tree_view.verticalScrollBar().setSliderPosition(10)
    assert tree_view.verticalScrollBar().value() == 10


@pytest.mark.parametrize(
    "table,test_data",
    [
        ("hourly", VariableData("BOILER", "Boiler Gas Rate", "W")),
        ("daily", VariableData("BOILER", "Boiler Gas Rate", "W")),
        ("hourly-simple", VariableData("Boiler Gas Rate", None, "W")),
        ("daily-simple", VariableData("Boiler Gas Rate", None, "W")),
    ],
)
def test_on_double_clicked(qtbot, tree_view: TreeView, table, test_data):
    tree_view.set_model(table)

    def variable_data(data):
        return test_data == data

    point = tree_view.visualRect(tree_view.model().index(1, 0)).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    signals = [tree_view.doubleClicked, tree_view.itemDoubleClicked]
    callbacks = [None, variable_data]
    with qtbot.wait_signals(signals, check_params_cbs=callbacks):
        # need to click first as single double click would emit only pressed signal
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)


def test_on_double_clicked_parent(qtbot, tree_view: TreeView):
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
            ),
            VariableData(
                "BLOCK1:ZONEA FAN COIL UNIT COOLING COIL",
                "Cooling Coil Sensible Cooling Rate",
                "W",
            ),
        ]
        return dt == variable_data

    with qtbot.wait_signal(tree_view.selectionPopulated, check_params_cb=test_data):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)


@pytest.mark.parametrize(
    "table,test_data",
    [
        ("hourly", VariableData("BOILER", "Boiler Gas Rate", "W")),
        ("daily", VariableData("BOILER", "Boiler Gas Rate", "W")),
        ("hourly-simple", VariableData("Boiler Gas Rate", None, "W")),
        ("daily-simple", VariableData("Boiler Gas Rate", None, "W")),
    ],
)
def test_on_pressed(qtbot, tree_view: TreeView, table, test_data):
    tree_view.set_model(table)

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


def test_on_pressed_right_mb(qtbot, tree_view: TreeView):
    index = tree_view.model().index(1, 0)
    point = tree_view.visualRect(index).center()
    qtbot.mouseMove(tree_view.viewport(), pos=point)
    with qtbot.assert_not_emitted(tree_view.pressed,):
        qtbot.mousePress(tree_view.viewport(), Qt.RightButton, pos=point)


def test_get_visual_data(tree_view: TreeView):
    assert tree_view.get_visual_column_data() == ("type", "key", "proxy_units", "units")
    tree_view.reorder_columns(("proxy_units", "type", "key", "units"))
    assert tree_view.get_visual_column_data() == ("proxy_units", "type", "key", "units")


def test_get_visual_ixs(tree_view: TreeView):
    assert tree_view.get_visual_column_mapping() == {
        "type": 0,
        "key": 1,
        "proxy_units": 2,
        "units": 3,
    }


def test_set_model(tree_view: TreeView):
    tree_view.set_model("daily")
    assert tree_view.source_model.name == "daily"
    assert tree_view.source_model.energy_units == "J"
    assert tree_view.source_model.power_units == "W"
    assert tree_view.source_model.units_system == "SI"
    assert not tree_view.source_model.rate_to_energy
    assert tree_view.source_model.tree_node == "type"


def test_set_and_update_model(tree_view: TreeView, daily_df: pd.DataFrame):
    units = {
        "energy_units": "J",
        "power_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    tree_view.set_and_update_model(daily_df, "daily", tree_node="key", **units)
    assert tree_view.source_model.name == "daily"
    assert tree_view.source_model.energy_units == "J"
    assert tree_view.source_model.power_units == "MW"
    assert tree_view.source_model.units_system == "IP"
    assert tree_view.source_model.rate_to_energy
    assert tree_view.source_model.tree_node == "key"


def test_update_model(tree_view: TreeView, hourly_df: pd.DataFrame):
    units = {
        "energy_units": "J",
        "power_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    tree_view.update_model(hourly_df, tree_node="key", **units)
    assert tree_view.source_model.name == "hourly"
    assert tree_view.source_model.energy_units == "J"
    assert tree_view.source_model.power_units == "MW"
    assert tree_view.source_model.units_system == "IP"
    assert tree_view.source_model.rate_to_energy
    assert tree_view.source_model.tree_node == "key"


def test_update_units(tree_view: TreeView, hourly_df: pd.DataFrame):
    units = {
        "energy_units": "J",
        "power_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    tree_view.update_units(hourly_df[UNITS_LEVEL], **units)
    assert tree_view.source_model.name == "hourly"
    assert tree_view.source_model.energy_units == "J"
    assert tree_view.source_model.power_units == "MW"
    assert tree_view.source_model.units_system == "IP"
    assert tree_view.source_model.rate_to_energy
    assert tree_view.source_model.tree_node == "type"


def test_update_units_proxy_tree_node(tree_view: TreeView, hourly_df: pd.DataFrame):
    units = {
        "energy_units": "J",
        "power_units": "MW",
        "rate_to_energy": True,
        "units_system": "IP",
    }
    tree_view.update_model(hourly_df, tree_node="units")
    tree_view.update_units(hourly_df[UNITS_LEVEL], **units)
    assert tree_view.source_model.name == "hourly"
    assert tree_view.source_model.energy_units == "J"
    assert tree_view.source_model.power_units == "MW"
    assert tree_view.source_model.units_system == "IP"
    assert tree_view.source_model.rate_to_energy
    assert tree_view.source_model.tree_node == "units"


def test_update_view_model_appearance(qtbot, tree_view: TreeView, daily_df: pd.DataFrame):
    header = ("type", "proxy_units", "key", "units")
    tree_view.set_and_update_model(daily_df, "daily", tree_node="type")

    widths = {"interactive": 150, "fixed": 50}
    expanded = {"Fan Electric Power", "Heating Coil Heating Rate"}
    tree_view.update_appearance(header=header, widths=widths, expanded=expanded)
    assert tree_view.header().sectionSize(tree_view.header().logicalIndex(0)) == 150
    assert tree_view.header().sectionSize(tree_view.header().logicalIndex(1)) == 50
    assert tree_view.header().sectionSize(tree_view.header().logicalIndex(2)) == 150
    assert tree_view.header().sectionSize(tree_view.header().logicalIndex(3)) == 50

    assert tree_view.get_visual_column_data() == header

    assert tree_view.isExpanded(tree_view.model().index(11, 0))
    assert tree_view.isExpanded(tree_view.model().index(13, 0))


def test_scroll_to(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    v = VariableData("BLOCK1:ZONEA", "Zone Infiltration Air Change Rate", "ach")
    with qtbot.wait_signal(tree_view.verticalScrollBar().valueChanged):
        tree_view.scroll_to(v)
    assert tree_view.verticalScrollBar().value() == 29


@pytest.mark.parametrize(
    "table,test_data",
    [
        (
            "hourly",
            [
                VariableData("BOILER", "Boiler Gas Rate", "W"),
                VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
            ],
        ),
        (
            "hourly-simple",
            [
                VariableData("Boiler Gas Rate", None, "W"),
                VariableData("Boiler Ancillary Electric Power", None, "W"),
            ],
        ),
    ],
)
def test_deselect_variables(qtbot, tree_view: TreeView, table, test_data):
    tree_view.set_model(table)
    tree_view.select_variables(test_data)
    with qtbot.wait_signal(tree_view.selectionCleared):
        tree_view.deselect_all_variables()
    assert not tree_view.selectionModel().selectedRows()


@pytest.mark.parametrize(
    "table,test_data",
    [
        (
            "hourly",
            [
                VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
                VariableData("BOILER", "Boiler Gas Rate", "W"),
            ],
        ),
        (
            "hourly-simple",
            [
                VariableData("Boiler Ancillary Electric Power", None, "W"),
                VariableData("Boiler Gas Rate", None, "W"),
            ],
        ),
    ],
)
def test_select_variables(qtbot, tree_view: TreeView, table, test_data):
    tree_view.set_model(table)

    def cb(variable_data):
        return set(test_data) == set(variable_data)

    with qtbot.wait_signal(tree_view.selectionPopulated, check_params_cb=cb):
        tree_view.select_variables(test_data)


def test_on_collapsed(qtbot, tree_view: TreeView, hourly_df: pd.DataFrame):
    index = tree_view.model().index(7, 0)
    tree_view.expand(index)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)

    def test_collapsed(expected_index):
        assert tree_view.source_model.expanded == set()
        return index == expected_index

    with qtbot.wait_signal(tree_view.collapsed, check_params_cb=test_collapsed):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert not tree_view.isExpanded(index)


def test_on_expanded(qtbot, tree_view: TreeView, eso_file: EsoFile):
    index = tree_view.model().index(7, 0)
    point = tree_view.visualRect(index).center()
    # need to move mouse to hover over view
    qtbot.mouseMove(tree_view.viewport(), pos=point)

    def test_expanded(expected_index):
        assert tree_view.source_model.expanded == {"Cooling Coil Sensible Cooling Rate"}
        return index == expected_index

    with qtbot.wait_signal(tree_view.expanded, check_params_cb=test_expanded):
        qtbot.mouseClick(tree_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(tree_view.viewport(), Qt.LeftButton, pos=point)

    assert tree_view.isExpanded(index)


def test_filter_view(qtbot, tree_view: TreeView, daily_df: pd.DataFrame):
    tree_view.set_and_update_model(daily_df, "daily", tree_node="type")
    tree_view.filter_view(FilterTuple(key="block1:zonea", type="temperature", proxy_units=""))

    assert tree_view.model().rowCount() == 3
    assert tree_view.model().sourceModel().rowCount() == 49

    index0 = tree_view.model().index(0, 0)
    index1 = tree_view.model().index(1, 0)
    index2 = tree_view.model().index(2, 0)

    assert tree_view.isExpanded(index0)
    assert tree_view.isExpanded(index1)
    assert tree_view.isExpanded(index2)

    vd0 = VariableData("BLOCK1:ZONEA", "Zone Mean Air Temperature", "C")
    vd1 = VariableData("BLOCK1:ZONEA", "Zone Mean Radiant Temperature", "C")
    vd2 = VariableData("BLOCK1:ZONEA", "Zone Operative Temperature", "C")

    parent0 = tree_view.proxy_model.mapToSource(index0)
    parent1 = tree_view.proxy_model.mapToSource(index1)
    parent2 = tree_view.proxy_model.mapToSource(index2)

    row0 = tree_view.proxy_model.mapToSource(index0.child(0, 0)).row()
    row1 = tree_view.proxy_model.mapToSource(index1.child(0, 0)).row()
    row2 = tree_view.proxy_model.mapToSource(index2.child(0, 0)).row()

    assert tree_view.source_model.get_row_variable_data(row0, parent0) == vd0
    assert tree_view.source_model.get_row_variable_data(row1, parent1) == vd1
    assert tree_view.source_model.get_row_variable_data(row2, parent2) == vd2

    child_index_invalid = tree_view.model().index(1, 0, index0)
    assert child_index_invalid == QModelIndex()
