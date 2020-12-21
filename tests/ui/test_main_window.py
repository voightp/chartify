from typing import List, Optional, Set, Tuple
from unittest.mock import patch, MagicMock

from PySide2.QtCore import QMargins, Qt, QSize, QPoint
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QSizePolicy, QAction
from esofile_reader import Variable, SimpleVariable, EsoFile
from chartify.settings import OutputType
from chartify.ui.treeview_model import ViewModel
from chartify.utils.utils import FilterTuple, VariableData
from tests.test_main import *


@pytest.fixture(scope="function")
def populated_mw(pretty_mw, excel_file, eso_file1, qtbot):
    # pretty_mw.load_files_from_paths([excel_file,eso_file1]
    models1 = ViewModel.models_from_file(eso_file1, tree_node="type")
    pretty_mw.add_treeview(0, eso_file1.file_name, OutputType.STANDARD, models1)
    models2 = ViewModel.models_from_file(excel_file, tree_node="type")
    pretty_mw.add_treeview(1, excel_file.file_name, OutputType.STANDARD, models2)
    return pretty_mw


def test_init_main_window(qtbot, pretty_mw: MainWindow):
    assert pretty_mw.windowTitle() == "chartify"
    assert pretty_mw.focusPolicy() == Qt.StrongFocus
    assert pretty_mw.size() == QSize(1200, 800)
    assert pretty_mw.pos() == QPoint(50, 50)

    assert pretty_mw.centralWidget() == pretty_mw.central_wgt
    assert pretty_mw.central_layout.itemAt(0).widget() == pretty_mw.central_splitter

    assert pretty_mw.left_main_layout.itemAt(0).widget() == pretty_mw.toolbar
    assert pretty_mw.left_main_layout.itemAt(1).widget() == pretty_mw.view_wgt
    assert pretty_mw.view_layout.itemAt(0).widget() == pretty_mw.tab_stacked_widget
    assert pretty_mw.view_layout.itemAt(1).widget() == pretty_mw.view_tools

    assert (
        pretty_mw.tab_stacked_widget.layout().itemAt(0).widget() == pretty_mw.standard_tab_wgt
    )
    assert pretty_mw.tab_stacked_widget.layout().itemAt(1).widget() == pretty_mw.totals_tab_wgt
    assert pretty_mw.tab_stacked_widget.layout().itemAt(2).widget() == pretty_mw.diff_tab_wgt
    assert pretty_mw.tab_stacked_widget.currentIndex() == 0

    assert pretty_mw.drop_button.parentWidget() == pretty_mw.standard_tab_wgt
    assert pretty_mw.totals_button.parentWidget() == pretty_mw.totals_tab_wgt
    assert pretty_mw.diff_button.parentWidget() == pretty_mw.diff_tab_wgt

    assert pretty_mw.drop_button.objectName() == "dropButton"
    assert pretty_mw.totals_button.objectName() == "totalsButton"
    assert pretty_mw.diff_button.objectName() == "diffButton"

    assert pretty_mw.left_main_wgt.objectName() == "leftMainWgt"
    assert pretty_mw.view_wgt.objectName() == "viewWidget"

    assert pretty_mw.objectName() == "viewTools"
    assert pretty_mw.layout().spacing() == 6
    assert pretty_mw.contentsMargins() == QMargins(0, 0, 0, 0)

    assert pretty_mw.tree_view_btn.objectName() == "treeButton"
    assert pretty_mw.tree_view_btn.isChecked()
    assert pretty_mw.tree_view_btn.isEnabled()
    assert pretty_mw.collapse_all_btn.objectName() == "collapseButton"
    assert not pretty_mw.collapse_all_btn.isChecked()
    assert pretty_mw.collapse_all_btn.isEnabled()
    assert pretty_mw.expand_all_btn.objectName() == "expandButton"
    assert not pretty_mw.expand_all_btn.isChecked()
    assert pretty_mw.expand_all_btn.isEnabled()
    assert pretty_mw.filter_icon.objectName() == "filterIcon"

    assert pretty_mw.type_line_edit.placeholderText() == "type..."
    assert pretty_mw.type_line_edit.sizePolicy() == QSizePolicy(
        QSizePolicy.Expanding, QSizePolicy.Fixed
    )
    assert pretty_mw.type_line_edit.width() == 100

    assert pretty_mw.key_line_edit.placeholderText() == "key..."
    assert pretty_mw.key_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert pretty_mw.key_line_edit.width() == 100

    assert pretty_mw.units_line_edit.placeholderText() == "units..."
    assert pretty_mw.units_line_edit.sizePolicy() == (
        QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    )
    assert pretty_mw.units_line_edit.width() == 50

    assert pretty_mw.central_splitter.widget(0) == pretty_mw.left_main_wgt
    assert pretty_mw.central_splitter.widget(1) == pretty_mw.right_main_wgt
    assert pretty_mw.main_chart_widget.parent() == pretty_mw.right_main_wgt
    assert pretty_mw.main_chart_widget.parent() == pretty_mw.right_main_wgt
    assert pretty_mw.web_view.parent() == pretty_mw.main_chart_widget

    assert pretty_mw.statusBar() == pretty_mw.status_bar
    assert pretty_mw.statusBar().height() == 20
    assert pretty_mw.progress_container.parent() == pretty_mw.statusBar()

    assert list(pretty_mw.palettes.keys()) == ["default", "monochrome", "dark"]
    assert Settings.PALETTE == pretty_mw.palettes[Settings.PALETTE_NAME]

    assert pretty_mw.scheme_btn.objectName() == "schemeButton"
    assert pretty_mw.scheme_btn.parent() == pretty_mw.statusBar()
    assert pretty_mw.swap_btn.objectName() == "swapButton"
    assert pretty_mw.swap_btn.parent() == pretty_mw.statusBar()

    assert pretty_mw.toolbar.layout.itemAt(0).widget() == pretty_mw.mini_menu

    assert pretty_mw.load_file_act.text() == "Load file | files"
    assert pretty_mw.load_file_act.shortcut() == QKeySequence("Ctrl+L")
    assert pretty_mw.close_all_act.text() == "Close all"
    assert pretty_mw.remove_variables_act.text() == "Delete"
    assert pretty_mw.sum_act.text() == "Sum"
    assert pretty_mw.sum_act.shortcut() == QKeySequence("Ctrl+T")
    assert not pretty_mw.sum_act.isEnabled()
    assert pretty_mw.mean_act.text() == "Mean"
    assert pretty_mw.mean_act.shortcut() == QKeySequence("Ctrl+M")
    assert not pretty_mw.mean_act.isEnabled()
    assert pretty_mw.collapse_all_act.text() == "Collapse All"
    assert pretty_mw.collapse_all_act.shortcut() == QKeySequence("Ctrl+Shift+E")
    assert pretty_mw.collapse_all_act.isEnabled()
    assert pretty_mw.expand_all_act.text() == "Expand All"
    assert pretty_mw.expand_all_act.shortcut() == QKeySequence("Ctrl+E")
    assert pretty_mw.collapse_all_act.isEnabled()
    assert pretty_mw.tree_act.text() == "Tree"
    assert pretty_mw.tree_act.shortcut() == QKeySequence("Ctrl+T")
    assert pretty_mw.tree_act.isEnabled()
    assert pretty_mw.tree_act.isChecked()
    assert pretty_mw.save_act.text() == "Save"
    assert pretty_mw.save_act.shortcut() == QKeySequence("Ctrl+S")
    assert pretty_mw.save_as_act.text() == "Save as"
    assert pretty_mw.save_as_act.shortcut() == QKeySequence("Ctrl+Shift+S")
    assert pretty_mw.actions() == [
        pretty_mw.remove_variables_act,
        pretty_mw.sum_act,
        pretty_mw.mean_act,
        pretty_mw.collapse_all_act,
        pretty_mw.expand_all_act,
        pretty_mw.tree_act,
    ]

    assert not pretty_mw.close_all_act.isEnabled()
    assert not pretty_mw.remove_variables_act.isEnabled()

    assert pretty_mw.load_file_btn.text() == "Load file | files"
    assert pretty_mw.load_file_btn.objectName() == "fileButton"
    assert pretty_mw.load_file_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert pretty_mw.load_file_btn.menu().actions() == [
        pretty_mw.load_file_act,
        pretty_mw.close_all_act,
    ]
    assert pretty_mw.save_btn.text() == "Save"
    assert pretty_mw.save_btn.objectName() == "saveButton"
    assert pretty_mw.save_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert pretty_mw.save_btn.menu().actions() == [pretty_mw.save_act, pretty_mw.save_as_act]
    assert pretty_mw.about_btn.text() == "About"
    assert pretty_mw.about_btn.objectName() == "aboutButton"
    assert pretty_mw.about_btn.iconSize() == Settings.ICON_SMALL_SIZE
    assert pretty_mw.about_btn.menu().actions() == []

    assert pretty_mw.mini_menu_layout.itemAt(0).widget() == pretty_mw.load_file_btn
    assert pretty_mw.mini_menu_layout.itemAt(1).widget() == pretty_mw.save_btn
    assert pretty_mw.mini_menu_layout.itemAt(2).widget() == pretty_mw.about_btn

    assert pretty_mw.tab_stacked_widget.minimumWidth() == 400
    assert pretty_mw.main_chart_widget.minimumWidth() == 600
    assert pretty_mw.central_splitter.sizes() == Settings.SPLIT

    assert (
        pretty_mw.styleSheet()[0:144]
        == """/* ~~~~~ GLOBAL ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

* {
    font-family: Roboto;
    font-size: 13px;
    color: rgb(112, 112, 112);
}"""
    )


