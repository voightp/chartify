import pathlib
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from PySide2.QtCore import Qt
from esofile_reader import GenericFile

from chartify.controller.app_controller import AppController
from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.settings import Settings, OutputType
from chartify.ui.main_window import MainWindow
from chartify.ui.treeview_model import ViewModel

ROOT = pathlib.Path(__file__).parent
TEST_FILES = Path(ROOT, "eso_files")

ESO_FILE1_PATH = Path(TEST_FILES, "eplusout1.eso")
ESO_FILE2_PATH = Path(TEST_FILES, "eplusout2.eso")
ESO_FILE_INCOMPLETE = Path(TEST_FILES, "eplusout_incomplete.eso")
ESO_FILE_ALL_INTERVALS_PATH = Path(TEST_FILES, "eplusout_all_intervals.eso")
EXCEL_FILE_PATH = Path(TEST_FILES, "test_excel_results.xlsx")


@pytest.fixture(scope="module")
def excel_file():
    return GenericFile.from_excel(EXCEL_FILE_PATH)


@pytest.fixture(scope="module")
def eso_file1():
    return GenericFile.from_eplus_file(ESO_FILE1_PATH)


@pytest.fixture(scope="module")
def eso_file2():
    return GenericFile.from_eplus_file(ESO_FILE2_PATH)


@pytest.fixture(scope="module")
def eso_file_all_intervals():
    return GenericFile.from_eplus_file(ESO_FILE_ALL_INTERVALS_PATH)


@pytest.fixture(scope="module")
def diff_file(eso_file1, eso_file_all_intervals):
    return GenericFile.from_diff(eso_file1, eso_file_all_intervals)


@pytest.fixture(scope="module")
def totals_file(eso_file1, eso_file_all_intervals):
    return GenericFile.from_totals(eso_file1)


@pytest.fixture(scope="session")
def test_tempdir():
    with tempfile.TemporaryDirectory(dir=ROOT) as tempdir:
        yield tempdir


@pytest.fixture(scope="function")
def pretty_mw(qtbot, test_tempdir):
    with tempfile.TemporaryDirectory(prefix="chartify", dir=test_tempdir) as fix_dir:
        Settings.APP_TEMP_DIR = Path(fix_dir)
        Settings.load_settings_from_json()
        main_window = MainWindow()
        model = AppModel()
        wv_controller = WVController(model, main_window.web_view)
        AppController(model, main_window, wv_controller)
        qtbot.add_widget(main_window)
        main_window.show()
        yield main_window


@pytest.fixture(scope="function")
def app_setup(qtbot, test_tempdir):
    with tempfile.TemporaryDirectory(prefix="chartify", dir=test_tempdir) as fix_dir:
        Settings.APP_TEMP_DIR = Path(fix_dir)
        Settings.load_settings_from_json()
        with mock.patch("chartify.ui.main_window.MainWindow.load_css_and_icons"):
            main_window = MainWindow()
            model = AppModel()
            wv_controller = WVController(model, main_window.web_view)
            controller = AppController(model, main_window, wv_controller)
            qtbot.add_widget(main_window)
            main_window.show()
            yield model, main_window, controller


@pytest.fixture(scope="function")
def eso_file_mw(mw, excel_file, eso_file1, totals_file, qtbot):
    models1 = ViewModel.models_from_file(eso_file1, tree_node="type")
    mw.add_treeview(0, eso_file1.file_name, OutputType.STANDARD, models1)
    models2 = ViewModel.models_from_file(excel_file, tree_node="type")
    mw.add_treeview(1, excel_file.file_name, OutputType.STANDARD, models2)
    models3 = ViewModel.models_from_file(excel_file, tree_node="type")
    mw.add_treeview(1, totals_file.file_name, OutputType.TOTALS, models3)
    return mw


@pytest.fixture(scope="function")
def excel_file_mw(mw, excel_file, eso_file1, totals_file, qtbot):
    models1 = ViewModel.models_from_file(eso_file1, tree_node="type")
    mw.add_treeview(0, eso_file1.file_name, OutputType.STANDARD, models1)
    models2 = ViewModel.models_from_file(excel_file, tree_node="type")
    mw.add_treeview(1, excel_file.file_name, OutputType.STANDARD, models2)
    models3 = ViewModel.models_from_file(excel_file, tree_node="type")
    mw.add_treeview(1, totals_file.file_name, OutputType.TOTALS, models3)
    mw.current_tab_widget.setCurrentIndex(1)
    qtbot.mouseClick(mw.toolbar.table_buttons[3], Qt.LeftButton)
    return mw


@pytest.fixture(scope="function")
def model(app_setup):
    return app_setup[0]


@pytest.fixture(scope="function")
def mw(app_setup):
    return app_setup[1]


@pytest.fixture(scope="function")
def controller(app_setup):
    return app_setup[2]