from typing import List, Any, Optional

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
    block_list : list
        A check list used to check for disallowed input.

    """

    def __init__(self, parent, title: str, block_list: Optional[List[Any]] = None):
        super().__init__(parent, Qt.FramelessWindowHint)
        self.block_list = [] if not block_list else block_list
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

    def verify_input(self):
        """ Check if dialog data input is allowed. """
        pass


class RenameVariableDialog(BaseTwoButtonDialog):
    """ Dialog to retrieve 'variable_name' input from user. """

    def __init__(self, parent, title: str, variable_name: str):
        super().__init__(parent, title)
        form = QWidget(self)
        self.form_layout = QFormLayout(form)
        self.content_layout.addWidget(form)

        self.variable_name_input = QLineEdit(self)
        self.variable_name_input.setText(variable_name)
        self.variable_name_input.setCursorPosition(0)
        self.variable_name_input.textChanged.connect(self.verify_input)
        self.form_layout.addRow("Variable", self.variable_name_input)

    @property
    def variable_name(self):
        return self.variable_name_input.text().strip()

    def verify_input(self):
        self.ok_btn.setEnabled(bool(self.variable_name))


class RenameKeyVariableDialog(RenameVariableDialog):
    """ Dialog to retrieve 'variable_name' and 'key_name' inputs from user. """

    def __init__(self, parent, title: str, variable_name: str, key_name: str):
        super().__init__(parent, title, variable_name)
        self.key_name_input = QLineEdit(self)
        self.key_name_input.setText(key_name)
        self.key_name_input.setCursorPosition(0)
        self.key_name_input.textChanged.connect(self.verify_input)
        self.form_layout.addRow("Key", self.key_name_input)

    @property
    def key_name(self):
        return self.key_name_input.text().strip()

    def verify_input(self):
        self.ok_btn.setEnabled(bool(self.key_name) and bool(self.variable_name))


class MulInputDialog(QDialog):
    """
    Dialog to allow user to specify text inputs.

    Values defined in check list will be forbidden
    from the input, i.e. the dialog will be blocked
    from confirming.

    Arbitrary number of rows can be defined as
    k, v pairs using **kwargs.

    QLineEdits can be accessed from the 'inputs'
    attribute.

    """

    def __init__(self, parent, text, check_list=None, **kwargs):
        super().__init__(parent, Qt.FramelessWindowHint)
        self.line_edits = {}
        self.check_list = [] if check_list is None else check_list

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        main_text = QLabel(self)
        main_text.setText(text)
        main_text.setProperty("primary", True)
        layout.addWidget(main_text)

        form = QWidget(self)
        form_layout = QFormLayout(form)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(form)

        box = TwoButtonBox(self)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout.addWidget(box)

        for k, v in kwargs.items():
            inp = QLineEdit(self)
            inp.textChanged.connect(self.verify_input)
            self.line_edits[k] = inp
            inp.setText(v)
            inp.setCursorPosition(0)

            form_layout.addRow(k, inp)

    def get_input(self, key):
        """ Return an input text of specified input. """
        try:
            return self.get_inputs_dct()[key]
        except KeyError:
            raise KeyError(f"Invalid dialog input '{key}' requested!")

    def get_inputs_dct(self):
        """ Return an input text of all the inputs. """
        return {k: v.text() for k, v in self.line_edits.items()}

    def get_inputs_vals(self):
        """ Return current input text. """
        return [v.text() for v in self.line_edits.values()]

    def verify_input(self):
        """ Check if the line text is applicable. """
        vals = self.get_inputs_vals()

        if any(map(lambda x: not x or not x.strip(), vals)):
            # one or more inputs is empty
            self.ok_btn.setEnabled(False)

        elif any(map(lambda x: x.strip() in self.check_list, vals)):
            self.ok_btn.setEnabled(False)

        else:
            if not self.ok_btn.isEnabled():
                self.ok_btn.setEnabled(True)


class ConfirmationDialog(QDialog):
    """
    A custom dialog to confirm user actions.

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
