from typing import List

from PySide2.QtCore import Signal
from PySide2.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QTabWidget,
    QToolButton,
)


class TabWidget(QTabWidget):
    """ Tab widget which displays information button when empty. """

    closeTabRequested = Signal(QTabWidget, int)
    currentTabChanged = Signal(QTabWidget, int, int)
    tabRenameRequested = Signal(QTabWidget, int)

    def __init__(self, parent, button: QToolButton):
        super().__init__(parent)
        self.tab_wgt_button = button
        self._previous_index = -1

        layout = QHBoxLayout(self)
        layout.addWidget(self.tab_wgt_button)

        self.setUsesScrollButtons(True)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setTabPosition(QTabWidget.North)

        self.currentChanged.connect(self.on_current_changed)
        self.tabCloseRequested.connect(lambda x: self.closeTabRequested.emit(self, x))
        self.tabBarDoubleClicked.connect(lambda x: self.tabRenameRequested.emit(self, x))

    @property
    def name(self) -> str:
        return self.tabText(self.currentIndex())

    def is_empty(self) -> bool:
        return self.count() <= 0

    def get_all_children(self) -> List[QWidget]:
        return [self.widget(i) for i in range(self.count())]

    def get_all_child_names(self) -> List[str]:
        return [self.tabText(i) for i in range(self.count())]

    def on_current_changed(self, index: int) -> None:
        if index == -1:
            self.tab_wgt_button.setVisible(True)
        elif self._previous_index == -1:
            self.tab_wgt_button.setVisible(False)
        self.currentTabChanged.emit(self, self._previous_index, index)
        self._previous_index = index

    def set_next_tab(self):
        if self.count() == 1:
            next_index = -1
        elif self.currentIndex() == 0:
            next_index = 1
        else:
            next_index = self.currentIndex() - 1
        self.setCurrentIndex(next_index)
