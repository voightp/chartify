from PySide2.QtWidgets import (QSizePolicy, QLineEdit, QHBoxLayout, QTabWidget,
                               QToolButton, QDialog, QFormLayout, QVBoxLayout,
                               QDialogButtonBox, QWidget, QApplication,
                               QPushButton, QMessageBox, QTextEdit, QLabel)
from PySide2.QtCore import Qt, QFileInfo, Signal, QSize
from PySide2.QtWidgets import QFrame
from PySide2.QtGui import QPixmap, QIcon
from esopie.view_widget import View


def update_appearance(wgt):
    """ Refresh CSS of the widget. """
    wgt.style().unpolish(wgt)
    wgt.style().polish(wgt)


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
    tabClosed = Signal(View)
    fileLoadRequested = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setUsesScrollButtons(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setTabPosition(QTabWidget.North)

        layout = QHBoxLayout(self)
        self.drop_btn = QToolButton(self)
        self.drop_btn.setObjectName("dropButton")
        self.drop_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.drop_btn.setText("Choose a file or drag it here!")
        self.drop_btn.setIcon(QPixmap("../icons/drop_file_grey.png"))
        self.drop_btn.setIconSize(QSize(50, 50))
        layout.addWidget(self.drop_btn)

        self.tabCloseRequested.connect(self.close_tab)
        self.drop_btn.clicked.connect(self.fileLoadRequested.emit)

    def is_empty(self):
        """ Check if there's at least one loaded file. """
        return self.count() <= 0

    def get_all_widgets(self):
        count = self.count()
        widgets = [self.widget(i) for i in range(count)]
        return widgets

    def get_current_widget(self):
        return self.currentWidget()

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

    def close_all_tabs(self):
        wgts = [self.widget(i) for i in range(self.count())]
        self.clear()
        self.drop_btn.setVisible(True)
        return wgts


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
        update_appearance(self)

    def dragLeaveEvent(self, event):
        """ Handle appearance when a drag event is leaving. """
        self.setProperty("drag-accept", "")
        update_appearance(self)

    def dropEvent(self, event):
        """ Handle file drops. """
        mime = event.mimeData()
        files = filter_eso_files(mime.urls())

        if files:
            # invoke load files
            self.fileDropped.emit(files)

        # update appearance
        self.setProperty("drag-accept", "")
        update_appearance(self)


# TODO this might not be necessary
# the reason behind this is that I'd like to find a way to hack cursor color
class LineEdit(QFrame):
    """
    A custom line edit to allow changing cursor color.

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


class MulInputDialog(QDialog):
    """
    Dialog to allow user to specify text inputs.

    Arbitrary number of rows can be defined as
    k, v pairs using **kwargs.

    QLineEdits can be accessed from the 'inputs'
    attribute.

    """

    def __init__(self, text, parent, **kwargs):
        super().__init__(parent, Qt.FramelessWindowHint)
        self.line_edits = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        main_text = QLabel(self)
        main_text.setText(text)
        main_text.setProperty("primary", "true")
        layout.addWidget(main_text)

        form = QWidget(self)
        form_layout = QFormLayout(form)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(form)

        box = QDialogButtonBox(self)
        self.ok_btn = QToolButton(self)  # TODO change colors
        self.ok_btn.setIcon(QIcon("../icons/check_black.png"))
        self.cancel_btn = QToolButton(self)
        self.cancel_btn.setIcon(QIcon("../icons/remove_grey.png"))
        box.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)
        box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

        for k, v in kwargs.items():
            inp = QLineEdit(self)
            inp.textChanged.connect(self.verify_input)
            self.line_edits[k] = inp
            inp.setText(v)

            form_layout.addRow(k, inp)

    def get_inputs_dct(self):
        """ Return current input text. """
        return {k: v.text() for k, v in self.line_edits.items()}

    def get_inputs_vals(self):
        """ Return current input text. """
        return [v.text() for v in self.line_edits.values()]

    def verify_input(self):
        """ Check if the line text is applicable. """
        vals = self.get_inputs_vals()
        if any(map(lambda x: not x or not x.strip(), vals)):
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
        main_text.setProperty("primary", "true")
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
        self.ok_btn = QToolButton(box)  # TODO change colors
        self.ok_btn.setIcon(QIcon("../icons/check_black.png"))
        self.cancel_btn = QToolButton(box)
        self.cancel_btn.setIcon(QIcon("../icons/remove_grey.png"))
        box.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)
        box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)
