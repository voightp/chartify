from pathlib import Path

import pytest
from PySide2.QtCore import Qt, QTimer
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QDialog, QDialogButtonBox

from chartify.ui.dialogs import (
    TwoButtonBox,
    BaseTwoButtonDialog,
    SingleInputDialog,
    DoubleInputDialog,
)
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
        dialog = BaseTwoButtonDialog(None, "Test title")
        qtbot.add_widget(dialog)
        return dialog

    def test_dialog_init(self, dialog: BaseTwoButtonDialog):
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


class TestSingleInputDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        dialog = SingleInputDialog(
            None, "Test title", "Some variable", "Some variable text", ["a", "b", "c"]
        )
        qtbot.add_widget(dialog)
        return dialog

    def test_dialog_init(self, dialog: SingleInputDialog):
        assert dialog.form_layout.itemAt(0).widget().text() == "Some variable"
        assert dialog.input1_text == "Some variable text"

    def test_valid_variable_input1(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input1.textChanged):
            dialog.input1.clear()
            qtbot.keyClicks(dialog.input1, "New variable")
        assert dialog.ok_btn.isEnabled()
        assert dialog.input1_text == "New variable"

    def test_invalid_variable_input1(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input1.textChanged):
            dialog.input1.clear()
            qtbot.keyClicks(dialog.input1, " ")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.input1_text == ""

    def test_blocker(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input1.textChanged):
            dialog.input1.clear()
            qtbot.keyClicks(dialog.input1, "a")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.input1_text == "a"


class TestDoubleInputDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        dialog = DoubleInputDialog(
            None,
            title="Test title",
            input1_name="Some variable",
            input1_text="Some variable text",
            input2_name="Some key",
            input2_text="Some key text",
            input2_blocker=["a", "b", "c"],
        )
        qtbot.add_widget(dialog)
        return dialog

    def test_dialog_init(self, dialog: SingleInputDialog):
        assert dialog.form_layout.itemAt(0).widget().text() == "Some variable"
        assert dialog.input1_text == "Some variable text"
        assert dialog.form_layout.itemAt(2).widget().text() == "Some key"
        assert dialog.input2_text == "Some key text"

    def test_valid_input2(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input2.textChanged):
            dialog.input2.clear()
            qtbot.keyClicks(dialog.input2, "New variable")
        assert dialog.ok_btn.isEnabled()
        assert dialog.input2_text == "New variable"

    def test_invalid_input2(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input2.textChanged):
            dialog.input2.clear()
            qtbot.keyClicks(dialog.input2, " ")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.input2_text == ""

    def test_blocker(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input2.textChanged):
            dialog.input2.clear()
            qtbot.keyClicks(dialog.input2, "a")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.input2_text == "a"

    def test_invalid_input1(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input1.textChanged):
            dialog.input1.clear()
            qtbot.keyClicks(dialog.input1, " ")
        assert not dialog.ok_btn.isEnabled()
        assert dialog.input1_text == ""

    def test_invalid_input1_and_input2(self, qtbot, dialog: SingleInputDialog):
        with qtbot.wait_signal(dialog.input1.textChanged):
            dialog.input1.clear()
            qtbot.keyClicks(dialog.input1, " ")
            dialog.input2.clear()
            qtbot.keyClicks(dialog.input1, " ")
        assert not dialog.ok_btn.isEnabled()
