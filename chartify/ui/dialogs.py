from typing import List

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget, QFormLayout, \
    QDialogButtonBox, QToolButton, QLineEdit, QTextEdit


class TwoButtonBox(QDialogButtonBox):
    """ Button box to hold 'Confirm' and 'Reject' buttons. """

    def __init__(self, parent: QDialog):
        super().__init__(parent)
        self.ok_btn = QToolButton(self)
        self.ok_btn.setObjectName("okButton")
        self.reject_btn = QToolButton(self)
        self.reject_btn.setObjectName("rejectButton")
        self.addButton(self.reject_btn, QDialogButtonBox.RejectRole)
        self.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)


class BaseTwoButtonDialog(QDialog):
    """ Base dialog with custom adn reject function.

    Content should be added into 'content_layout'. Dialog
    always shows a title.

    Attributes
    ----------
    parent : QWidget
        A dialog parent widget.
    title: str
        Main text appearing on the dialog.

    """

    def __init__(self, parent, title: str):
        super().__init__(parent, Qt.FramelessWindowHint)
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel(self)
        self.title.setText(title)
        self.title.setObjectName("dialogTitle")
        layout.addWidget(self.title)

        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_widget)

        self.button_box = TwoButtonBox(self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    @property
    def ok_btn(self):
        return self.button_box.ok_btn

    @property
    def reject_btn(self):
        return self.button_box.reject_btn


class SingleInputDialog(BaseTwoButtonDialog):
    """ Dialog to retrieve a single text input from user. """

    def __init__(
            self,
            parent,
            title: str,
            input1_name: str,
            input1_text: str,
            input1_blocker: List[str] = None
    ):
        super().__init__(parent, title)
        form = QWidget(self)
        self.input1_blocker = input1_blocker if input1_blocker else []
        self.form_layout = QFormLayout(form)
        self.content_layout.addWidget(form)

        self.input1 = QLineEdit(self)
        self.input1.setText(input1_text)
        self.input1.setCursorPosition(0)
        self.input1.textChanged.connect(self.verify_input)
        self.form_layout.addRow(input1_name, self.input1)

    @property
    def input1_text(self) -> str:
        return self.input1.text().strip()

    def verify_input(self) -> bool:
        valid = bool(self.input1_text) and self.input1_text not in self.input1_blocker
        self.ok_btn.setEnabled(valid)
        return valid


class DoubleInputDialog(SingleInputDialog):
    """ Dialog to retrieve two text inputs from user. """

    def __init__(
            self,
            parent,
            title: str,
            input1_name: str,
            input1_text: str,
            input2_name: str,
            input2_text: str,
            input1_blocker: List[str] = None,
            input2_blocker: List[str] = None
    ):
        super().__init__(parent, title, input1_name, input1_text, input1_blocker)
        self.input2_blocker = input2_blocker if input2_blocker else []
        self.input2 = QLineEdit(self)
        self.input2.setText(input2_text)
        self.input2.setCursorPosition(0)
        self.input2.textChanged.connect(self.verify_input)
        self.form_layout.addRow(input2_name, self.input2)

    @property
    def input2_text(self) -> str:
        return self.input2.text().strip()

    def verify_input(self) -> bool:
        valid1 = super().verify_input()
        valid2 = bool(self.input2_text) and self.input2_text not in self.input2_blocker
        valid = valid1 and valid2
        self.ok_btn.setEnabled(valid)
        return valid


class ConfirmationDialog(QDialog):
    """ A custom dialog to confirm user actions.

    The dialog works as QMessageBox with a bit
    more available customization.

    """

    def __init__(self, parent, text, inf_text=None, det_text=None):
        super().__init__(parent, Qt.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        main_text = QLabel(self)
        main_text.setText(text)
        main_text.setProperty("primary", True)
        layout.addWidget(main_text)

        if inf_text:
            label = QLabel(self)
            label.setText(inf_text)
            layout.addWidget(label)

        if det_text:
            area = QTextEdit(self)
            area.setText(det_text)
            area.setLineWrapMode(QTextEdit.NoWrap)
            area.setTextInteractionFlags(Qt.NoTextInteraction)
            layout.addWidget(area)

        box = QDialogButtonBox(self)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout.addWidget(box)
