from unittest.mock import patch

from esofile_reader import EsoFile

from tests.fixtures import *


def test_empty_current_view(mw):
    assert mw.current_view is None


def test_empty_current_model(mw):
    assert mw.current_model is None


def test_tab_widgets(mw):
    assert mw.tab_widgets == [mw.standard_tab_wgt, mw.totals_tab_wgt, mw.diff_tab_wgt]


@pytest.mark.parametrize(
    "all_files, all_tables, n_models",
    [(True, True, 14), (False, True, 4), (True, False, 2), (False, False, 1)],
)
def test_get_all_models(all_files, all_tables, n_models, eso_file_mw):
    eso_file_mw.toolbar.all_files_toggle.setChecked(all_files)
    eso_file_mw.toolbar.all_tables_toggle.setChecked(all_tables)
    assert n_models == len(eso_file_mw.get_all_models())


def test_all_other_models(mw):
    assert mw.current_model not in mw.get_all_other_models()


def test_save_storage_to_fs(mw):
    with patch("chartify.ui.main_window.QFileDialog") as qdialog:
        with patch("chartify.ui.main_window.Settings") as mock_settings:
            mock_settings.SAVE_PATH = "save/path"
            qdialog.getSaveFileName.return_value = ("some/dummy/path/file.abc", ".abc")
            mw.save_storage_to_fs()
            qdialog.getSaveFileName.assert_called_with(
                parent=mw, caption="Save project", filter="CFS (*.cfs)", dir="save/path"
            )
            path = mw.save_storage_to_fs()
            assert mock_settings.SAVE_PATH == "some\\dummy\\path"
            assert path == Path("some/dummy/path/file.abc")


def test_load_files_from_fs(qtbot, mw):
    def cb(paths):
        return paths == [Path("some/dummy/path/file.abc")]

    with patch("chartify.ui.main_window.QFileDialog") as qdialog:
        with patch("chartify.ui.main_window.Settings.LOAD_PATH") as mock_path:
            with qtbot.wait_signal(mw.fileProcessingRequested, check_params_cb=cb):
                qdialog.getOpenFileNames.return_value = (["some/dummy/path/file.abc"], ".abc")
                mock_path = Path("load/path")
                mw.load_files_from_fs()
                qdialog.getOpenFileNames.assert_called_with(
                    parent=mw,
                    caption="Load Project / Eso File",
                    filter="FILES (*.csv *.xlsx *.eso *.cfs)",
                    dir="load\\path",
                )
                assert mock_path == Path("some/dummy/path")


def test_file_dropped_signal(qtbot, mw):
    paths = ["/some/path", "/another/path"]
    with qtbot.wait_signal(mw.fileProcessingRequested, check_params_cb=lambda x: x == paths):
        mw.left_main_wgt.fileDropped.emit(paths)


def test_load_file_signal(qtbot, mw):
    mw.load_file_act.triggered.disconnect(mw.load_files_from_fs)
    with patch("chartify.ui.main_window.MainWindow.load_files_from_fs") as mock_func:
        mw.connect_ui_signals()
        mw.load_file_act.trigger()
        mock_func.assert_called_once_with()


def test_tree_act(qtbot, mw):
    mw.tree_act.toggled.disconnect(mw.on_tree_act_checked)
    with patch("chartify.ui.main_window.MainWindow.on_tree_act_checked") as mock_func:
        mw.connect_ui_signals()
        mw.tree_act.trigger()
        mock_func.assert_called_once_with(False)


def test_collapse_all_act(mw):
    mw.collapse_all_act.triggered.disconnect(mw.collapse_all)
    with patch("chartify.ui.main_window.MainWindow.collapse_all") as mock_func:
        mw.connect_ui_signals()
        mw.collapse_all_act.trigger()
        mock_func.assert_called_once_with()


def test_expand_all_act(mw):
    mw.expand_all_act.triggered.disconnect(mw.expand_all)
    with patch("chartify.ui.main_window.MainWindow.expand_all") as mock_func:
        mw.connect_ui_signals()
        mw.expand_all_act.trigger()
        mock_func.assert_called_once_with()


def test_remove_variables_act(qtbot, mw):
    with qtbot.wait_signal(mw.variableRemoveRequested):
        mw.remove_variables_act.trigger()


def test_sum_act(qtbot, mw):
    with qtbot.wait_signal(mw.aggregationRequested, check_params_cb=lambda x: x == "sum"):
        mw.sum_act.trigger()


def test_mean_act(qtbot, mw):
    with qtbot.wait_signal(mw.aggregationRequested, check_params_cb=lambda x: x == "mean"):
        mw.mean_act.trigger()


