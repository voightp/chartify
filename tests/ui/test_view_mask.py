from copy import deepcopy

from chartify.ui.treeview import ViewMask
from chartify.utils.utils import VariableData
from tests.conftest import *

VARIABLES = [
    VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
    VariableData("BOILER", "Boiler Gas Rate", "W"),
]

SIMPLE_VARIABLES = [
    VariableData("Boiler Gas Rate", None, "W"),
    VariableData("Boiler Ancillary Electric Power", None, "W"),
]


@pytest.fixture(autouse=True)
def reset_cached():
    cached = deepcopy(ViewMask._cached)
    yield
    ViewMask._cached = cached


@pytest.fixture
def modified_treeview(qtbot, mw_combined_file):
    mw_combined_file.on_table_change_requested("hourly")
    mw_combined_file.current_view.reorder_columns(("key", "type", "proxy_units", "units"))
    mw_combined_file.current_view.expandAll()
    mw_combined_file.current_view.select_variables(VARIABLES)
    mw_combined_file.current_view.update_scrollbar_position(10)
    mw_combined_file.current_view.header().resizeSection(0, 150)
    mw_combined_file.on_table_change_requested("daily")
    return mw_combined_file.current_view


@pytest.fixture
def modified_view(qtbot, mw_combined_file):
    mw_combined_file.on_table_change_requested("hourly")
    mw_combined_file.tree_act.setChecked(False)
    mw_combined_file.current_view.reorder_columns(("key", "type", "proxy_units", "units"))
    mw_combined_file.current_view.select_variables(VARIABLES)
    mw_combined_file.current_view.header().resizeSection(1, 180)
    mw_combined_file.current_view.update_scrollbar_position(8)
    mw_combined_file.on_table_change_requested("daily")
    return mw_combined_file.current_view


@pytest.fixture
def modified_simpleview(mw_combined_file):
    mw_combined_file.current_view.reorder_columns(("proxy_units", "units", "key"))
    mw_combined_file.current_view.select_variables(SIMPLE_VARIABLES)
    mw_combined_file.current_view.update_scrollbar_position(5)
    mw_combined_file.on_table_change_requested("daily-simple")
    return mw_combined_file.current_view


@pytest.fixture
def initial_treeview(qtbot, mw_combined_file):
    mw_combined_file.on_table_change_requested("hourly")
    return mw_combined_file.current_view


@pytest.fixture
def initial_simpleview(qtbot, mw_combined_file):
    return mw_combined_file.current_view


@pytest.mark.parametrize(
    "view, header",
    [
        (pytest.lazy_fixture("modified_treeview"), ("key", "type", "proxy_units", "units"),),
        (pytest.lazy_fixture("modified_view"), ("key", "type", "proxy_units", "units"),),
        (pytest.lazy_fixture("modified_simpleview"), ("proxy_units", "units", "key"),),
        (pytest.lazy_fixture("initial_treeview"), ("type", "key", "proxy_units", "units"),),
        (pytest.lazy_fixture("initial_simpleview"), ("key", "proxy_units", "units"),),
    ],
)
def test_header(qtbot, view, header):
    assert header == view.get_visual_column_data()


@pytest.mark.parametrize(
    "view, widths",
    [
        (pytest.lazy_fixture("modified_treeview"), {"fixed": 60, "interactive": 150},),
        (pytest.lazy_fixture("modified_view"), {"fixed": 60, "interactive": 180},),
        (pytest.lazy_fixture("modified_simpleview"), {"fixed": 60,},),
        (pytest.lazy_fixture("initial_treeview"), {"fixed": 60, "interactive": 200},),
        (pytest.lazy_fixture("initial_simpleview"), {"fixed": 60,},),
    ],
)
def test_widths(qtbot, view, widths):
    assert widths == view.get_widths()


@pytest.mark.parametrize(
    "view, selected",
    [
        (pytest.lazy_fixture("modified_treeview"), VARIABLES,),
        (pytest.lazy_fixture("modified_view"), VARIABLES,),
        (pytest.lazy_fixture("modified_simpleview"), SIMPLE_VARIABLES,),
        (pytest.lazy_fixture("initial_treeview"), [],),
        (pytest.lazy_fixture("initial_simpleview"), [],),
    ],
)
def test_selected(qtbot, view, selected):
    assert set(selected) == set(view.get_selected_variable_data())


@pytest.mark.parametrize(
    "view, pos",
    [
        (pytest.lazy_fixture("modified_treeview"), 10,),
        (pytest.lazy_fixture("modified_view"), 8,),
        (pytest.lazy_fixture("modified_simpleview"), 5,),
        (pytest.lazy_fixture("initial_treeview"), 0,),
        (pytest.lazy_fixture("initial_simpleview"), 0,),
    ],
)
def test_scroll_position(qtbot, view, pos):
    assert pos == view.source_model.scroll_position


@pytest.mark.parametrize(
    "view, expanded",
    [
        (
            pytest.lazy_fixture("modified_treeview"),
            {
                "BLOCK1:ZONEA",
                "BLOCK1:ZONEA FAN COIL UNIT COOLING COIL",
                "BLOCK1:ZONEB",
                "BLOCK1:ZONEB FAN COIL UNIT COOLING COIL",
                "BOILER",
                "CHILLER",
                "Environment",
                "Meter",
            },
        ),
        (pytest.lazy_fixture("modified_view"), set(),),
        (pytest.lazy_fixture("modified_simpleview"), set(),),
        (pytest.lazy_fixture("initial_treeview"), set(),),
        (pytest.lazy_fixture("initial_simpleview"), set(),),
    ],
)
def test_expanded(qtbot, view, expanded):
    assert expanded == view.source_model.expanded


@pytest.mark.parametrize(
    "view, tree_node",
    [
        (pytest.lazy_fixture("modified_treeview"), "key",),
        (pytest.lazy_fixture("modified_view"), None,),
        (pytest.lazy_fixture("modified_simpleview"), None,),
        (pytest.lazy_fixture("initial_treeview"), "type",),
        (pytest.lazy_fixture("initial_simpleview"), None,),
    ],
)
def test_tree_node(qtbot, view, tree_node):
    assert tree_node == view.source_model.tree_node