def test_empty_current_view(pretty_mw):
    assert not pretty_mw.current_view


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


def test_add_new_tab(pretty_mw, eso_file: EsoFile):
    models = ViewModel.models_from_file(eso_file)
    pretty_mw.add_treeview(0, "test", models)
    assert pretty_mw.standard_tab_wgt.widget(0) == pretty_mw.current_view
    assert not pretty_mw.toolbar.all_files_btn.isEnabled()
    assert not pretty_mw.close_all_act.isEnabled()

    models = ViewModel.models_from_file(eso_file)
    pretty_mw.add_treeview(0, "test", models)
    assert pretty_mw.standard_tab_wgt.widget(0) == pretty_mw.current_view
    assert pretty_mw.toolbar.all_files_btn.isEnabled()
    assert pretty_mw.close_all_act.isEnabled()


@pytest.mark.parametrize("checked,node,enabled", [(True, "type", True), (False, None, False)])
def test_on_tree_act_checked(
    qtbot, pretty_mw, checked: bool, node: Optional[str], enabled: bool
):
    pretty_mw.tree_act.setChecked(not checked)
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signals([pretty_mw.tree_act.triggered, pretty_mw.updateModelRequested]):
            qtbot.mouseClick(pretty_mw.tree_view_btn, Qt.LeftButton)
            assert pretty_mw.collapse_all_act.isEnabled() == enabled
            assert pretty_mw.expand_all_act.isEnabled() == enabled
            assert mock_settings.TREE_NODE == node


