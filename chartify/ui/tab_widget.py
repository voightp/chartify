from typing import List

from PySide2.QtCore import Signal
from PySide2.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QTabWidget,
    QToolButton,
)

from chartify.ui.treeview import TreeView


class TabWidget(QTabWidget):
    """ Tab widget which displays information button when empty. """

    tabClosed = Signal(int)

    def __init__(self, parent, button: QToolButton):
        super().__init__(parent)
        self.setUsesScrollButtons(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setTabPosition(QTabWidget.North)

        layout = QHBoxLayout(self)
        self.tab_wgt_button = button
        layout.addWidget(self.tab_wgt_button)

    def tabRemoved(self, index: int) -> None:
        if self.is_empty():
            self.tab_wgt_button.setVisible(True)
        self.tabClosed.emit(index)

    def is_empty(self) -> bool:
        """ Check if there's at least one loaded file. """
        return self.count() <= 0

    def get_all_children(self) -> List[QWidget]:
        return [self.widget(i) for i in range(self.count())]

    def get_all_child_names(self) -> List[str]:
        return [self.tabText(i) for i in range(self.count())]

    def add_tab(self, tree_view: TreeView, title: str) -> None:
        if self.is_empty():
            self.tab_wgt_button.setVisible(False)
        self.addTab(tree_view, title)
