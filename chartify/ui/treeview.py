from typing import Dict, List, Set, Sequence, Tuple

import pandas as pd
from PySide2.QtCore import (
    QItemSelection,
    QItemSelectionRange,
    Signal,
    QModelIndex,
    Qt
)
from PySide2.QtGui import QStandardItem
from PySide2.QtWidgets import QHeaderView

from chartify.ui.simpleview import SimpleView, SimpleFilterModel, SimpleViewModel
from chartify.utils.utils import FilterTuple, VariableData


class TreeViewModel(SimpleViewModel):
    def __init__(self):
        super().__init__()

    @staticmethod
    def _append_row(
            parent: QStandardItem,
            row: Sequence[str],
            item_row: List[QStandardItem],
            indexes: Dict[str, int]
    ) -> None:
        """ Append row to the given parent. """
        # assign status tip for all items in row
        key = row[indexes["key"]]
        variable = row[indexes["variable"]]
        proxy_units = row[indexes["units"]]
        source_units = row[indexes["source units"]]
        status_tip = f"{key} | {variable} | {proxy_units}"

        # show all the info for each item in row
        for item in item_row:
            item.setStatusTip(status_tip)

        # first item holds the variable data used for search
        item_row[0].setData(
            VariableData(
                key=key, variable=variable, units=source_units, proxyunits=proxy_units
            ),
            role=Qt.UserRole,
        )

        parent.appendRow(item_row)

    def append_tree_rows(self, variables_df: pd.DataFrame, indexes: Dict[str, int]) -> None:
        """ Add rows for a tree like view. """
        root = self.invisibleRootItem()
        grouped = variables_df.groupby(by=[variables_df.columns[0]])
        for parent, df in grouped:
            if len(df.index) == 1:
                self.append_plain_rows(df, indexes)
            else:
                parent_item = QStandardItem(parent)
                parent_item.setDragEnabled(False)
                root.appendRow(parent_item)
                for row in df.values:
                    # first standard item is empty to avoid
                    # having parent string in the child row
                    item_row = [QStandardItem("")]

                    # source units will not be displayed (last item)
                    for item in row[1:-1]:
                        item_row.append(QStandardItem(item))

                    self._append_row(parent_item, row, item_row, indexes)

    def populate_model(self, variables_df: pd.DataFrame, is_tree: bool) -> None:
        """  Create a model and set up its appearance. """
        columns = variables_df.columns.tolist()
        indexes = {
            "key": columns.index("key"),
            "variable": columns.index("variable"),
            "units": columns.index("units"),
            "source units": columns.index("source units"),
        }

        if not is_tree:
            # create plain table when tree structure not requested
            self.append_plain_rows(variables_df, indexes)
        else:
            self.append_tree_rows(variables_df, indexes)


class TreeFilterModel(SimpleFilterModel):
    def __init__(self):
        super().__init__()

    def get_logical_indexes(self) -> Dict[str, int]:
        """ Return logical positions of header labels. """
        names = self.get_logical_names()
        return {
            "key": names.index("key"),
            "variable": names.index("variable"),
            "units": names.index("units"),
        }

    def find_match(self, variables: List[VariableData], key: str) -> QItemSelection:
        """ Check if output variables are available in a new model. """

        def check_var():
            v = (var.key, var.variable)
            return v in test_variables

        selection = QItemSelection()
        test_variables = [(var.key, var.variable) for var in variables]

        # create a list which holds parent parts of currently
        # selected items, if the part of variable does not match,
        # than the variable (or any children) will not be selected
        quick_check = [var.__getattribute__(key) for var in variables]

        num_rows = self.rowCount()
        for i in range(num_rows):
            # loop through the first column
            p_ix = self.index(i, 0)
            dt = self.data(p_ix)

            if dt not in quick_check:
                # skip the variable as a quick check part does not match
                continue

            if self.hasChildren(p_ix):
                # check if the variable is nested
                num_child_rows = self.rowCount(p_ix)
                for j in range(num_child_rows):
                    ix = self.index(j, 0, p_ix)
                    var = self.data_at_index(ix)
                    if check_var():
                        selection.append(QItemSelectionRange(ix))
            else:
                var = self.data_at_index(p_ix)
                if check_var():
                    selection.append(QItemSelectionRange(p_ix))

        return selection


