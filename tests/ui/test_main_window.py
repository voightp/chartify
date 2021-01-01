from unittest.mock import patch

from tests.fixtures import *


def test_empty_current_view(mw):
    assert mw.current_view is None


def test_empty_current_model(mw):
    assert mw.current_model is None


def test_tab_widgets(mw):
    assert mw.tab_widgets == [mw.standard_tab_wgt, mw.totals_tab_wgt, mw.diff_tab_wgt]


@pytest.mark.parametrize(
    "all_files, all_tables, n_models",
    [(True, True, 10), (False, True, 6), (True, False, 1), (False, False, 1)],
)
def test_get_all_models(all_files, all_tables, n_models, mw_esofile):
    mw_esofile.toolbar.all_files_toggle.setChecked(all_files)
    mw_esofile.toolbar.all_tables_toggle.setChecked(all_tables)
    assert n_models == len(mw_esofile.get_all_models())


@pytest.mark.parametrize(
    "table_n, all_tables, n_models", [(0, True, 4), (0, False, 1), (4, True, 5), (4, False, 1)],
)
def test_get_all_models_filter_applied(qtbot, table_n, all_tables, n_models, mw_combined_file):
    mw_combined_file.toolbar.all_tables_toggle.setChecked(all_tables)
    qtbot.mouseClick(mw_combined_file.toolbar.table_buttons[table_n], Qt.LeftButton)
    assert n_models == len(mw_combined_file.get_all_models())


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


def test_on_tab_bar_double_clicked(qtbot, mw_esofile):
    def cb(tab_index, id_):
        return tab_index == 0 and id_ == 0

    with qtbot.wait_signal(mw_esofile.fileRenameRequested, check_params_cb=cb):
        mw_esofile.on_tab_bar_double_clicked(0)


def test_on_tab_closed(mw_esofile):
    mw_esofile.standard_tab_wgt.removeTab(0)
    assert not mw_esofile.toolbar.all_files_btn.isEnabled()
    assert not mw_esofile.close_all_act.isEnabled()


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
