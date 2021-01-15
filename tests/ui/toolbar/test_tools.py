from unittest.mock import patch

import pytest
from PySide2.QtCore import Qt

from chartify.ui.treeview_model import VV


@pytest.fixture(scope="function")
def mw_esofile1(mw_esofile, qtbot):
    mw_esofile.standard_tab_wgt.setCurrentIndex(1)
    qtbot.mouseClick(mw_esofile.toolbar.get_table_button_by_name("hourly"), Qt.LeftButton)
    return mw_esofile


class TestRemoveVariable:
    VARIABLES = [
        VV("HW LOOP SUPPLY PUMP", "Pump Electric Power", "W"),
        VV("CHW LOOP SUPPLY PUMP", "Pump Electric Power", "W"),
    ]
    SIMPLE_VARIABLES = [
        VV("Boiler Gas Rate", None, "W"),
        VV("Gas:Facility", None, "J"),
    ]

    def test_confirm_remove_variables(self, qtbot, mw_esofile1):
        mw_esofile1.current_view.select_variables(self.VARIABLES)
        with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = True
            qtbot.mouseClick(mw_esofile1.toolbar.remove_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_esofile1,
                "Delete following variables from table 'hourly', file 'eplusout1': ",
                det_text="HW LOOP SUPPLY PUMP | Pump Electric Power | W\nCHW LOOP SUPPLY PUMP | Pump Electric Power | W",
            )

    @pytest.mark.depends(on="test_confirm_remove_variables")
    def test_remove_variable(self, qtbot, mw_esofile1):
        exist = mw_esofile1.current_view.source_model.variables_exist(self.VARIABLES)
        assert not any(exist)
        assert not mw_esofile1.current_view.get_selected_view_variable()

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

    @pytest.mark.depends(on="test_confirm_remove_variables_simple")
    def test_remove_variable_simple(self, qtbot, mw_combined_file):
        exist = mw_combined_file.current_view.source_model.variables_exist(
            self.SIMPLE_VARIABLES
        )
        assert not any(exist)
        assert not mw_combined_file.current_view.get_selected_view_variable()


class TestRenameSimpleVariable:
    NEW_SIMPLE_VARIABLE = VV("foo", None, "J")

    def test_confirm_rename_variable_simple(self, qtbot, mw_excel_file):
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
        assert mw_excel_file.current_view.get_selected_view_variable() == [
            self.NEW_SIMPLE_VARIABLE
        ]
        assert mw_excel_file.current_model.variable_exists(self.NEW_SIMPLE_VARIABLE)

    @pytest.mark.depends(on="test_confirm_rename_variable_simple")
    def test_rename_simple_variable_file(self, qtbot, mw_excel_file):
        df = mw_excel_file.current_model.get_results(
            [self.NEW_SIMPLE_VARIABLE], **mw_excel_file.toolbar.current_units
        )
        assert df.shape == (365, 1)


