from unittest.mock import patch

import pytest
from PySide2.QtCore import QMargins, Qt, QSize, QPoint
from PySide2.QtWidgets import QSizePolicy

from chartify.settings import Settings
from chartify.ui.main_window import MainWindow
from chartify.utils.utils import FilterTuple


@patch("chartify.ui.main_window.Settings", autospec=True)
@patch("chartify.ui.toolbar.Settings", autospec=True)
def mocked_main_window(toolbar_mock, main_mock):
    for s in [main_mock, toolbar_mock]:
        s.TREE_VIEW = False
        s.SIZE = QSize(800, 600)
        s.POSITION = QPoint(150, 100)
        s.MIRRORED = False
        s.ALL_FILES = False
        s.ICON_SMALL_SIZE = QSize(20, 20)
    return MainWindow()


@pytest.fixture
def main_window(qtbot, tmp_path):
    Settings.load_settings_from_json()
    Settings.SETTINGS_PATH = tmp_path
    main_window = MainWindow()
    main_window.show()
    qtbot.add_widget(main_window)
    return main_window


def test_init_main_window(qtbot, main_window):
    assert main_window.windowTitle() == "chartify"
    assert main_window.focusPolicy() == Qt.StrongFocus
    breakpoint()
    print(Settings.as_str())
    assert main_window.size() == QSize(800, 600)
    assert main_window.pos() == QPoint(100, 100)

    assert main_window.centralWidget() == main_window.central_wgt
    assert main_window.central_layout.itemAt(0).widget() == main_window.central_splitter

    assert main_window.left_main_wgt.objectName() == "leftMainWgt"
    assert main_window.view_wgt.objectName() == "viewWidget"

    assert main_window.objectName() == "viewTools"
    assert main_window.layout().spacing() == 6
    assert main_window.contentsMargins() == QMargins(0, 0, 0, 0)

    assert main_window.tree_view_btn.objectName() == "treeButton"
    assert not main_window.tree_view_btn.isChecked()
    assert main_window.collapse_all_btn.objectName() == "collapseButton"
    assert not main_window.collapse_all_btn.isChecked()
    assert main_window.expand_all_btn.objectName() == "expandButton"
    assert not main_window.expand_all_btn.isChecked()
    assert main_window.filter_icon.objectName() == "filterIcon"

    assert main_window.variable_line_edit.placeholderText() == "type..."
    assert main_window.variable_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    )
    assert main_window.variable_line_edit.width() == 100

    assert main_window.key_line_edit.placeholderText() == "key..."
    assert main_window.key_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert main_window.key_line_edit.width() == 100

    assert main_window.units_line_edit.placeholderText() == "units..."
    assert main_window.units_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert main_window.units_line_edit.width() == 50


def test_tree_requested(qtbot, main_window):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        assert not main_window.tree_requested()

        qtbot.mouseClick(main_window.tree_view_btn, Qt.LeftButton)
        assert main_window.tree_requested()
        assert mock_settings.TREE_VIEW


def test_get_filter_tup(qtbot, main_window):
    test_filter = FilterTuple(key="foo", type="bar", units="baz")
    signals = [main_window.timer.timeout, main_window.textFiltered]
    callbacks = [None, lambda x: x == test_filter]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        qtbot.keyClicks(main_window.key_line_edit, "foo")
        qtbot.keyClicks(main_window.variable_line_edit, "bar")
        qtbot.keyClicks(main_window.units_line_edit, "baz")

    assert main_window.key_line_edit.text() == "foo"
    assert main_window.variable_line_edit.text() == "bar"
    assert main_window.units_line_edit.text() == "baz"

    assert main_window.get_filter_tuple() == test_filter


def test_toggle_tree_button(qtbot, main_window):
    with patch("chartify.ui.main_window.Settings") as mock_settings:

        def test_tree_btn_toggled(checked):
            assert main_window.tree_view_btn.property("checked")
            assert main_window.collapse_all_btn.isEnabled()
            assert main_window.expand_all_btn.isEnabled()
            assert mock_settings.TREE_VIEW
            return checked

        callbacks = [test_tree_btn_toggled, None]
        signals = [main_window.tree_view_btn.toggled, main_window.treeButtonChecked]
        with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
            qtbot.mouseClick(main_window.tree_view_btn, Qt.LeftButton)


def test_expand_all(qtbot, main_window):
    main_window.expand_all_btn.setEnabled(True)
    with qtbot.wait_signal(main_window.expandRequested):
        qtbot.mouseClick(main_window.expand_all_btn, Qt.LeftButton)


def test_collapse_all(qtbot, main_window):
    main_window.collapse_all_btn.setEnabled(True)
    with qtbot.wait_signal(main_window.collapseRequested):
        qtbot.mouseClick(main_window.collapse_all_btn, Qt.LeftButton)
