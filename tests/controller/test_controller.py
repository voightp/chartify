from tests.conftest import *


def test_load_standard_file(qtbot, mw, controller):
    with qtbot.wait_signal(controller.watcher.file_loaded, timeout=5000):
        controller.on_sync_file_processing_requested([ESO_FILE1_PATH])
    assert mw.standard_tab_wgt.count() == 1


def test_progress_signals(qtbot, mw, controller):
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
        timeout=5000,
    ):
        controller.on_sync_file_processing_requested([ESO_FILE1_PATH])


def test_progress_signals_fail(qtbot, mw, controller):
    with qtbot.wait_signal(controller.progress_thread.failed, timeout=5000):
        controller.on_sync_file_processing_requested([ESO_FILE_INCOMPLETE])
