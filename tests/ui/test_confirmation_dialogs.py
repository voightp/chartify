from typing import List, Optional, Tuple
from unittest.mock import patch

from esofile_reader import Variable

from chartify.utils.utils import VariableData
from tests.fixtures import *


@pytest.mark.parametrize("confirmed,expected", [(0, None), (1, "test")])
def test_confirm_rename_file(mw, confirmed: int, expected: Optional[str]):
    with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "test"
        out = mw.confirm_rename_file("test", ["foo", "bar"])
        dialog.assert_called_once_with(
            mw,
            title="Enter a new file name.",
            input1_name="Name",
            input1_text="test",
            input1_blocker=["foo", "bar"],
        )
        assert out == expected


def test_confirm_remove_variables(qtbot, eso_file_mw):
    variables = [
        VariableData("BOILER", "Boiler Gas Rate", "W"),
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
    ]
    eso_file_mw.current_view.select_variables(variables)
    with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = True
        qtbot.mouseClick(eso_file_mw.toolbar.remove_btn, Qt.LeftButton)
        dialog.assert_called_once_with(
            eso_file_mw,
            "Delete following variables from table 'hourly', file 'eplusout1': ",
            det_text="BOILER | Boiler Ancillary Electric Power | W\nBOILER | Boiler Gas Rate | W",
        )


def test_confirm_rename_variable_simple_variable(qtbot, excel_file_mw):
    excel_file_mw.on_table_change_requested()
    with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
        point = excel_file_mw.current_view.visualRect(
            excel_file_mw.current_view.model().index(1, 0)
        ).center()
        # need to move mouse to hover over view
        qtbot.mouseMove(excel_file_mw.current_view.viewport(), pos=point)
        qtbot.mouseClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
        instance = dialog.return_value
        instance.exec_.return_value = True
        dialog.assert_called_once_with(
            excel_file_mw,
            title="Rename variable for table 'daily', file 'test_excel_results':",
            input1_name="Key",
            input1_text="BLOCK1:ZONE1",
            input1_blocker={"Environment", "BLOCK4:ZONE1", "BLOCK2:ZONE1", "BLOCK3:ZONE1"},
        )


def test_confirm_rename_variable(qtbot, excel_file_mw):
    excel_file_mw.on_table_change_requested("hourly")
    with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
        point = excel_file_mw.current_view.visualRect(
            excel_file_mw.current_view.model().index(1, 0)
        ).center()
        # need to move mouse to hover over view
        qtbot.mouseMove(excel_file_mw.current_view.viewport(), pos=point)
        qtbot.mouseClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
        qtbot.mouseDClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
        instance = dialog.return_value
        instance.exec_.return_value = True
        dialog.assert_called_once_with(
            excel_file_mw,
            title="Rename variable for table 'hourly', file 'test_excel_results':",
            input1_name="Key",
            input1_text="BLOCK1:ZONE1",
            input1_blocker={"Environment", "BLOCK4:ZONE1", "BLOCK2:ZONE1", "BLOCK3:ZONE1"},
            input2_name="Type",
            input2_text="Zone Mean Air Humidity Ratio",
            input2_blocker={
                "Site Diffuse Solar Radiation Rate per Area",
                "Zone People Occupant Count",
                "Zone Mean Air Temperature",
            },
        )


@pytest.mark.parametrize("variables, key", [
    ([
        VariableData("BOILER", "Boiler Gas Rate", "W"),
        VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
    ])
])
def test_confirm_aggregate_variables_simple_variables(qtbot, excel_file_mw, variables, key):
    variables =
    qtbot.stop()
    excel_file_mw.current_view.select_variables(variables)
    with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = True
        qtbot.mouseClick(excel_file_mw.toolbar.sum_btn, Qt.LeftButton)
        dialog.assert_called_once_with(
            eso_file_mw,
            "Delete following variables from table 'hourly', file 'eplusout1': ",
            det_text="BOILER | Boiler Ancillary Electric Power | W\nBOILER | Boiler Gas Rate | W",
        )


def test_confirm_aggregate_variables(
    mw,
    confirmed: int,
    expected: Optional[Tuple[str, None]],
    variables: List[Variable],
    key: str,
    type_: str,
):
    with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "New KEY"
        instance.input2_text = "New TYPE"
        out = mw.confirm_aggregate_variables(variables, "sum")
        dialog.assert_called_once_with(
            mw,
            title="Enter details of the new variable:",
            input1_name="Key",
            input1_text=key,
            input2_name="Type",
            input2_text=type_,
        )
        assert out == expected


@pytest.mark.parametrize("confirmed,expected", [(0, False), (1, True)])
def test_confirm_delete_file(mw, confirmed: int, expected: bool):
    with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        out = mw.confirm_delete_file("FOO")
        assert out is expected
