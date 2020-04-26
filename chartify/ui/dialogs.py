from PySide2.QtCore import Qt
from PySide2.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget, QFormLayout, \
    QDialogButtonBox, QToolButton, QLineEdit, QTextEdit


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

        box = QDialogButtonBox(self)
        self.ok_btn = QToolButton(box)
        self.ok_btn.setObjectName("okButton")

        self.cancel_btn = QToolButton(box)
        self.cancel_btn.setObjectName("cancelButton")

        box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        box.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)
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
        main_text.setProperty("primary",True)
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

        self.ok_btn = QToolButton(box)
        self.ok_btn.setObjectName("okButton")

        self.cancel_btn = QToolButton(box)
        self.cancel_btn.setObjectName("cancelButton")

        box.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)
        box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout.addWidget(box)