from typing import Dict, List, Set, Sequence, Tuple

import pandas as pd
from PySide2.QtCore import (
    Qt,
    QSortFilterProxyModel,
    QItemSelectionModel,
    QItemSelection,
    QItemSelectionRange,
    QMimeData,
    QEvent,
    Signal,
    QModelIndex
)
from PySide2.QtGui import QStandardItemModel, QStandardItem, QDrag, QPixmap
from PySide2.QtWidgets import QTreeView, QAbstractItemView, QHeaderView, QMenu

from chartify.utils.utils import FilterTuple, VariableData
from chartify.utils.utils import create_proxy_units_column


class View(QTreeView):
    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(object)
    treeNodeChanged = Signal()
    viewSettingsChanged = Signal(dict)

    def __init__(self, id_: int, name: str):
        super().__init__()
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.setMouseTracking(True)

        self.setDragEnabled(False)
        self.setWordWrap(False)  # not working at the moment
        self.setAlternatingRowColors(False)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.NoFocus)

        self.id_ = id_
        self.name = name

        # create initial view model
        model = ViewModel()

        # install proxy model
        proxy_model = FilterModel()
        proxy_model.setSourceModel(model)
        proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxy_model.setRecursiveFilteringEnabled(True)
        proxy_model.setDynamicSortFilter(False)
        self.setModel(proxy_model)

        self.temp_settings = {
            "interval": None,
            "is_tree": None,
            "units": None,
            "filter": None,
            "force_update": True,
        }

        # hold ui attributes
        self.scrollbar_position = 0
        self.indicator = (0, Qt.AscendingOrder)

        self.verticalScrollBar().valueChanged.connect(self.on_slider_moved)
        self.expanded.connect(self.on_expanded)
        self.collapsed.connect(self.on_collapsed)
        self.pressed.connect(self.on_pressed)
        self.doubleClicked.connect(self.on_double_clicked)

        self.header().setFirstSectionMovable(True)

    def mousePressEvent(self, event: QEvent) -> None:
        """ Handle mouse events. """
        btn = event.button()
        if btn == Qt.RightButton or btn == Qt.MiddleButton:
            return
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event: QEvent) -> None:
        """ Manage context menu. """
        menu = QMenu(self)
        menu.setObjectName("contextMenu")
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.exec_(self.mapToGlobal(event.pos()))

    def setFirstTreeColumnSpanned(self) -> None:
        """ Set parent row to be spanned over all columns. """
        for i in range(self.model().rowCount()):
            ix = self.model().index(i, 0)
            if self.model().hasChildren(ix):
                super().setFirstColumnSpanned(i, self.rootIndex(), True)

    def filter_view(self, filter_tup: FilterTuple, is_tree: bool) -> None:
        """ Filter the model using given filter tuple. """
        self.model().setFilterTuple(filter_tup)

        # Expand all items when filter is applied
        self.expandAll()

        if is_tree:
            # it's required to reapply column span after each filter
            self.setFirstTreeColumnSpanned()

    def set_next_update_forced(self) -> None:
        """ Notify the view that it needs to be updated. """
        self.temp_settings["force_update"] = True

    def get_visual_names(self) -> List[str]:
        """ Return sorted column names (by visual index). """
        dct_items = sorted(self.get_visual_ixs().items(), key=lambda x: x[1])
        return [t[0] for t in dct_items]

    def get_visual_ixs(self) -> Dict[str, int]:
        """ Get a dictionary of section visual index pairs. """
        log_ixs = self.model().get_logical_ixs()
        return {k: self.header().visualIndex(i) for k, i in log_ixs.items()}

    def reshuffle_columns(self, order: Dict[str, int]):
        """ Reset column positions to match last visual appearance. """
        for i, nm in enumerate(order):
            vis_names = self.get_visual_names()
            j = vis_names.index(nm)
            if i != j:
                self.header().moveSection(j, i)

    def update_sort_order(self) -> None:
        """ Set order for all columns. """
        indicator_column, order = self.indicator
        self.model().sort(indicator_column, order)
        self.header().setSortIndicator(indicator_column, order)

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

    def scroll_to(self, var: VariableData, first_col: str) -> None:
        """ Scroll to the given var. """
        proxy_model = self.model()

        # var needs to be passed as a list
        proxy_selection = proxy_model.find_match([var], first_col)

        if proxy_selection:
            self.scrollTo(proxy_selection.indexes()[0])

    def update_view_appearance(self, settings: dict) -> None:
        """ Update the model appearance to be consistent with last view. """
        self.resize_header(settings["widths"])
        self.update_sort_order()

        if settings["expanded"]:
            self.expand_items(settings["expanded"])

        # it's required to adjust columns order to match the last applied order
        self.reshuffle_columns(settings["header"])

        # scroll to last position
        self.verticalScrollBar().setValue(self.scrollbar_position)

    def disconnect_signals(self) -> None:
        """ Disconnect specific signals to avoid overriding stored values. """
        self.verticalScrollBar().valueChanged.disconnect(self.on_slider_moved)

    def connect_signals(self) -> None:
        """ Connect specific signals. """
        self.verticalScrollBar().valueChanged.connect(self.on_slider_moved)
        self.header().sectionResized.connect(self.on_view_resized, type=Qt.UniqueConnection)
        self.header().sectionMoved.connect(self.on_section_moved, type=Qt.UniqueConnection)
        self.header().sortIndicatorChanged.connect(
            self.on_sort_order_changed, type=Qt.UniqueConnection
        )

    def deselect_variables(self) -> None:
        """ Deselect all currently selected variables. """
        self.selectionModel().clearSelection()
        self.selectionCleared.emit()

    def select_variables(self, variables: List[VariableData]) -> None:
        """ Select previously selected items when the model changes. """
        proxy_model = self.model()
        key = self.settings["header"][0]

        # Find matching items and select items on a new model
        proxy_selection = proxy_model.find_match(variables, key)

        # select items in view
        self._select_items(proxy_selection)

        proxy_rows = proxy_selection.indexes()
        variables_data = [proxy_model.data_from_index(index) for index in proxy_rows]

        if variables_data:
            self.selectionPopulated.emit(variables_data)
        else:
            self.selectionCleared.emit()

    def build_view(
            self,
            variables_df: pd.DataFrame,
            interval: str,
            is_tree: bool,
            rate_to_energy: bool = False,
            units_system: str = "SI",
            energy_units: str = "J",
            power_units: str = "W",
            filter_tup: FilterTuple = FilterTuple("", "", ""),
            selected: List[VariableData] = None,
            scroll_to: VariableData = None,
            settings: dict = None
    ) -> None:
        """ Set the model and define behaviour of the tree view. """
        if not settings:
            settings = {
                "widths": {"interactive": 200, "fixed": 70},
                "header": ["variable", "key", "units"],
                "expanded": set(),
            }

        # deactivate signals as those would override settings
        self.disconnect_signals()

        # gather units to check
        units = (rate_to_energy, units_system, energy_units, power_units)

        # Only update the model if the settings have changed
        conditions = [
            is_tree != self.temp_settings["is_tree"],
            interval != self.temp_settings["interval"],
            units != self.temp_settings["units"],
            filter_tup != self.temp_settings["filter"],
            self.temp_settings["force_update"],
        ]

        if any(conditions):
            print("UPDATING MODEL")
            # clear the previous model
            self.model().sourceModel().clear()

            # populate new model
            model = ViewModel()
            model.setColumnCount(len(settings["header"]))
            model.setHorizontalHeaderLabels(settings["header"])

            # id and interval data are not required
            variables_df.drop(["id", "interval"], axis=1, inplace=True)

            # add proxy units - these will be visible on ui
            variables_df["source units"] = variables_df["units"]
            variables_df["units"] = create_proxy_units_column(
                source_units=variables_df["source units"],
                rate_to_energy=rate_to_energy,
                units_system=units_system,
                energy_units=energy_units,
                power_units=power_units,
            )

            # update columns order based on current view
            view_order = settings["header"] + ["source units"]
            variables_df = variables_df[view_order]

            # feed the data
            model.populate_model(variables_df, is_tree)
            self.model().setSourceModel(model)

            # Store current sorting key and interval
            self.temp_settings = {
                "interval": interval,
                "is_tree": is_tree,
                "units": units,
                "filter": filter_tup,
                "force_update": False,
            }
            # make sure that parent column spans full width
            if is_tree:
                self.setFirstTreeColumnSpanned()

        # clear selections to avoid having visually
        # selected items from previous selection
        self.deselect_variables()

        if selected:
            self.select_variables(selected)

        if any(filter_tup):
            self.filter_view(filter_tup, is_tree)

        if scroll_to:
            self.scroll_to(scroll_to, settings["header"][0])

        # update visual appearance of the view to be consistent
        # with previously displayed View
        self.update_view_appearance(settings)
        self.connect_signals()

    def resize_header(self, widths) -> None:
        """ Define resizing behaviour. """
        log_ixs = self.model().get_logical_ixs()
        vis_ixs = self.get_visual_ixs()

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
        self.header().resizeSection(fixed, widths["fixed"])
        self.header().resizeSection(interactive, widths["interactive"])

    def on_sort_order_changed(self, log_ix: int, order: Qt.SortOrder) -> None:
        """ Store current sorting order. """
        self.indicator = (log_ix, order)
        name = self.model().headerData(log_ix, Qt.Horizontal)

    def on_view_resized(self, log_ix: int, _, new_size: int) -> None:
        """ Store interactive section width in the main app. """
        if self.header().sectionResizeMode(log_ix) == self.header().Interactive:
            self.viewSettingsChanged.emit({"interactive": new_size})

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when first column changed. """
        names = self.get_visual_names()
        is_tree = self.temp_settings["is_tree"]
        self.viewSettingsChanged.emit({"header": names})

        # view needs to be updated when the tree structure is applied and first item changes
        if (new_visual_ix == 0 or old_visual_ix == 0) and is_tree:
            self.set_next_update_forced()
            self.treeNodeChanged.emit()

            # automatically sort first column based on last sort update
            self.header().setSortIndicator(0, self.model().sortOrder())

    def on_slider_moved(self, val: int) -> None:
        """ Handle moving view slider. """
        self.scrollbar_position = val

    def on_double_clicked(self, index: QModelIndex):
        """ Handle view double click. """
        proxy_model = self.model()
        source_item = proxy_model.item_from_index(index)

        if source_item.hasChildren():
            # parent item cannot be renamed
            return

        if source_item.column() > 0:
            index = index.siblingAtColumn(0)

        # deselect all base variables
        self.deselect_variables()

        dt = proxy_model.data_from_index(index)
        if dt:
            self.select_variables([dt])
            self.itemDoubleClicked.emit(dt)

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
                source_item = proxy_model.item_from_index(index)
                source_index = proxy_model.mapToSource(index)

                if source_item.hasChildren():
                    # select all the children if the item is expanded
                    # and none of the children has been already selected
                    expanded = self.isExpanded(index)
                    cond = any(map(lambda x: x.parent() == source_index, rows))
                    if expanded and not cond:
                        self._select_children(source_item, source_index)

                    # deselect all the parent nodes as these should not be
                    # included in output variable data
                    self._deselect_item(index)

            # needs to be called again to get updated selection
            proxy_rows = self.selectionModel().selectedRows()

        variables_data = [proxy_model.data_from_index(index) for index in proxy_rows]

        if variables_data:
            mime_dt = QMimeData()
            mime_dt.setText("HELLO FROM CHARTIFY")
            pix = QPixmap("./icons/input.png")

            drag = QDrag(self)
            drag.setMimeData(mime_dt)
            drag.setPixmap(pix)
            drag.exec_(Qt.CopyAction)

            self.selectionPopulated.emit(variables_data)
        else:
            self.selectionCleared.emit()

    def _select_children(self, source_item: QStandardItem, source_index: QModelIndex) -> None:
        """ Select all children of the parent row. """
        first_ix = source_index.child(0, 0)
        last_ix = source_index.child((source_item.rowCount() - 1), 0)

        selection = QItemSelection(first_ix, last_ix)
        proxy_selection = self.model().mapSelectionFromSource(selection)

        self._select_items(proxy_selection)

    def _deselect_item(self, proxy_index: QModelIndex) -> None:
        """ Select an item programmatically. """
        self.selectionModel().select(
            proxy_index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows
        )

    def _select_item(self, proxy_index: QModelIndex) -> None:
        """ Select an item programmatically. """
        self.selectionModel().select(
            proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows
        )

    def _select_items(self, proxy_selection: QItemSelection) -> None:
        """ Select items given by given selection (model indexes). """
        self.selectionModel().select(
            proxy_selection, QItemSelectionModel.Select | QItemSelectionModel.Rows
        )

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


class ViewModel(QStandardItemModel):
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
        status_tip = (
            f"{key} | {variable} | {proxy_units}" if key else f"{variable} | {proxy_units}"
        )

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

    def append_plain_rows(self, variables_df: pd.DataFrame, indexes: Dict[str, int]) -> None:
        for row in variables_df.values:
            item_row = [QStandardItem(item) for item in row[:-1]]
            self._append_row(self, row, item_row, indexes)

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
        key_index = columns.index("key") if "key" in columns else None
        indexes = {
            "key": key_index,
            "variable": columns.index("variable"),
            "units": columns.index("units"),
            "source units": columns.index("source units"),
        }

        if not is_tree:
            # create plain table when tree structure not requested
            self.append_plain_rows(variables_df, indexes)
        else:
            self.append_tree_rows(variables_df, indexes)


class FilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter_tup = FilterTuple(key="", variable="", units="")

    def lessThan1(self, source_left: QModelIndex, source_right: QModelIndex) -> bool:
        left_row = source_left.row()
        right_row = source_right.row()
        num_columns = self.sourceModel().columnCount()

        print(source_left)

        for i in range(num_columns):
            left_index = self.sourceModel().index(left_row, i)
            right_index = self.sourceModel().index(right_row, i)

            left_data = self.sourceModel().data(left_index)
            right_data = self.sourceModel().data(right_index)

            if left_data != right_data:
                return left_data < right_data

        return False

    def setFilterTuple(self, filter_tup: FilterTuple) -> None:
        self._filter_tup = filter_tup
        self.invalidateFilter()

    def get_logical_names(self) -> List[str]:
        """ Get names sorted by logical index. """
        num = self.columnCount()
        return [self.headerData(i, Qt.Horizontal).lower() for i in range(num)]

    def get_logical_index(self, name: str) -> int:
        """ Get a logical index of a given section title. """
        return self.get_logical_names().index(name)

    def get_logical_ixs(self) -> Dict[str, int]:
        """ Return logical positions of header labels. """
        names = self.get_logical_names()
        return {
            "key": names.index("key"),
            "variable": names.index("variable"),
            "units": names.index("units"),
        }

    def data_from_index(self, index: QModelIndex) -> VariableData:
        """ Get item data from source model. """
        return self.item_from_index(index).data(Qt.UserRole)

    def item_from_index(self, index: QModelIndex) -> QStandardItem:
        """ Get item from source model. """
        source_index = self.mapToSource(index)
        return self.sourceModel().itemFromIndex(source_index)

    def map_to_source_lst(self, indexes: List[QModelIndex]) -> List[QModelIndex]:
        """ Map a list of indexes to the source model. """
        return [self.mapToSource(ix) for ix in indexes]

    def map_from_source_lst(self, indexes: List[QModelIndex]) -> List[QModelIndex]:
        """ Map a list of source indexes to the proxy model. """
        return [self.mapFromSource(ix) for ix in indexes]

    def filterAcceptsRow(self, source_row: int, source_parent: QStandardItem) -> bool:
        """ Set up filtering rules for the model. """

        def valid():
            if fval:
                return fval.lower() in val.lower()
            else:
                return True

        if not any(self._filter_tup):
            return True

        # first item can be either parent for 'tree' structure or a normal item
        ix0 = self.sourceModel().index(source_row, 0, source_parent)
        it0 = self.sourceModel().itemFromIndex(ix0)

        if it0.hasChildren():
            # exclude parent nodes (these are enabled due to recursive filter)
            return False

        else:
            variable_data = it0.data(role=Qt.UserRole)

            # check if all filter fields match
            for k, fval in self._filter_tup._asdict().items():
                if not fval:
                    continue
                else:
                    fval = fval.strip()
                    val = variable_data.__getattribute__(k)

                if not valid():
                    # condition fails if any of filter fields does not match
                    return False

            return True

    def find_match(self, variables: List[VariableData], key: str) -> QItemSelection:
        """ Check if output variables are available in a new model. """

        def check_var():
            v = (var.key, var.variable)
            return v in stripped_vars

        selection = QItemSelection()
        stripped_vars = [(var.key, var.variable) for var in variables]

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
                    var = self.data_from_index(ix)
                    if check_var():
                        selection.append(QItemSelectionRange(ix))
            else:
                var = self.data_from_index(p_ix)
                if check_var():
                    selection.append(QItemSelectionRange(p_ix))

        return selection

    def flags(self, index: QModelIndex) -> None:
        """ Set item flags. """
        if self.hasChildren(index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable
