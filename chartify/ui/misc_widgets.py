from PySide2.QtCore import Qt, QFileInfo, Signal
from PySide2.QtWidgets import (
    QSizePolicy,
    QLineEdit,
    QHBoxLayout,
    QTabWidget,
    QToolButton,
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QDialogButtonBox,
    QWidget,
    QTextEdit,
    QLabel,
    QFrame,
)

from chartify.ui.treeview import TreeView
from chartify.utils.utils import refresh_css


def filter_eso_files(urls, extensions=("eso",)):
    """ Return a list of file paths with given extensions. """
    files = []
    for url in urls:
        f = url.toLocalFile()
        info = QFileInfo(f)
        if info.suffix() in extensions:
            files.append(f)
    return files


class TabWidget(QTabWidget):
    tabClosed = Signal(TreeView)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setUsesScrollButtons(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setTabPosition(QTabWidget.North)

        layout = QHBoxLayout(self)
        self.drop_btn = QToolButton(self)
        self.drop_btn.setObjectName("dropButton")
        self.drop_btn.setText("Choose a file or drag it here!")
        layout.addWidget(self.drop_btn)

        self.tabCloseRequested.connect(self.close_tab)

    def is_empty(self):
        """ Check if there's at least one loaded file. """
        return self.count() <= 0

    def get_all_children(self):
        return [self.widget(i) for i in range(self.count())]

    def get_all_child_names(self):
        return [self.tabText(i) for i in range(self.count())]

    def add_tab(self, wgt, title):
        if self.is_empty():
            self.drop_btn.setVisible(False)

        self.addTab(wgt, title)

    def close_tab(self, index):
        wgt = self.widget(index)
        self.removeTab(index)

        if self.is_empty():
            self.drop_btn.setVisible(True)

        self.tabClosed.emit(wgt)


class DropFrame(QFrame):
    """
    A custom frame accepting .eso file drops.

    Works together with custom .css to allow
    changing colours based on file extension.

    """

    fileDropped = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def dragEnterEvent(self, event):
        """ Handle appearance when a drag event is entering. """
        mime = event.mimeData()

        if not mime.hasUrls():
            return

        event.acceptProposedAction()
        files = filter_eso_files(mime.urls())

        # update appearance
        self.setProperty("drag-accept", bool(files))
        refresh_css(self)

    def dragLeaveEvent(self, event):
        """ Handle appearance when a drag event is leaving. """
        self.setProperty("drag-accept", "")
        refresh_css(self)

    def dropEvent(self, event):
        """ Handle file drops. """
        mime = event.mimeData()
        files = filter_eso_files(mime.urls())

        if files:
            # invoke load files
            self.fileDropped.emit(files)

        # update appearance
        self.setProperty("drag-accept", "")
        refresh_css(self)


class LineEdit(QFrame):
    """
    A custom line edit to allow changing cursor color.

    Which is not working!

    """

    textEdited = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.line_edit = QLineEdit(self)
        self.line_edit.textEdited.connect(self.on_text_change)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.line_edit)

    def on_text_change(self):
        """ Trigger textEdited signal. """
        self.textEdited.emit()

    def text(self):
        """ Get str content. """
        return self.line_edit.text()

    def setPlaceholderText(self, text):
        """ Set LineEdit placeholder text. """
        self.line_edit.setPlaceholderText(text)

    def placeholderText(self):
        """ Get placeholderText attribute. """
        return self.line_edit.placeholderText()


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
