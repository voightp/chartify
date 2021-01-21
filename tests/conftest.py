import pathlib
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from copy import copy
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

import pytest
from PySide2.QtWidgets import QWidget
from esofile_reader import GenericFile
from esofile_reader.pqt.parquet_storage import ParquetStorage

from chartify.controller.app_controller import AppController
from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.settings import Settings
from chartify.ui.main_window import MainWindow

ROOT = pathlib.Path(__file__).parent
TEST_FILES = Path(ROOT, "eso_files")

ESO_FILE1_PATH = Path(TEST_FILES, "eplusout1.eso")
ESO_FILE2_PATH = Path(TEST_FILES, "eplusout2.eso")
ESO_FILE_INCOMPLETE = Path(TEST_FILES, "eplusout_incomplete.eso")
ESO_FILE_ALL_INTERVALS_PATH = Path(TEST_FILES, "eplusout_all_intervals.eso")
EXCEL_FILE_PATH = Path(TEST_FILES, "various_table_types.xlsx")
ESO_FILE_EXCEL_PATH = Path(TEST_FILES, "eplusout.xlsx")


@pytest.fixture(scope="session")
def test_tempdir():
    path = Path(ROOT, "temp")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def session_excel_file():
    return GenericFile.from_excel(EXCEL_FILE_PATH)


@pytest.fixture(scope="session")
def session_eso_file1():
    return GenericFile.from_eplus_file(ESO_FILE1_PATH)


@pytest.fixture(scope="session")
def session_eso_file2():
    return GenericFile.from_eplus_file(ESO_FILE2_PATH)


@pytest.fixture(scope="session")
def session_eso_file_excel():
    return GenericFile.from_excel(ESO_FILE_EXCEL_PATH)


@pytest.fixture(scope="session")
def session_eso_file_all_intervals():
    return GenericFile.from_eplus_file(ESO_FILE_ALL_INTERVALS_PATH)


@pytest.fixture(scope="session")
def session_diff_file(eso_file1, eso_file_all_intervals):
    return GenericFile.from_diff(eso_file1, eso_file_all_intervals)


@pytest.fixture(scope="session")
def session_totals_file(session_eso_file1):
    return GenericFile.from_totals(session_eso_file1)


@pytest.fixture(scope="class")
def excel_file(session_excel_file):
    return copy(session_excel_file)


@pytest.fixture(scope="class")
def eso_file1(session_eso_file1):
    return copy(session_eso_file1)


@pytest.fixture(scope="class")
def eso_file2(session_eso_file2):
    return copy(session_eso_file2)


@pytest.fixture(scope="class")
def eso_file_excel(session_eso_file_excel):
    return copy(session_eso_file_excel)


@pytest.fixture(scope="class")
def eso_file_all_intervals(session_eso_file_all_intervals):
    return copy(session_eso_file_all_intervals)


@pytest.fixture(scope="class")
def diff_file(session_diff_file):
    return copy(session_diff_file)


@pytest.fixture(scope="class")
def totals_file(session_totals_file):
    return copy(session_totals_file)


@pytest.fixture(scope="class")
def parquet_eso_file_storage(eso_file_all_intervals, eso_file1, eso_file2, totals_file):
    storage = ParquetStorage()
    storage.store_file(eso_file_all_intervals)
    storage.store_file(eso_file1)
    storage.store_file(eso_file2)
    storage.store_file(totals_file)
    yield storage
    del storage


@pytest.fixture(scope="class")
def parquet_excel_file_storage(excel_file):
    storage = ParquetStorage()
    storage.store_file(excel_file)
    yield storage
    del storage


@pytest.fixture(scope="class")
def parquet_combined_file_storage(eso_file_excel):
    storage = ParquetStorage()
    storage.store_file(eso_file_excel)
    yield storage
    del storage


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
            with mock.patch("chartify.ui.main_window.QWebEngineView") as wgt:
                wgt.return_value = QWidget()
                main_window = MainWindow()
                model = AppModel()
                wv_controller = Mock()
                # wv_controller = WVController(model, main_window.web_view)
                controller = AppController(model, main_window, wv_controller)
                controller.pool = ProcessPoolExecutor()  # reusable executor crashes
                qtbot.add_widget(main_window)
                main_window.show()
                yield model, main_window, controller


@pytest.fixture(scope="function")
def model(app_setup):
    return app_setup[0]


@pytest.fixture(scope="function")
def mw(app_setup):
    return app_setup[1]


@pytest.fixture(scope="function")
def controller(app_setup):
    return app_setup[2]


@pytest.fixture(scope="function")
def mw_esofile(mw, controller, model, parquet_eso_file_storage, qtbot):
    for file in parquet_eso_file_storage.files.values():
        controller.on_file_loaded(file)
        controller.ids.append(file.id_)
    model.storage = parquet_eso_file_storage
    return mw


@pytest.fixture(scope="function")
def mw_excel_file(mw, controller, model, parquet_excel_file_storage, qtbot):
    for file in parquet_excel_file_storage.files.values():
        controller.on_file_loaded(file)
        controller.ids.append(file.id_)
    mw.on_table_change_requested("daily")
    model.storage = parquet_excel_file_storage
    return mw


@pytest.fixture(scope="function")
def mw_combined_file(mw, controller, parquet_combined_file_storage, qtbot):
    for file in parquet_combined_file_storage.files.values():
        controller.on_file_loaded(file)
        controller.ids.append(file.id_)
    model.storage = parquet_combined_file_storage
    return mw
