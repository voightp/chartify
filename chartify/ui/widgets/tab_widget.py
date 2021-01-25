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
    currentTabChanged = Signal(QTabWidget, QWidget, QWidget)
    tabRenameRequested = Signal(QTabWidget, int)

    def __init__(self, parent, button: QToolButton):
        super().__init__(parent)
        self.tab_wgt_button = button
        self._previous_widget = None

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
        elif self._previous_widget is None:
            self.tab_wgt_button.setVisible(False)
        current_widget = self.widget(index)
        if current_widget is not self._previous_widget:
            self.currentTabChanged.emit(self, self._previous_widget, current_widget)
            self._previous_widget = current_widget

    def set_next_tab_before_delete(self, tab_index: int) -> None:
        if self.currentIndex() == tab_index:
            if tab_index == 0:
                next_index = tab_index + 1
            else:
                next_index = tab_index - 1
            self.setCurrentIndex(next_index)

    def remove_last_tab(self) -> int:
        last_index = self.count() - 1
        stacked_widget = self.widget(last_index)
        self.removeTab(last_index)
        file_id = stacked_widget.file_id
        stacked_widget.deleteLater()
        return file_id