def test_expand_all_empty(pretty_mw):
    try:
        pretty_mw.expand_all()
    except AttributeError:
        pytest.fail()


def test_expand_all(qtbot, populated_mw: MainWindow):
    populated_mw.on_table_change_requested("daily")
    qtbot.mouseClick(populated_mw.expand_all_btn, Qt.LeftButton)
    assert len(populated_mw.current_view.source_model.expanded) == 28


def test_collapse_all_empty(pretty_mw):
    try:
        pretty_mw.collapse_all()
    except AttributeError:
        pytest.fail()


def test_collapse_all(qtbot, populated_mw: MainWindow):
    populated_mw.on_table_change_requested("daily")
    qtbot.mouseClick(populated_mw.expand_all_btn, Qt.LeftButton)
    qtbot.mouseClick(populated_mw.collapse_all_btn, Qt.LeftButton)
    assert len(populated_mw.current_view.source_model.expanded) == 0


def test_save_storage_to_fs(pretty_mw):
    with patch("chartify.ui.main_window.QFileDialog") as qdialog:
        with patch("chartify.ui.main_window.Settings") as mock_settings:
            mock_settings.SAVE_PATH = "save/path"
            qdialog.getSaveFileName.return_value = ("some/dummy/path/file.abc", ".abc")
            pretty_mw.save_storage_to_fs()
            qdialog.getSaveFileName.assert_called_with(
                parent=pretty_mw, caption="Save project", filter="CFS (*.cfs)", dir="save/path"
            )
            path = pretty_mw.save_storage_to_fs()
            assert mock_settings.SAVE_PATH == "some\\dummy\\path"
            assert path == Path("some/dummy/path/file.abc")


def test_load_files_from_fs(qtbot, pretty_mw):
    def cb(paths):
        return paths == [Path("some/dummy/path/file.abc")]

    with patch("chartify.ui.main_window.QFileDialog") as qdialog:
        with patch("chartify.ui.main_window.Settings") as mock_settings:
            with qtbot.wait_signal(pretty_mw.fileProcessingRequested, check_params_cb=cb):
                qdialog.getOpenFileNames.return_value = (["some/dummy/path/file.abc"], ".abc")
                mock_settings.LOAD_PATH = Path("load/path")
                pretty_mw.load_files_from_fs()
                qdialog.getOpenFileNames.assert_called_with(
                    parent=pretty_mw,
                    caption="Load Project / Eso File",
                    filter="FILES (*.csv *.xlsx *.eso *.cfs)",
                    dir="load\\path",
                )
                assert mock_settings.LOAD_PATH == Path("some/dummy/path")