@pytest.mark.parametrize(
    "is_simple,enabled, rate_to_energy, rate_to_energy_enabled",
    [(True, False, True, True), (False, True, False, False)],
)
def test_on_table_change_requested(
    qtbot,
    eso_file_mw,
    is_simple: bool,
    enabled: bool,
    rate_to_energy: bool,
    rate_to_energy_enabled: bool,
):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(eso_file_mw.setModelRequested):
            new_model = eso_file_mw.current_view.models["hourly"]
            new_model.is_simple = is_simple
            new_model.allow_rate_to_energy = rate_to_energy
            eso_file_mw.on_table_change_requested("hourly")
            assert mock_settings.TABLE_NAME == "hourly"
            assert eso_file_mw.tree_act.isEnabled() == enabled
            assert eso_file_mw.expand_all_act.isEnabled() == enabled
            assert eso_file_mw.collapse_all_act.isEnabled() == enabled
            assert eso_file_mw.toolbar.rate_energy_btn.isEnabled() == rate_to_energy_enabled


def test_on_table_change_requested_same_table(qtbot, eso_file_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(eso_file_mw.updateModelRequested):
            eso_file_mw.on_table_change_requested("daily")
            assert mock_settings.TABLE_NAME == "daily"


def test_on_tab_changed(eso_file_mw, eso_file: EsoFile):
    models = ViewModel.models_from_file(eso_file, tree_node="type")
    models.pop("runperiod")  # delete so models are not identical
    eso_file_mw.add_treeview(1, "new file", models)
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mock_settings.TABLE_NAME = "daily"
        eso_file_mw.standard_tab_wgt.setCurrentIndex(1)
        assert mock_settings.CURRENT_FILE_ID == 1
        assert mock_settings.TABLE_NAME == "daily"
        button_names = [btn.text() for btn in eso_file_mw.toolbar.table_buttons]
        assert button_names == ["hourly", "daily", "monthly"]


def test_on_tab_changed_fresh(mw, eso_file: EsoFile):
    models = ViewModel.models_from_file(eso_file, tree_node="type")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mw.add_treeview(0, "new file", models)
        mock_settings.TABLE_NAME = "hourly"
        assert mock_settings.CURRENT_FILE_ID == 0
        assert mock_settings.TABLE_NAME == "hourly"


def test_on_tab_changed_empty(eso_file_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        eso_file_mw.standard_tab_wgt.removeTab(0)
        assert mock_settings.CURRENT_FILE_ID is None
        assert mock_settings.TABLE_NAME is None
        assert not eso_file_mw.remove_variables_act.isEnabled()
        assert not eso_file_mw.toolbar.all_files_btn.isEnabled()
        assert not eso_file_mw.toolbar.totals_outputs_btn.isEnabled()
        assert eso_file_mw.toolbar.rate_energy_btn.isEnabled()
        assert not eso_file_mw.toolbar.table_buttons
        assert not eso_file_mw.toolbar.table_group.layout().itemAt(0)


def test_on_tab_bar_double_clicked(qtbot, eso_file_mw):
    def cb(tab_index, id_):
        return tab_index == 0 and id_ == 0

    with qtbot.wait_signal(eso_file_mw.fileRenameRequested, check_params_cb=cb):
        eso_file_mw.on_tab_bar_double_clicked(0)


def test_on_tab_closed(eso_file_mw):
    eso_file_mw.standard_tab_wgt.removeTab(0)
    assert not eso_file_mw.toolbar.all_files_btn.isEnabled()
    assert not eso_file_mw.close_all_act.isEnabled()


def test_connect_tab_widget_close_requested(qtbot, mw):
    with qtbot.wait_signal(mw.fileRemoveRequested, check_params_cb=lambda x: x == 123):
        mw.standard_tab_wgt.closeTabRequested.emit(123)


def test_connect_tab_widget_current_changed(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_tab_changed") as func_mock:
        mw.standard_tab_wgt.currentChanged.emit(123)
        func_mock.assert_called_once_with(123)


def test_connect_tab_widget_tab_double_clicked(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_tab_bar_double_clicked") as func_mock:
        mw.standard_tab_wgt.tabRenameRequested.emit(123)
        func_mock.assert_called_once_with(123)


def test_connect_tab_widget_tab_closed(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.on_all_tabs_closed") as func_mock:
        mw.standard_tab_wgt.tabClosed.emit(123)
        func_mock.assert_called_once_with()


def test_connect_tab_widget_drop_btn_clicked(qtbot, mw):
    with patch("chartify.ui.main_window.MainWindow.load_files_from_fs") as func_mock:
        mw.standard_tab_wgt.tab_wgt_button.click()
        func_mock.assert_called_once_with()