class TreeView(SimpleView):
    treeNodeChanged = Signal()

    def __init__(self, id_: int, name: str):
        super().__init__(id_, name, TreeViewModel, TreeFilterModel)
        self.setRootIsDecorated(True)
        self.expanded.connect(self.on_expanded)
        self.collapsed.connect(self.on_collapsed)
        self.header().sectionResized.connect(self.on_view_resized)

    def setFirstTreeColumnSpanned(self) -> None:
        """ Set parent row to be spanned over all columns. """
        for i in range(self.model().rowCount()):
            ix = self.model().index(i, 0)
            if self.model().hasChildren(ix):
                super().setFirstColumnSpanned(i, self.rootIndex(), True)

    def filter_view(self, filter_tup: FilterTuple) -> None:
        """ Filter the model using given filter tuple. """
        super().filter_view(filter_tup)
        if self.is_tree:
            # Expand all items when filter is applied
            self.expandAll()
            # it's required to reapply column span after each filter
            self.setFirstTreeColumnSpanned()

    def expand_items(self, expanded_set: Set[str]) -> None:
        """ Expand items which were previously expanded (on other models). """
        for i in range(self.model().rowCount()):
            ix = self.model().index(i, 0)
            if self.model().hasChildren(ix):
                data = self.model().data(ix)
                if data in expanded_set:
                    self.expand(ix)
                else:
                    self.collapse(ix)

    def resize_header(self, widths) -> None:
        """ Define resizing behaviour. """
        super().resize_header(widths)
        log_ixs = self.model().get_logical_indexes()
        vis_ixs = self.get_visual_indexes()

        # units column width is always fixed
        fixed = log_ixs["units"]
        self.header().setSectionResizeMode(fixed, QHeaderView.Fixed)
        self.header().setStretchLastSection(False)

        # key and variable sections can be either Stretch or Interactive
        # Interactive section can be resized programmatically
        if vis_ixs["key"] > vis_ixs["variable"]:
            stretch = log_ixs["key"]
            interactive = log_ixs["variable"]
        else:
            stretch = log_ixs["variable"]
            interactive = log_ixs["key"]

        self.header().setSectionResizeMode(stretch, QHeaderView.Stretch)
        self.header().setSectionResizeMode(interactive, QHeaderView.Interactive)

        # resize sections programmatically
        self.header().resizeSection(interactive, widths["interactive"])

    def update_view_appearance(
            self,
            header: tuple = ("variable", "key", "units"),
            widths: Dict[str, int] = None,
            expanded: Set[str] = None,
            **kwargs
    ) -> None:
        """ Update the model appearance to be consistent with last view. """
        if not widths:
            widths = {"interactive": 200, "fixed": 70}
        if expanded:
            self.expand_items(expanded)
        super().update_view_appearance(header, widths)

    def populate_view(
            self,
            variables_df: pd.DataFrame,
            interval: str,
            is_tree: bool =True,
            rate_to_energy: bool = False,
            units_system: str = "SI",
            energy_units: str = "J",
            power_units: str = "W",
            header: Tuple[str, str, str] = ("variable", "key", "units"),
    ) -> None:
        """ Set the model and define behaviour of the tree view. """
        self.is_tree = is_tree
        super().populate_view(
            variables_df=variables_df,
            interval=interval,
            is_tree=is_tree,
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            power_units=power_units,
            header=header,
        )
        # make sure that parent column spans full width
        if is_tree:
            self.setFirstTreeColumnSpanned()

    def on_view_resized(self, log_ix: int, _, new_size: int) -> None:
        """ Store interactive section width in the main app. """
        if self.header().sectionResizeMode(log_ix) == self.header().Interactive:
            self.viewSettingsChanged.emit({"interactive": new_size})

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when first column changed. """
        super().on_section_moved(_logical_ix, old_visual_ix, new_visual_ix)

        # view needs to be updated when the tree structure is applied and first item changes
        if (new_visual_ix == 0 or old_visual_ix == 0) and self.is_tree:
            self.next_update_forced = True
            self.treeNodeChanged.emit()

            # automatically sort first column based on last sort update
            self.header().setSortIndicator(0, self.model().sortOrder())

    def on_double_clicked(self, index: QModelIndex):
        """ Handle view double click. """
        proxy_model = self.model()
        source_item = proxy_model.item_at_index(index)

        if not source_item.hasChildren():
            # parent item cannot be renamed
            super().on_double_clicked(index)

    def on_pressed(self) -> None:
        """ Handle pressing the view item or items. """
        proxy_model = self.model()
        proxy_rows = self.selectionModel().selectedRows()
        rows = proxy_model.map_to_source_lst(proxy_rows)

        if proxy_rows:
            # handle a case in which expanded parent node is clicked
            # note that desired behaviour is to select all the children
            # unless any of the children is included in the multi selection
            for index in proxy_rows:
                source_item = proxy_model.item_at_index(index)
                source_index = proxy_model.mapToSource(index)

                if source_item.hasChildren():
                    # select all the children if the item is expanded
                    # and none of the children has been already selected
                    cond = any(map(lambda x: x.parent() == source_index, rows))
                    if self.isExpanded(index) and not cond:
                        self._select_children(source_item, source_index)

                    # deselect all the parent nodes as these should not be
                    # included in output variable data
                    self._deselect_item(index)

            # needs to be called again to get updated selection
            super().on_pressed()

    def _select_children(self, source_item: QStandardItem, source_index: QModelIndex) -> None:
        """ Select all children of the parent row. """
        first_ix = source_index.child(0, 0)
        last_ix = source_index.child((source_item.rowCount() - 1), 0)

        selection = QItemSelection(first_ix, last_ix)
        proxy_selection = self.model().mapSelectionFromSource(selection)

        self._select_items(proxy_selection)

    def on_collapsed(self, index: QModelIndex) -> None:
        """ Deselect the row when node collapses."""
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            self.viewSettingsChanged.emit({"collapsed": name})

    def on_expanded(self, index: QModelIndex) -> None:
        """ Deselect the row when node is expanded. """
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            self.viewSettingsChanged.emit({"expanded": name})
