from pathlib import Path

import pytest
from PySide2.QtCore import QCoreApplication, Qt, QMimeData, QUrl
from PySide2.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide2.QtWidgets import QWidget

from chartify.ui.misc_widgets import TabWidget, DropFrame
from tests import ROOT


class TestTabWidget:
    @pytest.fixture()
    def tab_widget(self, qtbot):
        tab_widget = TabWidget(None)
        tab_widget.show()
        qtbot.add_widget(tab_widget)
        return tab_widget

    def test_init(self, tab_widget: TabWidget):
        assert tab_widget.usesScrollButtons
        assert tab_widget.tabsClosable()
        assert tab_widget.isMovable()
        assert tab_widget.tabPosition() == TabWidget.North
        assert tab_widget.drop_btn.objectName() == "dropButton"
        assert tab_widget.drop_btn.text() == "Choose a file or drag it here!"

    def test_is_empty(self, tab_widget: TabWidget):
        assert tab_widget.drop_btn.isVisible()
        assert tab_widget.is_empty()

    def test_get_all_children(self, tab_widget: TabWidget):
        widgets = []
        for i in range(3):
            wgt = QWidget(tab_widget)
            tab_widget.add_tab(wgt, str(i))
            widgets.append(wgt)
        assert tab_widget.get_all_children() == widgets

    def test_get_all_child_names(self, tab_widget: TabWidget):
        widgets = []
        for i in range(3):
            wgt = QWidget(tab_widget)
            tab_widget.add_tab(wgt, str(i))
            widgets.append(wgt)
        assert tab_widget.get_all_child_names() == ["0", "1", "2"]

    def test_add_tab(self, tab_widget: TabWidget):
        wgt = QWidget(tab_widget)
        tab_widget.add_tab(wgt, "test widget")
        assert tab_widget.widget(0) == wgt
        assert tab_widget.tabText(0) == "test widget"
        assert not tab_widget.drop_btn.isVisible()

    def test_close_tab_invisible_button(self, tab_widget: TabWidget):
        widgets = []
        for i in range(3):
            wgt = QWidget(tab_widget)
            tab_widget.add_tab(wgt, str(i))
            widgets.append(wgt)
        tab_widget.removeTab(0)
        assert not tab_widget.widget(2)
        assert not tab_widget.drop_btn.isVisible()

    def test_close_tab_visible_button(self, tab_widget: TabWidget):
        wgt = QWidget(tab_widget)
        tab_widget.add_tab(wgt, "test widget")
        tab_widget.removeTab(0)
        assert tab_widget.drop_btn.isVisible()


class TestDropFrame:
    @pytest.fixture(autouse=True)
    def drop_frame(self, qtbot):
        drop_frame = DropFrame(None, extensions=[".eso", ".xlsx"])
        drop_frame.show()
        qtbot.add_widget(drop_frame)
        return drop_frame

    def test_init(self, drop_frame: DropFrame):
        assert drop_frame.acceptDrops()
        assert drop_frame.hasMouseTracking()

    def test_dragEnterEvent(self, drop_frame: DropFrame):
        mime = QMimeData()
        mime.setUrls([QUrl("file://C:/dummy/path.eso")])
        mime.setText("HELLO FROM CHARTIFY")
        event = QDragEnterEvent(
            drop_frame.pos(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        QCoreApplication.sendEvent(drop_frame, event)
        assert drop_frame.property("drag-accept")

    def test_dragEnterEvent_invalid_ext(self, drop_frame: DropFrame):
        mime = QMimeData()
        mime.setUrls([QUrl("file://C:/dummy/path.invalid")])
        mime.setText("HELLO FROM CHARTIFY")
        event = QDragEnterEvent(
            drop_frame.pos(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        QCoreApplication.sendEvent(drop_frame, event)
        assert not drop_frame.property("drag-accept")

    def test_dragEnterEvent_leave(self, drop_frame: DropFrame):
        mime = QMimeData()
        mime.setUrls([QUrl("file://C:/dummy/path.eso")])
        mime.setText("HELLO FROM CHARTIFY")
        event = QDragEnterEvent(
            drop_frame.pos(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        QCoreApplication.sendEvent(drop_frame, event)
        assert drop_frame.property("drag-accept")

        event = QDragLeaveEvent()
        QCoreApplication.sendEvent(drop_frame, event)
        assert drop_frame.property("drag-accept") == ""

    def test_dropEvent(self, qtbot, drop_frame: DropFrame):
        paths = [Path(ROOT, "eso_files", "simple_view.xlsx")]
        urls = ["file:" + str(p) for p in paths]
        mime = QMimeData()
        mime.setUrls(urls)
        mime.setText("HELLO FROM CHARTIFY")

        drag_event = QDragEnterEvent(
            drop_frame.pos(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )
        QCoreApplication.sendEvent(drop_frame, drag_event)

        drop_event = QDropEvent(
            drop_frame.pos(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier
        )

        def cb(a):
            print(a)
            return a == paths

        with qtbot.wait_signal(drop_frame.fileDropped, check_params_cb=cb):
            QCoreApplication.sendEvent(drop_frame, drop_event)
        assert drop_frame.property("drag-accept") == ""
