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
    SIMPLE_VARIABLES = [
        VariableData("Boiler Gas Rate", None, "W"),
        VariableData("Gas:Facility", None, "J"),
    ]

    def test_confirm_remove_variables(self, qtbot, mw_esofile):
        mw_esofile.current_view.select_variables(self.VARIABLES)
        with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = True
            qtbot.mouseClick(mw_esofile.toolbar.remove_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_esofile,
                "Delete following variables from table 'hourly', file 'eplusout1': ",
                det_text="HW LOOP SUPPLY PUMP | Pump Electric Power | W\nCHW LOOP SUPPLY PUMP | Pump Electric Power | W",
            )

    @pytest.mark.depends(on="test_confirm_remove_variables")
    def test_remove_variable(self, qtbot, mw_esofile):
        exist = mw_esofile.current_view.source_model.variables_exist(self.VARIABLES)
        assert not any(exist)
        assert not mw_esofile.current_view.get_selected_variable_data()

    def test_confirm_remove_variables_simple(self, qtbot, mw_combined_file):
        mw_combined_file.current_view.select_variables(self.SIMPLE_VARIABLES)
        with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = True
            qtbot.mouseClick(mw_combined_file.toolbar.remove_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_combined_file,
                "Delete following variables from table 'hourly-simple', file 'eplusout': ",
                det_text="Boiler Gas Rate | W\nGas:Facility | J",
            )

    @pytest.mark.depends(on="test_confirm_remove_variables")
    def test_remove_variable_simple(self, qtbot, mw_combined_file):
        exist = mw_combined_file.current_view.source_model.variables_exist(
            self.SIMPLE_VARIABLES
        )
        assert not any(exist)
        assert not mw_combined_file.current_view.get_selected_variable_data()


class TestRenameVariable:
    NEW_SIMPLE_VARIABLE = VariableData("foo", None, "J")
    NEW_VARIABLE = VariableData("foo", "bar", "%")

    def test_confirm_rename_variable_simple(self, qtbot, mw_excel_file):
        mw_excel_file.on_table_change_requested("daily")
        with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            point = mw_excel_file.current_view.visualRect(
                mw_excel_file.current_view.model().index(1, 0)
            ).center()
            qtbot.mouseMove(mw_excel_file.current_view.viewport(), pos=point)
            qtbot.mouseClick(mw_excel_file.current_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(mw_excel_file.current_view.viewport(), Qt.LeftButton, pos=point)
            dialog.assert_called_once_with(
                mw_excel_file,
                title="Rename variable for table 'daily', file 'various_table_types':",
                input1_name="Key",
                input1_text="BLOCK1:ZONE1",
                input1_blocker={"Environment", "BLOCK2:ZONE1", "BLOCK3:ZONE1"},
            )

    @pytest.mark.depends(on="test_confirm_rename_variable_simple")
    def test_rename_simple_variable(self, qtbot, mw_excel_file):
        mw_excel_file.current_view.select_variables([self.NEW_SIMPLE_VARIABLE])
        assert mw_excel_file.current_view.get_selected_variable_data() == [
            self.NEW_SIMPLE_VARIABLE
        ]
        assert mw_excel_file.current_model.variable_exists(self.NEW_SIMPLE_VARIABLE)

    @pytest.mark.depends(on="test_confirm_rename_variable_simple")
    def test_rename_simple_variable_file(self, qtbot, mw_excel_file):
        df = mw_excel_file.current_model.get_results(
            [self.NEW_SIMPLE_VARIABLE], **Settings.get_units()
        )
        assert df.shape == (365, 1)

    def test_confirm_rename_variable(self, qtbot, mw_excel_file):
        mw_excel_file.on_table_change_requested("hourly")
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            instance.input2_text = "bar"
            point = mw_excel_file.current_view.visualRect(
                mw_excel_file.current_view.model().index(1, 0)
            ).center()
            # need to move mouse to hover over view
            qtbot.mouseMove(mw_excel_file.current_view.viewport(), pos=point)
            qtbot.mouseClick(mw_excel_file.current_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(mw_excel_file.current_view.viewport(), Qt.LeftButton, pos=point)
            dialog.assert_called_once_with(
                mw_excel_file,
                title="Rename variable for table 'hourly', file 'various_table_types':",
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
        def test_rename_variable_ui(self, qtbot, mw_esofile):
            assert mw_esofile.current_model.variable_exists(self.NEW_SIMPLE_VARIABLE)

        @pytest.mark.depends(on="test_confirm_rename_variable_simple")
        def test_rename_variable_file(self, qtbot, mw_esofile):
            df = mw_esofile.current_model.get_results(
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
    def test_confirm_aggregate_variables(self, qtbot, mw_esofile, variables, text1, text2):
        mw_esofile.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            instance.input2_text = "bar"
            qtbot.mouseClick(mw_esofile.toolbar.mean_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_esofile,
                title=f"Calculate mean from selected "
                f"variables for {mw_esofile.get_files_and_tables_text()}:",
                input1_name="Key",
                input1_text=text1,
                input2_name="Type",
                input2_text=text2,
            )

    @pytest.mark.depends(on="test_confirm_aggregate_variables")
    def test_aggregate_variables(self, qtbot, mw_esofile):
        variables = [VariableData("foo", "bar", "W"), VariableData("foo (1)", "bar", "W")]
        mw_esofile.current_view.select_variables(variables)
        df = mw_esofile.fetch_results()
        assert df.shape == (4392, 2)
        assert mw_esofile.current_model.variables_exist(variables)


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
    def test_confirm_aggregate_variables_simple(self, qtbot, mw_excel_file, variables, text):
        mw_excel_file.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            qtbot.mouseClick(mw_excel_file.toolbar.sum_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_excel_file,
                title=f"Calculate sum from selected "
                f"variables for {mw_excel_file.get_files_and_tables_text()}:",
                input1_name="Key",
                input1_text=text,
            )

    @pytest.mark.depends(on="test_confirm_aggregate_variables_simple")
    def test_aggregate_variables_simple(self, qtbot, mw_excel_file):
        variables = [VariableData("foo", None, "J"), VariableData("foo", None, "")]
        mw_excel_file.current_view.select_variables(variables)
        df = mw_excel_file.fetch_results()
        assert df.shape == (365, 2)
        assert mw_excel_file.current_model.variables_exist(variables)


class TestAllFilesTables:
    VARIABLES = [
        VariableData("HW LOOP SUPPLY PUMP", "Pump Electric Power", "W"),
        VariableData("CHW LOOP SUPPLY PUMP", "Pump Electric Power", "W"),
    ]
    SIMPLE_VARIABLES = [
        VariableData("Boiler Gas Rate", None, "W"),
        VariableData("Gas:Facility", None, "J"),
    ]

    def test_confirm_remove_variables(self, qtbot, mw_esofile):
        mw_esofile.toolbar.all_files_toggle.setChecked(True)
        mw_esofile.toolbar.all_tables_toggle.setChecked(True)
        mw_esofile.current_view.select_variables(self.VARIABLES)
        with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = True
            qtbot.mouseClick(mw_esofile.toolbar.remove_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_esofile,
                f"Delete following variables from {mw_esofile.get_files_and_tables_text()}: ",
                det_text="HW LOOP SUPPLY PUMP | Pump Electric Power | W\nCHW LOOP SUPPLY PUMP | Pump Electric Power | W",
            )

    @pytest.mark.depends(on="test_confirm_remove_variables")
    def test_remove_variable(self, qtbot, mw_combined_file):
        models = mw_combined_file.get_all_models()
        for model in models:
            assert not any(model.variables_exist(self.VARIABLES))
