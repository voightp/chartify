from typing import Optional
from unittest.mock import patch

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


class TestRemoveVariable:
    VARIABLES = [
        VariableData("HW LOOP SUPPLY PUMP", "Pump Electric Power", "W"),
        VariableData("CHW LOOP SUPPLY PUMP", "Pump Electric Power", "W"),
    ]

    def test_confirm_remove_variables(self, qtbot, eso_file_mw):
        eso_file_mw.current_view.select_variables(self.VARIABLES)
        with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = True
            qtbot.mouseClick(eso_file_mw.toolbar.remove_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                eso_file_mw,
                "Delete following variables from table 'hourly', file 'eplusout1': ",
                det_text="HW LOOP SUPPLY PUMP | Pump Electric Power | W\nCHW LOOP SUPPLY PUMP | Pump Electric Power | W",
            )

    @pytest.mark.depends(on="test_confirm_remove_variables")
    def test_remove_variable_ui(self, qtbot, eso_file_mw):
        eso_file_mw.current_view.select_variables(self.VARIABLES)
        assert not eso_file_mw.current_view.get_selected_variable_data()

    @pytest.mark.depends(on="test_confirm_remove_variables")
    def test_remove_variable_file(self, qtbot, eso_file_mw):
        df = eso_file_mw.current_model.get_results(self.VARIABLES, **Settings.get_units())
        assert df is None


class TestRenameVariable:
    NEW_SIMPLE_VARIABLE = VariableData("foo", None, "J")
    NEW_VARIABLE = VariableData("foo", "bar", "%")

    def test_confirm_rename_variable_simple(self, qtbot, excel_file_mw):
        excel_file_mw.on_table_change_requested("daily")
        with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            point = excel_file_mw.current_view.visualRect(
                excel_file_mw.current_view.model().index(1, 0)
            ).center()
            qtbot.mouseMove(excel_file_mw.current_view.viewport(), pos=point)
            qtbot.mouseClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
            dialog.assert_called_once_with(
                excel_file_mw,
                title="Rename variable for table 'daily', file 'test_excel_results':",
                input1_name="Key",
                input1_text="BLOCK1:ZONE1",
                input1_blocker={"Environment", "BLOCK2:ZONE1", "BLOCK3:ZONE1"},
            )

    @pytest.mark.depends(on="test_confirm_rename_variable_simple")
    def test_rename_variable_ui_simple(self, qtbot, excel_file_mw):
        excel_file_mw.current_view.select_variables([self.NEW_SIMPLE_VARIABLE])
        assert excel_file_mw.current_view.get_selected_variable_data() == [
            self.NEW_SIMPLE_VARIABLE
        ]

    @pytest.mark.depends(on="test_confirm_rename_variable_simple")
    def test_rename_variable_file_simple(self, qtbot, excel_file_mw):
        df = excel_file_mw.current_model.get_results(
            [self.NEW_SIMPLE_VARIABLE], **Settings.get_units()
        )
        assert df.shape == (365, 1)

    def test_confirm_rename_variable(self, qtbot, excel_file_mw):
        excel_file_mw.on_table_change_requested("hourly")
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            instance.input2_text = "bar"
            point = excel_file_mw.current_view.visualRect(
                excel_file_mw.current_view.model().index(1, 0)
            ).center()
            # need to move mouse to hover over view
            qtbot.mouseMove(excel_file_mw.current_view.viewport(), pos=point)
            qtbot.mouseClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(excel_file_mw.current_view.viewport(), Qt.LeftButton, pos=point)
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

        @pytest.mark.depends(on="test_confirm_rename_variable_simple")
        def test_rename_variable_ui(self, qtbot, eso_file_mw):
            eso_file_mw.current_view.select_variables([self.NEW_VARIABLE])
            assert eso_file_mw.current_view.get_selected_variable_data() == [self.NEW_VARIABLE]

        @pytest.mark.depends(on="test_confirm_rename_variable_simple")
        def test_rename_variable_file(self, qtbot, eso_file_mw):
            df = eso_file_mw.current_model.get_results(
                [self.NEW_VARIABLE], **Settings.get_units()
            )
            assert df.shape == (4392, 1)


class TestAggregate:
    @pytest.mark.parametrize(
        "variables, text1, text2",
        [
            (
                [
                    VariableData("BOILER", "Boiler Ancillary Electric Power", "W"),
                    VariableData("BOILER", "Boiler Gas Rate", "W"),
                ],
                "BOILER - mean",
                "Custom Type",
            ),
            (
                [
                    VariableData("BLOCK1:ZONEA", "Lights Total Heating Rate", "W"),
                    VariableData("BLOCK1:ZONEB", "Lights Total Heating Rate", "W"),
                ],
                "Custom Key - mean",
                "Lights Total Heating Rate",
            ),
        ],
    )
    def test_confirm_aggregate_variables(self, qtbot, eso_file_mw, variables, text1, text2):
        eso_file_mw.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            instance.input2_text = "bar"
            qtbot.mouseClick(eso_file_mw.toolbar.mean_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                eso_file_mw,
                title=f"Calculate mean from selected "
                f"variables for {eso_file_mw.get_files_and_tables_text()}:",
                input1_name="Key",
                input1_text=text1,
                input2_name="Type",
                input2_text=text2,
            )

    @pytest.mark.depends(on="test_confirm_aggregate_variables")
    def test_aggregate_variables(self, qtbot, eso_file_mw):
        variables = [VariableData("foo", "bar", "W"), VariableData("foo (1)", "bar", "W")]
        eso_file_mw.current_view.select_variables(variables)
        df = eso_file_mw.fetch_results()
        assert df.shape == (4392, 2)


class TestAggregateSimple:
    @pytest.mark.parametrize(
        "variables, text",
        [
            (
                [
                    VariableData("BLOCK2:ZONE1", None, ""),
                    VariableData("BLOCK3:ZONE1", None, ""),
                ],
                "Custom Key - sum",
            ),
            (
                [
                    VariableData("BLOCK1:ZONE1", None, "J"),
                    VariableData("BLOCK1:ZONE1", None, "W"),
                ],
                "BLOCK1:ZONE1 - sum",
            ),
        ],
    )
    def test_confirm_aggregate_variables_simple(self, qtbot, excel_file_mw, variables, text):
        excel_file_mw.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            qtbot.mouseClick(excel_file_mw.toolbar.sum_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                excel_file_mw,
                title=f"Calculate sum from selected "
                f"variables for {excel_file_mw.get_files_and_tables_text()}:",
                input1_name="Key",
                input1_text=text,
            )

    @pytest.mark.depends(on="test_confirm_aggregate_variables_simple")
    def test_aggregate_variables_simple(self, qtbot, excel_file_mw):
        variables = [VariableData("foo", None, "J"), VariableData("foo", None, "")]
        excel_file_mw.current_view.select_variables(variables)
        df = excel_file_mw.fetch_results()
        assert df.shape == (365, 2)
