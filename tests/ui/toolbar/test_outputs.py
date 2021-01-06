from PySide2.QtCore import Qt


def test_output_types(qtbot, mw):
    expected = [mw.standard_tab_wgt, mw.totals_tab_wgt, mw.diff_tab_wgt]
    buttons = [
        mw.toolbar.standard_outputs_btn,
        mw.toolbar.totals_outputs_btn,
        mw.toolbar.diff_outputs_btn,
    ]
    for i in range(mw.output_stacked_widget.count()):
        qtbot.mouseClick(buttons[i], Qt.LeftButton)
        assert mw.current_tab_widget is expected[i]


def test_change_output_type(qtbot, mw_esofile):
    qtbot.mouseClick(mw_esofile.toolbar.totals_outputs_btn, Qt.LeftButton)
    assert mw_esofile.close_all_act.isEnabled()


def test_change_output_type_empty(qtbot, mw_esofile):
    qtbot.mouseClick(mw_esofile.toolbar.diff_outputs_btn, Qt.LeftButton)
    assert not mw_esofile.close_all_act.isEnabled()