class TestRenameVariable:
    NEW_VARIABLE = VV("foo", "bar", "kgWater/kgDryAir")

    @pytest.fixture(autouse=True)
    def mw_excel_file_hourly(self, mw_excel_file, qtbot):
        qtbot.mouseClick(
            mw_excel_file.toolbar.get_table_button_by_name("hourly"), Qt.LeftButton
        )
        return mw_excel_file

    def test_confirm_rename_variable(self, qtbot, mw_excel_file_hourly):
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            instance.input2_text = "bar"
            point = mw_excel_file_hourly.current_view.visualRect(
                mw_excel_file_hourly.current_view.model().index(1, 0)
            ).center()
            # need to move mouse to hover over view
            qtbot.mouseMove(mw_excel_file_hourly.current_view.viewport(), pos=point)
            qtbot.mouseClick(
                mw_excel_file_hourly.current_view.viewport(), Qt.LeftButton, pos=point
            )
            qtbot.mouseDClick(
                mw_excel_file_hourly.current_view.viewport(), Qt.LeftButton, pos=point
            )
            dialog.assert_called_once_with(
                mw_excel_file_hourly,
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

    @pytest.mark.depends(on="test_confirm_rename_variable")
    def test_rename_variable_ui(self, qtbot, mw_excel_file_hourly):
        assert mw_excel_file_hourly.current_model.variable_exists(self.NEW_VARIABLE)

    @pytest.mark.depends(on="test_confirm_rename_variable")
    def test_rename_variable_file(self, qtbot, mw_excel_file_hourly):
        df = mw_excel_file_hourly.current_model.get_results(
            [self.NEW_VARIABLE], **mw_excel_file_hourly.toolbar.current_units
        )
        assert df.shape == (8760, 1)


class TestAggregate:
    @pytest.mark.parametrize(
        "variables, text1, text2",
        [
            (
                [
                    VV("BOILER", "Boiler Ancillary Electric Power", "W"),
                    VV("BOILER", "Boiler Gas Rate", "W"),
                ],
                "BOILER - mean",
                "Custom Type",
            ),
            (
                [
                    VV("BLOCK1:ZONEA", "Lights Total Heating Rate", "W"),
                    VV("BLOCK1:ZONEB", "Lights Total Heating Rate", "W"),
                ],
                "Custom Key - mean",
                "Lights Total Heating Rate",
            ),
        ],
    )
    def test_confirm_aggregate_variables(self, qtbot, mw_esofile1, variables, text1, text2):
        mw_esofile1.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = "foo"
            instance.input2_text = "bar"
            qtbot.mouseClick(mw_esofile1.toolbar.mean_btn, Qt.LeftButton)
            dialog.assert_called_once_with(
                mw_esofile1,
                title=f"Calculate mean from selected "
                f"variables for {mw_esofile1.get_files_and_tables_text()}:",
                input1_name="Key",
                input1_text=text1,
                input2_name="Type",
                input2_text=text2,
            )

    @pytest.mark.depends(on="test_confirm_aggregate_variables")
    def test_aggregate_variables(self, qtbot, mw_esofile1):
        variables = [VV("foo", "bar", "W"), VV("foo (1)", "bar", "W")]
        mw_esofile1.current_view.select_variables(variables)
        df = mw_esofile1.fetch_results()
        assert df.shape == (4392, 2)
        assert mw_esofile1.current_model.variables_exist(variables)


class TestAggregateSimple:
    @pytest.mark.parametrize(
        "variables, text",
        [
            (
                [VV("BLOCK2:ZONE1", None, ""), VV("BLOCK3:ZONE1", None, ""),],
                "Custom Key - sum",
            ),
            (
                [VV("BLOCK1:ZONE1", None, "J"), VV("BLOCK1:ZONE1", None, "W"),],
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
        variables = [VV("foo", None, "J"), VV("foo", None, "")]
        mw_excel_file.current_view.select_variables(variables)
        df = mw_excel_file.fetch_results()
        assert df.shape == (365, 2)
        assert mw_excel_file.current_model.variables_exist(variables)


class TestAllFilesTables:
    @pytest.fixture
    def mw_esofile_all(self, mw_esofile):
        mw_esofile.toolbar.all_files_toggle.setChecked(True)
        mw_esofile.toolbar.all_tables_toggle.setChecked(True)
        return mw_esofile

    @pytest.fixture
    def mw_esofile1_all(self, mw_esofile):
        mw_esofile.toolbar.all_files_toggle.setChecked(True)
        mw_esofile.toolbar.all_tables_toggle.setChecked(True)
        mw_esofile.standard_tab_wgt.setCurrentIndex(1)
        return mw_esofile

    class TestModels:
        @pytest.mark.parametrize(
            "all_files, all_tables, n_models",
            [(True, True, 14), (False, True, 6), (True, False, 1), (False, False, 1)],
        )
        def test_get_all_models(self, all_files, all_tables, n_models, mw_esofile):
            mw_esofile.toolbar.all_files_toggle.setChecked(all_files)
            mw_esofile.toolbar.all_tables_toggle.setChecked(all_tables)
            assert n_models == len(mw_esofile.get_all_models())

        @pytest.mark.parametrize(
            "table, all_tables, n_models",
            [
                ("hourly-simple", True, 4),
                ("hourly-simple", False, 1),
                ("hourly", True, 5),
                ("hourly", False, 1),
            ],
        )
        def test_get_all_models_filter_applied(
            self, qtbot, table, all_tables, n_models, mw_combined_file
        ):
            mw_combined_file.toolbar.all_tables_toggle.setChecked(all_tables)
            qtbot.mouseClick(
                mw_combined_file.toolbar.get_table_button_by_name(table), Qt.LeftButton
            )
            assert n_models == len(mw_combined_file.get_all_models())

        def test_all_other_models(self, mw_combined_file):
            assert mw_combined_file.current_model not in mw_combined_file.get_all_other_models()

    @pytest.mark.parametrize(
        "all_files, all_tables, expected_text",
        [
            (False, False, "table 'timestep', file 'eplusout_all_intervals'"),
            (True, False, "table 'timestep', all files"),
            (False, True, "all tables, file 'eplusout_all_intervals'"),
            (True, True, "all files and all tables"),
        ],
    )
    def test_get_all_files_and_tables(
        self, mw_esofile_all, all_files, all_tables, expected_text
    ):
        mw_esofile_all.toolbar.all_files_toggle.setChecked(all_files)
        mw_esofile_all.toolbar.all_tables_toggle.setChecked(all_tables)
        assert mw_esofile_all.get_files_and_tables_text() == expected_text

    def test_remove_variables(self, qtbot, mw_esofile1_all):
        variables = [
            VV("BLOCK1:ZONEA", "Zone Mean Air Temperature", "C"),
            VV("BLOCK1:ZONEB", "Zone Mean Air Temperature", "C"),
        ]
        mw_esofile1_all.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = True
            qtbot.mouseClick(mw_esofile1_all.toolbar.remove_btn, Qt.LeftButton)
            for model in mw_esofile1_all.get_all_models():
                assert not any(model.variables_exist(variables))

    def test_aggregate_variables(self, qtbot, mw_esofile1_all):
        variables = [
            VV("BLOCK1:ZONEA", "Zone Mean Radiant Temperature", "C"),
            VV("BLOCK1:ZONEB", "Zone Mean Radiant Temperature", "C"),
        ]
        mw_esofile1_all.current_view.select_variables(variables)
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.input1_text = "aggregated"
            instance.input2_text = "variable"
            instance.exec_.return_value = True
            qtbot.mouseClick(mw_esofile1_all.toolbar.mean_btn, Qt.LeftButton)
            for model in mw_esofile1_all.get_all_models():
                if any(model.variables_exist(variables)):
                    assert model.variable_exists(VV("aggregated", "variable", "C"))

    def test_rename_variable(self, qtbot, mw_esofile1_all):
        variable = VV("BLOCK1:ZONEA", "Zone Operative Temperature", "C")
        new_variable = VV("foo", "bar", "c")
        mw_esofile1_all.current_view.select_variables([variable])
        with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
            instance = dialog.return_value
            instance.exec_.return_value = 1
            instance.input1_text = new_variable.key
            instance.input2_text = new_variable.type
            selection = mw_esofile1_all.current_model.get_matching_selection([variable])
            index = selection.indexes()[0]
            point = mw_esofile1_all.current_view.visualRect(index).center()
            # need to move mouse to hover over view
            qtbot.mouseMove(mw_esofile1_all.current_view.viewport(), pos=point)
            qtbot.mouseClick(mw_esofile1_all.current_view.viewport(), Qt.LeftButton, pos=point)
            qtbot.mouseDClick(mw_esofile1_all.current_view.viewport(), Qt.LeftButton, pos=point)
