from unittest.mock import patch

from PySide2.QtCore import QMargins, QSize, QPoint
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QSizePolicy

from tests.fixtures import *


def test_init_main_window(qtbot, pretty_mw: MainWindow):
    mw = pretty_mw
    assert mw.windowTitle() == "chartify"
    assert mw.focusPolicy() == Qt.StrongFocus
    assert mw.size() == QSize(1200, 800)
    assert mw.pos() == QPoint(50, 50)

    assert mw.centralWidget() == mw.central_wgt
    assert mw.central_layout.itemAt(0).widget() == mw.central_splitter

    assert mw.left_main_layout.itemAt(0).widget() == mw.toolbar
    assert mw.left_main_layout.itemAt(1).widget() == mw.view_wgt
    assert mw.view_layout.itemAt(0).widget() == mw.tab_stacked_widget
    assert mw.view_layout.itemAt(1).widget() == mw.view_tools

    assert mw.tab_stacked_widget.layout().itemAt(0).widget() == mw.standard_tab_wgt
    assert mw.tab_stacked_widget.layout().itemAt(1).widget() == mw.totals_tab_wgt
    assert mw.tab_stacked_widget.layout().itemAt(2).widget() == mw.diff_tab_wgt
    assert mw.tab_stacked_widget.currentIndex() == 0

    assert mw.drop_button.parentWidget() == mw.standard_tab_wgt
    assert mw.totals_button.parentWidget() == mw.totals_tab_wgt
    assert mw.diff_button.parentWidget() == mw.diff_tab_wgt

    assert mw.drop_button.objectName() == "dropButton"
    assert mw.totals_button.objectName() == "totalsButton"
    assert mw.diff_button.objectName() == "diffButton"

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
    assert mw.progress_container.parent() == mw.statusBar()

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
    assert not mw.sum_act.isEnabled()
    assert mw.mean_act.text() == "Mean"
    assert mw.mean_act.shortcut() == QKeySequence("Ctrl+M")
    assert not mw.mean_act.isEnabled()
    assert mw.collapse_all_act.text() == "Collapse All"
    assert mw.collapse_all_act.shortcut() == QKeySequence("Ctrl+Shift+E")
    assert mw.collapse_all_act.isEnabled()
    assert mw.expand_all_act.text() == "Expand All"
    assert mw.expand_all_act.shortcut() == QKeySequence("Ctrl+E")
    assert mw.collapse_all_act.isEnabled()
    assert mw.tree_act.text() == "Tree"
    assert mw.tree_act.shortcut() == QKeySequence("Ctrl+T")
    assert mw.tree_act.isEnabled()
    assert mw.tree_act.isChecked()
    assert mw.save_act.text() == "Save"
    assert mw.save_act.shortcut() == QKeySequence("Ctrl+S")
    assert mw.save_as_act.text() == "Save as"
    assert mw.save_as_act.shortcut() == QKeySequence("Ctrl+Shift+S")
    assert mw.actions() == [
        mw.remove_variables_act,
        mw.sum_act,
        mw.mean_act,
        mw.collapse_all_act,
        mw.expand_all_act,
        mw.tree_act,
    ]

    assert not mw.close_all_act.isEnabled()
    assert not mw.remove_variables_act.isEnabled()

    assert mw.load_file_btn.text() == "Load file | files"
    assert mw.load_file_btn.objectName() == "fileButton"
    assert mw.load_file_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert mw.load_file_btn.menu().actions() == [
        mw.load_file_act,
        mw.close_all_act,
    ]
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

    assert mw.tab_stacked_widget.minimumWidth() == 400
    assert mw.main_chart_widget.minimumWidth() == 600
    assert mw.central_splitter.sizes() == Settings.SPLIT

    assert (
        mw.styleSheet()[0:144]
        == """/* ~~~~~ GLOBAL ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

* {
    font-family: Roboto;
    font-size: 13px;
    color: rgb(112, 112, 112);
}"""
    )
    assert Path(Settings.APP_TEMP_DIR, "icons").exists()
    assert [p for p in Path(Settings.APP_TEMP_DIR, "icons").iterdir() if p.suffix == ".png"]


def test_mirror_layout(pretty_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mock_settings.MIRRORED = False
        pretty_mw.mirror_layout()
        assert pretty_mw.left_main_layout.itemAt(1).widget() == pretty_mw.toolbar
        assert pretty_mw.left_main_layout.itemAt(0).widget() == pretty_mw.view_wgt
        assert pretty_mw.central_splitter.widget(1) == pretty_mw.left_main_wgt
        assert pretty_mw.central_splitter.widget(0) == pretty_mw.right_main_wgt
        assert mock_settings.MIRRORED
        assert pretty_mw.central_splitter.sizes() == [654, 540]


@pytest.mark.parametrize("checked, enabled", [(True, True), (False, False)])
def test_tree_action(qtbot, mw, checked: bool, enabled: bool):
    mw.tree_act.setChecked(not checked)
    with qtbot.wait_signal(mw.tree_act.triggered):
        qtbot.mouseClick(mw.tree_view_btn, Qt.LeftButton)
        assert mw.collapse_all_act.isEnabled() == enabled
        assert mw.expand_all_act.isEnabled() == enabled


def test_on_color_scheme_changed(qtbot, mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(mw.paletteUpdated):
            mw.on_color_scheme_changed("monochrome")
            assert mock_settings.PALETTE == mw.palettes["monochrome"]
            assert mock_settings.PALETTE_NAME == "monochrome"