def test_on_color_scheme_changed(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(pretty_mw.paletteUpdated):
            pretty_mw.on_color_scheme_changed("monochrome")
            assert mock_settings.PALETTE == pretty_mw.palettes["monochrome"]
            assert mock_settings.PALETTE_NAME == "monochrome"


@pytest.mark.parametrize(
    "variables,enabled,rate_to_energy",
    [
        ([VariableData("A", "B", "C"), VariableData("C", "D", "kWh")], False, False,),
        ([VariableData("A", "B", "C"), VariableData("C", "D", "C")], True, False),
        ([VariableData("A", "B", "J"), VariableData("C", "D", "W")], False, False,),
        ([VariableData("A", "B", "J"), VariableData("C", "D", "W")], True, True),
    ],
)
def test_on_selection_populated(
    qtbot, pretty_mw, variables: List[VariableData], enabled: bool, rate_to_energy: bool
):
    def cb(vd):
        return vd == variables

    tab_wgt_mock = MagicMock()
    model_mock = MagicMock()
    model_mock.source_model.allow_rate_to_energy = rate_to_energy
    tab_wgt_mock.currentWidget.return_value = model_mock
    pretty_mw.standard_tab_wgt = tab_wgt_mock

    with qtbot.wait_signal(pretty_mw.selectionChanged, check_params_cb=cb):
        pretty_mw.on_selection_populated(variables)
        assert pretty_mw.remove_variables_act.isEnabled()
        assert pretty_mw.toolbar.remove_btn.isEnabled()
        assert pretty_mw.toolbar.sum_btn.isEnabled() == enabled
        assert pretty_mw.toolbar.mean_btn.isEnabled() == enabled


def test_on_selection_cleared(qtbot, pretty_mw):
    with qtbot.wait_signal(pretty_mw.selectionChanged, check_params_cb=lambda x: x == []):
        pretty_mw.on_selection_cleared()
        assert not pretty_mw.remove_variables_act.isEnabled()
        assert not pretty_mw.toolbar.sum_btn.isEnabled()
        assert not pretty_mw.toolbar.mean_btn.isEnabled()
        assert not pretty_mw.toolbar.remove_btn.isEnabled()


def test_on_tree_node_changed(qtbot, pretty_mw):
    with qtbot.wait_signal(pretty_mw.updateModelRequested):
        with patch("chartify.ui.main_window.Settings") as mock_settings:
            pretty_mw.on_tree_node_changed("foo")
            assert mock_settings.TREE_NODE == "foo"


def test_on_view_header_resized(pretty_mw):
    pretty_mw.on_view_header_resized("tree", 100)
    assert pretty_mw.view_settings["tree"]["widths"]["interactive"] == 100


def test_on_view_header_changed(pretty_mw):
    pretty_mw.on_view_header_changed("tree", ("foo", "bar", "baz"))
    assert pretty_mw.view_settings["tree"]["header"] == ("foo", "bar", "baz")


def test_on_splitter_moved(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        pretty_mw.central_splitter.setSizes([530, 664])
        pretty_mw.on_splitter_moved()  # this is only triggered with manual interaction
        assert mock_settings.SPLIT == [530, 664]


def test_file_dropped_signal(qtbot, pretty_mw):
    paths = ["/some/path", "/another/path"]
    with qtbot.wait_signal(
        pretty_mw.fileProcessingRequested, check_params_cb=lambda x: x == paths
    ):
        pretty_mw.left_main_wgt.fileDropped.emit(paths)


def test_load_file_signal(qtbot, pretty_mw):
    pretty_mw.load_file_act.triggered.disconnect(pretty_mw.load_files_from_fs)
    with patch("chartify.ui.main_window.MainWindow.load_files_from_fs") as mock_func:
        pretty_mw.connect_ui_signals()
        pretty_mw.load_file_act.trigger()
        mock_func.assert_called_once_with()


def test_tree_act(qtbot, pretty_mw):
    pretty_mw.tree_act.toggled.disconnect(pretty_mw.on_tree_act_checked)
    with patch("chartify.ui.main_window.MainWindow.on_tree_act_checked") as mock_func:
        pretty_mw.connect_ui_signals()
        pretty_mw.tree_act.trigger()
        mock_func.assert_called_once_with(False)


def test_collapse_all_act(pretty_mw):
    pretty_mw.collapse_all_act.triggered.disconnect(pretty_mw.collapse_all)
    with patch("chartify.ui.main_window.MainWindow.collapse_all") as mock_func:
        pretty_mw.connect_ui_signals()
        pretty_mw.collapse_all_act.trigger()
        mock_func.assert_called_once_with()


def test_expand_all_act(pretty_mw):
    pretty_mw.expand_all_act.triggered.disconnect(pretty_mw.expand_all)
    with patch("chartify.ui.main_window.MainWindow.expand_all") as mock_func:
        pretty_mw.connect_ui_signals()
        pretty_mw.expand_all_act.trigger()
        mock_func.assert_called_once_with()


def test_remove_variables_act(qtbot, pretty_mw):
    with qtbot.wait_signal(pretty_mw.variableRemoveRequested):
        pretty_mw.remove_variables_act.trigger()


def test_sum_act(qtbot, pretty_mw):
    with qtbot.wait_signal(
        pretty_mw.aggregationRequested, check_params_cb=lambda x: x == "sum"
    ):
        pretty_mw.sum_act.trigger()


def test_mean_act(qtbot, pretty_mw):
    with qtbot.wait_signal(
        pretty_mw.aggregationRequested, check_params_cb=lambda x: x == "mean"
    ):
        pretty_mw.mean_act.trigger()


def test_get_filter_tuple(qtbot, pretty_mw):
    pretty_mw.key_line_edit.setText("foo")
    pretty_mw.type_line_edit.setText("bar")
    pretty_mw.units_line_edit.setText("baz")
    assert FilterTuple("foo", "bar", "baz") == pretty_mw.get_filter_tuple()


@pytest.mark.parametrize(
    "similar,old_pos, current_pos,expected_pos,ref_expanded,current_expanded,expected_expanded",
    [
        (True, 123, 321, 123, {"A", "B"}, {"C", "D"}, {"A", "B"}),
        (False, 123, 321, 321, {"A", "B"}, {"C", "D"}, {"C", "D"}),
    ],
)
def test_update_view_visual(
    pretty_mw,
    similar: bool,
    old_pos: int,
    current_pos: int,
    expected_pos: int,
    ref_expanded: Set[str],
    current_expanded: Set[str],
    expected_expanded: Set[str],
):
    old_model = MagicMock()
    old_model.is_similar.return_value = similar
    old_model.scroll_position = old_pos
    old_model.expanded = ref_expanded
    with patch("chartify.ui.main_window.MainWindow.current_view") as current_view:
        current_view.source_model.scroll_position = current_pos
        current_view.source_model.expanded = current_expanded
        current_view.view_type = "tree"
        var = VariableData("Temperature", "Zone A", "C")
        pretty_mw.update_view_visual(
            selected=[var], scroll_to=var, old_model=old_model, hide_source_units=False
        )
        current_view.update_appearance.assert_called_with(
            widths={"fixed": 60, "interactive": 200},
            header=["type", "key", "proxy_units", "units"],
            filter_tuple=FilterTuple(key="", type="", proxy_units=""),
            expanded=expected_expanded,
            selected=[var],
            scroll_pos=expected_pos,
            scroll_to=var,
            hide_source_units=False,
        )


@pytest.mark.parametrize(
    "is_simple,enabled, rate_to_energy, rate_to_energy_enabled",
    [(True, False, True, True), (False, True, False, False)],
)
def test_on_table_change_requested(
    qtbot,
    populated_mw: MainWindow,
    is_simple: bool,
    enabled: bool,
    rate_to_energy: bool,
    rate_to_energy_enabled: bool,
):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(populated_mw.setModelRequested):
            new_model = populated_mw.current_view.models["hourly"]
            new_model.is_simple = is_simple
            new_model.allow_rate_to_energy = rate_to_energy
            populated_mw.on_table_change_requested("hourly")
            assert mock_settings.TABLE_NAME == "hourly"
            assert populated_mw.tree_act.isEnabled() == enabled
            assert populated_mw.expand_all_act.isEnabled() == enabled
            assert populated_mw.collapse_all_act.isEnabled() == enabled
            assert populated_mw.toolbar.rate_energy_btn.isEnabled() == rate_to_energy_enabled


def test_on_table_change_requested_same_table(qtbot, populated_mw: MainWindow):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(populated_mw.updateModelRequested):
            populated_mw.on_table_change_requested("daily")
            assert mock_settings.TABLE_NAME == "daily"


def test_on_tab_changed(populated_mw: MainWindow, eso_file: EsoFile):
    models = ViewModel.models_from_file(eso_file, tree_node="type")
    models.pop("runperiod")  # delete so models are not identical
    populated_mw.add_treeview(1, "new file", models)
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        mock_settings.TABLE_NAME = "daily"
        populated_mw.standard_tab_wgt.setCurrentIndex(1)
        assert mock_settings.CURRENT_FILE_ID == 1
        assert mock_settings.TABLE_NAME == "daily"
        button_names = [btn.text() for btn in populated_mw.toolbar.table_buttons]
        assert button_names == ["hourly", "daily", "monthly"]


def test_on_tab_changed_fresh(pretty_mw, eso_file: EsoFile):
    models = ViewModel.models_from_file(eso_file, tree_node="type")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        pretty_mw.add_treeview(0, "new file", models)
        mock_settings.TABLE_NAME = "hourly"
        assert mock_settings.CURRENT_FILE_ID == 0
        assert mock_settings.TABLE_NAME == "hourly"


def test_on_tab_changed_empty(populated_mw: MainWindow):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        populated_mw.standard_tab_wgt.removeTab(0)
        assert mock_settings.CURRENT_FILE_ID is None
        assert mock_settings.TABLE_NAME is None
        assert not populated_mw.remove_variables_act.isEnabled()
        assert not populated_mw.toolbar.all_files_btn.isEnabled()
        assert not populated_mw.toolbar.totals_outputs_btn.isEnabled()
        assert populated_mw.toolbar.rate_energy_btn.isEnabled()
        assert not populated_mw.toolbar.table_buttons
        assert not populated_mw.toolbar.table_group.layout().itemAt(0)


def test_on_tab_bar_double_clicked(qtbot, populated_mw: MainWindow):
    def cb(tab_index, id_):
        return tab_index == 0 and id_ == 0

    with qtbot.wait_signal(populated_mw.fileRenameRequested, check_params_cb=cb):
        populated_mw.on_tab_bar_double_clicked(0)


def test_on_tab_closed(populated_mw: MainWindow):
    populated_mw.standard_tab_wgt.removeTab(0)
    assert not populated_mw.toolbar.all_files_btn.isEnabled()
    assert not populated_mw.close_all_act.isEnabled()


def test_connect_tab_widget_close_requested(qtbot, pretty_mw):
    with qtbot.wait_signal(pretty_mw.fileRemoveRequested, check_params_cb=lambda x: x == 123):
        pretty_mw.standard_tab_wgt.closeTabRequested.emit(123)


def test_connect_tab_widget_current_changed(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_tab_changed") as func_mock:
        pretty_mw.standard_tab_wgt.currentChanged.emit(123)
        func_mock.assert_called_once_with(123)


def test_connect_tab_widget_tab_double_clicked(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_tab_bar_double_clicked") as func_mock:
        pretty_mw.standard_tab_wgt.tabRenameRequested.emit(123)
        func_mock.assert_called_once_with(123)


def test_connect_tab_widget_tab_closed(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_all_tabs_closed") as func_mock:
        pretty_mw.standard_tab_wgt.tabClosed.emit(123)
        func_mock.assert_called_once_with()


def test_connect_tab_widget_drop_btn_clicked(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.load_files_from_fs") as func_mock:
        pretty_mw.standard_tab_wgt.tab_wgt_button.click()
        func_mock.assert_called_once_with()


def test_on_totals_checked(qtbot, pretty_mw):
    pytest.fail()


def test_on_all_files_checked(pretty_mw):
    pytest.fail()


def test_table_change_requested(pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_table_change_requested") as func_mock:
        pretty_mw.toolbar.tableChangeRequested.emit("test")
        func_mock.assert_called_once_with("test")


def test_on_rate_energy_btn_checked(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(pretty_mw.updateModelRequested):
            pretty_mw.on_rate_energy_btn_checked(True)
            assert mock_settings.RATE_TO_ENERGY is True


def test_on_source_units_toggled(pretty_mw):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
            pretty_mw.on_source_units_toggled(True)
            assert mock_settings.HIDE_SOURCE_UNITS is False
            mock_view.hide_section.assert_called_once_with("units", False)


@pytest.mark.parametrize("allow_rate_to_energy,rate_to_energy", [(True, True), (False, False)])
def test_on_custom_units_toggled(
    qtbot, populated_mw: MainWindow, allow_rate_to_energy: bool, rate_to_energy: bool
):
    populated_mw.current_view.source_model.allow_rate_to_energy = allow_rate_to_energy
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(populated_mw.updateModelRequested):
            populated_mw.on_custom_units_toggled("kBTU", "MW", "IP", True)
            assert mock_settings.ENERGY_UNITS == "kBTU"
            assert mock_settings.POWER_UNITS == "MW"
            assert mock_settings.UNITS_SYSTEM == "IP"
            assert mock_settings.RATE_TO_ENERGY is rate_to_energy
            assert populated_mw.toolbar.rate_energy_btn.isEnabled() is rate_to_energy


def test_on_energy_units_changed(qtbot, pretty_mw):
    act = QAction()
    act.setData("FOO")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(pretty_mw.updateModelRequested):
            pretty_mw.on_energy_units_changed(act)
            mock_settings.ENERGY_UNITS = "FOO"


def test_on_power_units_changed(qtbot, pretty_mw):
    act = QAction()
    act.setData("FOO")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(pretty_mw.updateModelRequested):
            pretty_mw.on_power_units_changed(act)
            mock_settings.POWER_UNITS = "FOO"


def test_on_units_system_changed(qtbot, pretty_mw):
    act = QAction()
    act.setData("FOO")
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        with qtbot.wait_signal(pretty_mw.updateModelRequested):
            pretty_mw.on_units_system_changed(act)
            mock_settings.UNITS_SYSTEM = "FOO"


def test_connect_totals_btn(qtbot, pretty_mw):
    pretty_mw.toolbar.totals_outputs_btn.setEnabled(True)
    with patch("chartify.ui.main_window.MainWindow.on_totals_checked") as mock_func:
        qtbot.mouseClick(pretty_mw.toolbar.totals_outputs_btn, Qt.LeftButton)
        mock_func.assert_called_once_with(True)


def test_connect_all_files_btn(qtbot, pretty_mw):
    pretty_mw.toolbar.all_files_btn.setEnabled(True)
    with patch("chartify.ui.main_window.MainWindow.on_all_files_toggled") as mock_func:
        qtbot.mouseClick(pretty_mw.toolbar.all_files_btn, Qt.LeftButton)
        mock_func.assert_called_once_with(True)


def test_connect_tableChangeRequested(pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_table_change_requested") as mock_func:
        pretty_mw.toolbar.tableChangeRequested.emit("foo")
        mock_func.assert_called_once_with("foo")


def test_connect_customUnitsToggled(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_custom_units_toggled") as mock_func:
        pretty_mw.toolbar.customUnitsToggled.emit("foo", "bar", "baz", True)
        mock_func.assert_called_once_with("foo", "bar", "baz", True)


def test_connect_source_units_toggle(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_source_units_toggled") as mock_func:
        pretty_mw.toolbar.source_units_toggle.stateChanged.emit(True)
        mock_func.assert_called_once_with(True)


def test_connect_rate_energy_btn(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_rate_energy_btn_checked") as mock_func:
        qtbot.mouseClick(pretty_mw.toolbar.rate_energy_btn, Qt.LeftButton)
        mock_func.assert_called_once_with(True)


def test_connect_energy_btn(pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_energy_units_changed") as mock_func:
        act = pretty_mw.toolbar.energy_btn.menu().actions()[0]
        act.trigger()
        mock_func.assert_called_once_with(act)


def test_connect_power_btn(pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_power_units_changed") as mock_func:
        act = pretty_mw.toolbar.power_btn.menu().actions()[0]
        act.trigger()
        mock_func.assert_called_once_with(act)


def test_connect_units_system_button(pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_units_system_changed") as mock_func:
        act = pretty_mw.toolbar.units_system_button.menu().actions()[0]
        act.trigger()
        mock_func.assert_called_once_with(act)


def test_connect_rate_energy_toggle(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_rate_energy_btn_checked") as func_mock:
        qtbot.mouseClick(pretty_mw.toolbar.rate_energy_btn, Qt.LeftButton)
        func_mock.assert_called_once_with(True)


@pytest.mark.parametrize("checked,tree_node", [(True, "type"), (False, None)])
def test_on_tree_btn_toggled(qtbot, pretty_mw, checked: bool, tree_node: Optional[str]):
    with patch("chartify.ui.main_window.Settings") as mock_settings:
        pretty_mw.tree_act.setChecked(not checked)
        with qtbot.wait_signal(pretty_mw.updateModelRequested):
            qtbot.mouseClick(pretty_mw.tree_view_btn, Qt.LeftButton)
            assert pretty_mw.tree_act.isChecked() is checked
            assert pretty_mw.collapse_all_btn.isEnabled() is checked
            assert pretty_mw.expand_all_btn.isEnabled() is checked
            assert mock_settings.TREE_NODE == tree_node


def test_on_text_edited(qtbot, populated_mw: MainWindow):
    def cb():
        mock_view.filter_view.assert_called_once_with(FilterTuple("foo", "bar", "baz"))
        return True

    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        qtbot.wait_signal(populated_mw.timer.timeout, check_params_cb=cb)
        qtbot.keyClicks(populated_mw.key_line_edit, "foo")
        qtbot.keyClicks(populated_mw.type_line_edit, "bar")
        qtbot.keyClicks(populated_mw.units_line_edit, "baz")

    assert populated_mw.key_line_edit.text() == "foo"
    assert populated_mw.type_line_edit.text() == "bar"
    assert populated_mw.units_line_edit.text() == "baz"
    assert populated_mw.get_filter_tuple() == FilterTuple("foo", "bar", "baz")


def test_on_filter_timeout_empty(pretty_mw):
    pretty_mw.key_line_edit.setText("foo")
    pretty_mw.type_line_edit.setText("bar")
    pretty_mw.units_line_edit.setText("baz")
    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        pretty_mw.on_filter_timeout()
        assert not mock_view.filter_view.called


def test_on_filter_timeout(populated_mw: MainWindow):
    populated_mw.key_line_edit.setText("foo")
    populated_mw.type_line_edit.setText("bar")
    populated_mw.units_line_edit.setText("baz")
    with patch("chartify.ui.main_window.MainWindow.current_view") as mock_view:
        populated_mw.on_filter_timeout()
        mock_view.filter_view.assert_called_once_with(FilterTuple("foo", "bar", "baz"))


def test_connect_type_line_edit(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_text_edited") as mock_func:
        qtbot.keyClicks(pretty_mw.type_line_edit, "foo")
        mock_func.assert_called_with()


def test_connect_key_line_edit(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_text_edited") as mock_func:
        qtbot.keyClicks(pretty_mw.key_line_edit, "foo")
        mock_func.assert_called_with()


def test_connect_units_line_edit(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_filter_timeout") as mock_func:
        pretty_mw.timer.timeout.emit()
        mock_func.assert_called_once_with()


def test_connect_timer(qtbot, pretty_mw):
    with patch("chartify.ui.main_window.MainWindow.on_filter_timeout") as mock_func:
        pretty_mw.timer.timeout.emit()
        mock_func.assert_called_once_with()


@pytest.mark.parametrize("confirmed,expected", [(0, None), (1, "test")])
def test_confirm_rename_file(pretty_mw, confirmed: int, expected: Optional[str]):
    with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "test"
        out = pretty_mw.confirm_rename_file("test", ["foo", "bar"])
        dialog.assert_called_once_with(
            pretty_mw,
            title="Enter a new file name.",
            input1_name="Name",
            input1_text="test",
            input1_blocker=["foo", "bar"],
        )
        assert out == expected


@pytest.mark.parametrize("confirmed,expected", [(0, False), (1, True)])
def test_confirm_remove_variables(pretty_mw, confirmed: int, expected: bool):
    with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "test"
        out = pretty_mw.confirm_remove_variables([Variable("T", "A", "B", "C")], False, "foo")
        dialog.assert_called_once_with(
            pretty_mw, "Delete following variables from file 'foo': ", det_text="A | B | C"
        )
        assert out == expected


@pytest.mark.parametrize("confirmed,expected", [(0, None), (1, ("renamed", None))])
def test_confirm_rename_variable_simple_variable(
    pretty_mw, confirmed: int, expected: Optional[Tuple[str, None]]
):
    with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "renamed"
        out = pretty_mw.confirm_rename_variable("test", None)
        dialog.assert_called_once_with(
            pretty_mw, title="Rename variable:", input1_name="Key", input1_text="test",
        )
        assert out == expected


@pytest.mark.parametrize("confirmed,expected", [(0, None), (1, ("renamed1", "renamed2"))])
def test_confirm_rename_variable(
    pretty_mw, confirmed: int, expected: Optional[Tuple[str, None]]
):
    with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "renamed1"
        instance.input2_text = "renamed2"
        out = pretty_mw.confirm_rename_variable("test1", "test2")
        dialog.assert_called_once_with(
            pretty_mw,
            title="Rename variable:",
            input1_name="Key",
            input1_text="test1",
            input2_name="Type",
            input2_text="test2",
        )
        assert out == expected


@pytest.mark.parametrize(
    "confirmed,expected,variables,key",
    [
        (0, None, [SimpleVariable("T", "A", "D"), SimpleVariable("T", "A", "D")], "A - sum",),
        (
            1,
            ("New KEY", None),
            [SimpleVariable("T", "A", "D"), SimpleVariable("T", "B", "D")],
            "Custom Key - sum",
        ),
    ],
)
def test_confirm_aggregate_variables_simple_variables(
    pretty_mw,
    confirmed: int,
    expected: Optional[Tuple[str, None]],
    variables: List[SimpleVariable],
    key: str,
):
    with patch("chartify.ui.main_window.SingleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "New KEY"
        out = pretty_mw.confirm_aggregate_variables(variables, "sum")
        dialog.assert_called_once_with(
            pretty_mw,
            title="Enter details of the new variable:",
            input1_name="Key",
            input1_text=key,
        )
        assert out == expected


@pytest.mark.parametrize(
    "confirmed,expected,variables,key,type_",
    [
        (
            0,
            None,
            [Variable("T", "A", "B", "C"), Variable("T", "A", "B", "C")],
            "A - sum",
            "B",
        ),
        (
            1,
            ("New KEY", "New TYPE"),
            [Variable("T", "A", "E", "C"), Variable("T", "B", "F", "C")],
            "Custom Key - sum",
            "Custom Type",
        ),
    ],
)
def test_confirm_aggregate_variables(
    pretty_mw,
    confirmed: int,
    expected: Optional[Tuple[str, None]],
    variables: List[Variable],
    key: str,
    type_: str,
):
    with patch("chartify.ui.main_window.DoubleInputDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        instance.input1_text = "New KEY"
        instance.input2_text = "New TYPE"
        out = pretty_mw.confirm_aggregate_variables(variables, "sum")
        dialog.assert_called_once_with(
            pretty_mw,
            title="Enter details of the new variable:",
            input1_name="Key",
            input1_text=key,
            input2_name="Type",
            input2_text=type_,
        )
        assert out == expected


@pytest.mark.parametrize("confirmed,expected", [(0, False), (1, True)])
def test_confirm_delete_file(pretty_mw, confirmed: int, expected: bool):
    with patch("chartify.ui.main_window.ConfirmationDialog") as dialog:
        instance = dialog.return_value
        instance.exec_.return_value = confirmed
        out = pretty_mw.confirm_delete_file("FOO")
        assert out is expected
