from pathlib import Path
from unittest.mock import patch

import pytest
from PySide2.QtCore import QMargins, Qt, QSize, QPoint
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QSizePolicy

from chartify.settings import Settings
from chartify.ui.main_window import MainWindow
from chartify.utils.utils import FilterTuple


# @patch("chartify.ui.mw.Settings", autospec=True)
# @patch("chartify.ui.toolbar.Settings", autospec=True)
# def mocked_main_window(toolbar_mock, main_mock):
#     for s in [main_mock, toolbar_mock]:
#         s.TREE_VIEW = False
#         s.SIZE = QSize(800, 600)
#         s.POSITION = QPoint(150, 100)
#         s.MIRRORED = False
#         s.ALL_FILES = False
#         s.ICON_SMALL_SIZE = QSize(20, 20)
#     return MainWindow()


@pytest.fixture
def mw(qtbot, tmp_path):
    Settings.SETTINGS_PATH = Path("dummy/path")  # force default
    Settings.load_settings_from_json()
    main_window = MainWindow()
    qtbot.add_widget(main_window)
    main_window.closeEvent = lambda x: True
    main_window.show()
    return main_window


def test_init_main_window(qtbot, mw):
    assert mw.windowTitle() == "chartify"
    assert mw.focusPolicy() == Qt.StrongFocus
    assert mw.size() == QSize(1200, 800)
    assert mw.pos() == QPoint(50, 50)

    assert mw.centralWidget() == mw.central_wgt
    assert mw.central_layout.itemAt(0).widget() == mw.central_splitter

    assert mw.left_main_layout.itemAt(0).widget() == mw.toolbar
    assert mw.left_main_layout.itemAt(1).widget() == mw.view_wgt
    assert mw.view_layout.itemAt(0).widget() == mw.tab_wgt
    assert mw.view_layout.itemAt(1).widget() == mw.view_tools

    assert mw.left_main_wgt.objectName() == "leftMainWgt"
    assert mw.view_wgt.objectName() == "viewWidget"

    assert mw.objectName() == "viewTools"
    assert mw.layout().spacing() == 6
    assert mw.contentsMargins() == QMargins(0, 0, 0, 0)

    assert mw.tree_view_btn.objectName() == "treeButton"
    assert mw.tree_view_btn.isChecked()
    assert mw.tree_view_btn.isEnabled()
    assert mw.collapse_all_btn.objectName() == "collapseButton"
    assert not mw.collapse_all_btn.isChecked()
    assert mw.collapse_all_btn.isEnabled()
    assert mw.expand_all_btn.objectName() == "expandButton"
    assert not mw.expand_all_btn.isChecked()
    assert mw.expand_all_btn.isEnabled()
    assert mw.filter_icon.objectName() == "filterIcon"

    assert mw.type_line_edit.placeholderText() == "type..."
    assert mw.type_line_edit.sizePolicy() == QSizePolicy(
        QSizePolicy.Expanding, QSizePolicy.Fixed
    )
    assert mw.type_line_edit.width() == 100

    assert mw.key_line_edit.placeholderText() == "key..."
    assert mw.key_line_edit.sizePolicy() == (QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
    assert mw.key_line_edit.width() == 100

    assert mw.units_line_edit.placeholderText() == "units..."
    assert mw.units_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert mw.units_line_edit.width() == 50

    assert mw.central_splitter.widget(0) == mw.left_main_wgt
    assert mw.central_splitter.widget(1) == mw.right_main_wgt
    assert mw.main_chart_widget.parent() == mw.right_main_wgt
    assert mw.main_chart_widget.parent() == mw.right_main_wgt
    assert mw.web_view.parent() == mw.main_chart_widget

    assert mw.statusBar() == mw.status_bar
    assert mw.statusBar().height() == 20
    assert mw.progress_cont.parent() == mw.statusBar()

    assert list(mw.palettes.keys()) == ["default", "monochrome", "dark"]
    assert Settings.PALETTE == mw.palettes[Settings.PALETTE_NAME]

    assert mw.scheme_btn.objectName() == "schemeButton"
    assert mw.scheme_btn.parent() == mw.statusBar()
    assert mw.swap_btn.objectName() == "swapButton"
    assert mw.swap_btn.parent() == mw.statusBar()

    assert mw.toolbar.layout.itemAt(0).widget() == mw.mini_menu

    assert mw.load_file_act.text() == "Load file | files"
    assert mw.load_file_act.shortcut() == QKeySequence("Ctrl+L")
    assert mw.close_all_act.text() == "Close all"
    assert mw.remove_variables_act.text() == "Delete"
    assert mw.sum_act.text() == "Sum"
    assert mw.sum_act.shortcut() == QKeySequence("Ctrl+T")
    assert mw.avg_act.text() == "Mean"
    assert mw.avg_act.shortcut() == QKeySequence("Ctrl+M")
    assert mw.collapse_all_act.text() == "Collapse All"
    assert mw.collapse_all_act.shortcut() == QKeySequence("Ctrl+Shift+E")
    assert mw.expand_all_act.text() == "Expand All"
    assert mw.expand_all_act.shortcut() == QKeySequence("Ctrl+E")
    assert mw.tree_act.text() == "Tree"
    assert mw.tree_act.shortcut() == QKeySequence("Ctrl+T")
    assert mw.save_act.text() == "Save"
    assert mw.save_act.shortcut() == QKeySequence("Ctrl+S")
    assert mw.save_as_act.text() == "Save as"
    assert mw.save_as_act.shortcut() == QKeySequence("Ctrl+Shift+S")
    assert mw.actions() == [
        mw.remove_variables_act,
        mw.sum_act,
        mw.avg_act,
        mw.collapse_all_act,
        mw.expand_all_act,
        mw.tree_act,
    ]

    assert not mw.close_all_act.isEnabled()
    assert not mw.remove_variables_act.isEnabled()

    assert mw.load_file_btn.text() == "Load file | files"
    assert mw.load_file_btn.objectName() == "fileButton"
    assert mw.load_file_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert mw.load_file_btn.menu().actions() == [mw.load_file_act, mw.close_all_act]
    assert mw.save_btn.text() == "Save"
    assert mw.save_btn.objectName() == "saveButton"
    assert mw.save_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert mw.save_btn.menu().actions() == [mw.save_act, mw.save_as_act]
    assert mw.about_btn.text() == "About"
    assert mw.about_btn.objectName() == "aboutButton"
    assert mw.about_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert mw.about_btn.menu().actions() == []

    assert mw.mini_menu_layout.itemAt(0).widget() == mw.load_file_btn
    assert mw.mini_menu_layout.itemAt(1).widget() == mw.save_btn
    assert mw.mini_menu_layout.itemAt(2).widget() == mw.about_btn

    assert mw.tab_wgt.minimumWidth() == 400
    assert mw.main_chart_widget.minimumWidth() == 600
    assert mw.central_splitter.sizes() == Settings.SPLIT

    assert (
        mw.css.content[0:144]
        == """/* ~~~~~ GLOBAL ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

* {
    font-family: Roboto;
    font-size: 13px;
    color: rgb(112, 112, 112);
}"""
    )


def test_tree_requested(qtbot, mw):
    with patch("chartify.ui.mw.Settings") as mock_settings:
        assert not mw.tree_requested()

        qtbot.mouseClick(mw.tree_view_btn, Qt.LeftButton)
        assert mw.tree_requested()
        assert mock_settings.TREE_VIEW


def test_get_filter_tup(qtbot, mw):
    test_filter = FilterTuple(key="foo", type="bar", units="baz")
    signals = [mw.timer.timeout, mw.textFiltered]
    callbacks = [None, lambda x: x == test_filter]
    with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
        qtbot.keyClicks(mw.key_line_edit, "foo")
        qtbot.keyClicks(mw.type_line_edit, "bar")
        qtbot.keyClicks(mw.units_line_edit, "baz")

    assert mw.key_line_edit.text() == "foo"
    assert mw.type_line_edit.text() == "bar"
    assert mw.units_line_edit.text() == "baz"

    assert mw.get_filter_tuple() == test_filter


def test_toggle_tree_button(qtbot, mw):
    with patch("chartify.ui.mw.Settings") as mock_settings:

        def test_tree_btn_toggled(checked):
            assert mw.tree_view_btn.property("checked")
            assert mw.collapse_all_btn.isEnabled()
            assert mw.expand_all_btn.isEnabled()
            assert mock_settings.TREE_VIEW
            return checked

        callbacks = [test_tree_btn_toggled, None]
        signals = [mw.tree_view_btn.toggled, mw.treeButtonChecked]
        with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
            qtbot.mouseClick(mw.tree_view_btn, Qt.LeftButton)


def test_expand_all(qtbot, mw):
    mw.expand_all_btn.setEnabled(True)
    with qtbot.wait_signal(mw.expandRequested):
        qtbot.mouseClick(mw.expand_all_btn, Qt.LeftButton)


def test_collapse_all(qtbot, mw):
    mw.collapse_all_btn.setEnabled(True)
    with qtbot.wait_signal(mw.collapseRequested):
        qtbot.mouseClick(mw.collapse_all_btn, Qt.LeftButton)
