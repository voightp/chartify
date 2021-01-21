from pathlib import Path

import pytest

from tests.conftest import ESO_FILE_INCOMPLETE, ESO_FILE1_PATH, ESO_FILE2_PATH, EXCEL_FILE_PATH


class TestLoadFiles:
    def test_load_standard_files(self, qtbot, mw, controller):
        with qtbot.wait_signals([controller.watcher.file_loaded] * 3, timeout=10000):
            mw.load_files_from_paths([ESO_FILE1_PATH, ESO_FILE2_PATH, EXCEL_FILE_PATH])
        assert mw.standard_tab_wgt.count() == 3

    def test_load_standard_files_synchronously(self, qtbot, mw, controller):
        with qtbot.wait_signals(
            [controller.watcher.file_loaded, controller.watcher.file_loaded], timeout=5000
        ):
            mw.load_files_from_paths_synchronously([ESO_FILE1_PATH, ESO_FILE2_PATH])
        assert mw.standard_tab_wgt.count() == 2

    def test_progress_signals(self, qtbot, mw, controller):
        with qtbot.wait_signals(
            signals=[
                controller.progress_thread.file_added,
                controller.progress_thread.progress_updated,
                controller.progress_thread.range_changed,
                controller.progress_thread.pending,
                controller.progress_thread.status_changed,
                controller.progress_thread.done,
                mw.standard_tab_wgt.currentTabChanged,
            ],
            timeout=10000,
        ):
            mw.load_files_from_paths([ESO_FILE1_PATH])

    @pytest.mark.skip
    def test_progress_signals_fail(self, qtbot, mw, controller):
        with qtbot.wait_signal(controller.progress_thread.failed, timeout=10000):
            mw.load_files_from_paths([ESO_FILE_INCOMPLETE])

    @pytest.mark.skip
    def test_load_unsupported_file(self, qtbot, mw, controller):
        with qtbot.wait_signal(controller.progress_thread.failed, timeout=10000):
            mw.load_files_from_paths([Path("foo.bar")])
