from typing import List, Dict

from PySide2.QtWidgets import QStackedWidget, QWidget

from chartify.ui.treeview import TreeView
from chartify.ui.treeview_model import ViewModel


class StackedWidget(QStackedWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)

    @property
    def current_treeview(self) -> TreeView:
        return self.currentWidget()

    @property
    def current_table_name(self) -> str:
        return self.currentWidget().source_model.name

    @property
    def all_view_models(self) -> List[ViewModel]:
        return [treeview.source_model for treeview in self.get_all_children()]

    @property
    def table_names(self) -> List[str]:
        return [model.name for model in self.all_view_models]

    @property
    def name_indexes(self) -> Dict[str, int]:
        name_index_pairs = {}
        for i in range(self.count()):
            treeview = self.widget(i)
            name = treeview.source_model.name
            name_index_pairs[name] = i
        return name_index_pairs

    @property
    def file_id(self) -> int:
        return self.widget(0).id_

    def get_all_children(self) -> List[QWidget]:
        return [self.widget(i) for i in range(self.count())]

    def get_treeview(self, name: str) -> TreeView:
        index = self.name_indexes[name]
        return self.widget(index)

    def get_view_model(self, name: str) -> ViewModel:
        return self.get_treeview(name).source_model

    def get_next_treeview(self, previous_file_widget: "StackedWidget") -> "StackedWidget":
        if (
            previous_file_widget is not None
            and previous_file_widget.current_table_name in self.table_names
        ):
            name = previous_file_widget.current_table_name
        else:
            name = self.current_table_name
        return self.get_treeview(name)

    def set_treeview(self, treeview: TreeView) -> None:
        index = self.indexOf(treeview)
        self.setCurrentIndex(index)
