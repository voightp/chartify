from pathlib import Path

import pytest
from PySide2.QtCore import Qt, QTimer
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QDialog, QDialogButtonBox

from chartify.ui.dialogs import TwoButtonBox, BaseTwoButtonDialog, RenameVariableDialog, \
    RenameKeyVariableDialog
from chartify.utils.icon_painter import Pixmap
from tests import ROOT


@pytest.fixture(scope="module")
def icon1():
    path = Path(ROOT, "resources/icons/test.png")
    return QIcon(Pixmap(path))


@pytest.fixture(scope="module")
def icon2():
    path = Path(ROOT, "resources/icons/test.png")
    return QIcon(Pixmap(path, r=100, g=100, b=100, a=0.7))


class TestTwoButtonBox:
    def test_button_init(self, qtbot):
        dialog = QDialog(None)
        box = TwoButtonBox(dialog)
        qtbot.add_widget(dialog)
        assert box.buttonRole(box.ok_btn) == QDialogButtonBox.AcceptRole
        assert box.buttonRole(box.reject_btn) == QDialogButtonBox.RejectRole
        assert box.ok_btn.objectName() == "okButton"
        assert box.reject_btn.objectName() == "rejectButton"


class TestBaseTwoButtonDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        dialog = BaseTwoButtonDialog(None, "Test title", block_list=[1, 2, 3])
        qtbot.add_widget(dialog)
        return dialog

    def test_dialog_init(self, dialog: BaseTwoButtonDialog):
        assert dialog.block_list == [1, 2, 3]
        assert dialog.title.objectName() == "dialogTitle"

    def test_dialog_accept(self, qtbot, dialog: BaseTwoButtonDialog):
        def click_button():
            qtbot.mouseClick(dialog.button_box.ok_btn, Qt.LeftButton)

        QTimer().singleShot(100, click_button)
        assert dialog.exec_() == 1

    def test_dialog_reject(self, qtbot, dialog: BaseTwoButtonDialog):
        def click_button():
            qtbot.mouseClick(dialog.button_box.reject_btn, Qt.LeftButton)

        QTimer().singleShot(100, click_button)
        assert dialog.exec_() == 0


class TestRenameVariableDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        dialog = RenameVariableDialog(None, "Test title", "Some variable")
        qtbot.add_widget(dialog)
        return dialog

    def test_dialog_init(self, dialog: RenameVariableDialog):
        assert dialog.variable_name == "Some variable"

    def test_valid_variable_input(self, qtbot, dialog: RenameVariableDialog):
        with qtbot.wait_signal(dialog.variable_name_input.textChanged):
            dialog.variable_name_input.clear()
            qtbot.keyClicks(dialog.variable_name_input, "New variable")
        assert dialog.variable_name_input.isEnabled()
        assert dialog.variable_name == "New variable"

    def test_invalid_variable_input(self, qtbot, dialog: RenameVariableDialog):
        with qtbot.wait_signal(dialog.variable_name_input.textChanged):
            dialog.variable_name_input.clear()
            qtbot.keyClicks(dialog.variable_name_input, " ")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.variable_name == ""


class TestRenameKeyVariableDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        dialog = RenameKeyVariableDialog(None, "Test title", "Some variable", "Some key")
        qtbot.add_widget(dialog)
        return dialog

    def test_dialog_init(self, dialog: RenameKeyVariableDialog):
        assert dialog.variable_name == "Some variable"
        assert dialog.key_name == "Some key"

    def test_valid_variable_input(self, qtbot, dialog: RenameKeyVariableDialog):
        with qtbot.wait_signal(dialog.variable_name_input.textChanged):
            dialog.variable_name_input.clear()
            dialog.key_name_input.clear()
            qtbot.keyClicks(dialog.variable_name_input, "New variable")
            qtbot.keyClicks(dialog.key_name_input, "New key")
        assert dialog.variable_name_input.isEnabled()
        assert dialog.variable_name == "New variable"
        assert dialog.key_name == "New key"

    def test_invalid_key_input(self, qtbot, dialog: RenameKeyVariableDialog):
        with qtbot.wait_signal(dialog.key_name_input.textChanged):
            dialog.key_name_input.clear()
            qtbot.keyClicks(dialog.key_name_input, " ")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.key_name == ""
        assert dialog.variable_name == "Some variable"

    def test_invalid_variable_input(self, qtbot, dialog: RenameKeyVariableDialog):
        with qtbot.wait_signal(dialog.variable_name_input.textChanged):
            dialog.variable_name_input.clear()
            qtbot.keyClicks(dialog.variable_name_input, " ")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.variable_name == ""
