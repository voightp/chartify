from typing import List, Optional, Set, Tuple
from unittest.mock import patch, MagicMock

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QAction
from esofile_reader import Variable, SimpleVariable, EsoFile

from chartify.utils.utils import FilterTuple, VariableData
from tests.conftest import *


@pytest.mark.parametrize(
    "similar,old_pos, current_pos,expected_pos,ref_expanded,current_expanded,expected_expanded",
    [
        (True, 123, 321, 123, {"A", "B"}, {"C", "D"}, {"A", "B"}),
        (False, 123, 321, 321, {"A", "B"}, {"C", "D"}, {"C", "D"}),
    ],
)
def test_update_view_visual(
    mw,
    similar: bool,
    old_pos: int,
    current_pos: int,
    expected_pos: int,
    ref_expanded: Set[str],
    current_expanded: Set[str],
    expected_expanded: Set[str],
):
    old_model = MagicMock()
    old_model.is_similar.return_value = similar
    old_model.scroll_position = old_pos
    old_model.expanded = ref_expanded
    with patch("chartify.ui.main_window.MainWindow.current_view") as current_view:
        current_view.source_model.scroll_position = current_pos
        current_view.source_model.expanded = current_expanded
        current_view.view_type = "tree"
        var = VariableData("Temperature", "Zone A", "C")
        mw.update_view_visual(
            selected=[var], scroll_to=var, old_model=old_model, hide_source_units=False
        )
        current_view.update_appearance.assert_called_with(
            widths={"fixed": 60, "interactive": 200},
            header=["type", "key", "proxy_units", "units"],
            filter_tuple=FilterTuple(key="", type="", proxy_units=""),
            expanded=expected_expanded,
            selected=[var],
            scroll_pos=expected_pos,
            scroll_to=var,
            hide_source_units=False,
        )
