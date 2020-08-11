import contextlib
from typing import Dict, List, Set, Sequence, Optional, Tuple

import pandas as pd
from PySide2.QtCore import (
    QSortFilterProxyModel,
    QMimeData,
    QEvent,
    QItemSelectionModel,
    QItemSelection,
    QItemSelectionRange,
    Signal,
    QModelIndex,
    Qt,
)
from PySide2.QtGui import QStandardItem, QStandardItemModel, QDrag, QPixmap
from PySide2.QtWidgets import QTreeView, QAbstractItemView, QHeaderView
from esofile_reader.constants import *

from chartify.utils.utils import (
    FilterTuple,
    VariableData,
    create_proxy_units_column,
    SignalBlocker,
)

SOURCE_UNITS = "source units"


class ViewModel(QStandardItemModel):
    """ View models allowing 'tree' like structure.

    Model can show up to four columns 'key', 'type', units' and
    'source units'. 'Type' column is optional.
    The 'VariableData' named tuple containing variable information
    is stored as 'UserData' on the first item in row (only for
    'child' items when tree structure is applied).

    Tree items which would only have one child are automatically
    treated as plain table rows.

    Attributes
    ----------
    is_simple : bool
        Check if model includes 'type' column.
    allow_rate_to_energy : bool
        Define if model can convert rate to energy.
    tree_node : str
        Current tree column node, may be 'None' for
        plain table structure.
    rate_to_energy : bool
        Checks if rate is transposed to energy.
    units_system : str
        Current view units system {SI, IP}.
    energy_units : str
        Used energy units.
    power_units : str
        Used power units.
    dirty : bool
        Check if model needs to be updated.
    scroll_position : int
        Store current scrollbar position.
    expanded : set of {str}
        Currently expanded items.

    """

    def __init__(
        self,
        name: str,
        header_df: pd.DataFrame,
        is_simple: bool = False,
        allow_rate_to_energy: bool = False,
    ):
        super().__init__()
        self.name = name
        self.is_simple = is_simple
        self.allow_rate_to_energy = allow_rate_to_energy
        self.tree_node = None
        self.rate_to_energy = False
        self.units_system = "SI"
        self.energy_units = "J"
        self.power_units = "W"
        self.dirty = False
        self.scroll_position = 0
        self.expanded = set()
        self.populate_model(header_df=header_df)

    def count_rows(self) -> int:
        """ Calculate total number of rows (including child rows). """
        count = self.rowCount()
        if not self.is_simple:
            for i in range(self.rowCount()):
                item = self.item(i, 0)
                if item.hasChildren():
                    count += item.rowCount()
        return count

    def is_similar(self, other_model: "ViewModel", rows_diff: float = 0.05):
        """ Check if number of variables and structure matches the other model. """
        count = self.count_rows()
        diff = (count - other_model.count_rows()) / count
        return self.tree_node == other_model.tree_node and abs(diff) <= rows_diff

    def _append_row(
        self,
        parent: QStandardItem,
        row: Sequence[str],
        item_row: List[QStandardItem],
        indexes: Dict[str, int],
    ) -> None:
        """ Append row to the given parent. """
        # assign status tip for all items in row
        key = row[indexes[KEY_LEVEL]]
        proxy_units = row[indexes[UNITS_LEVEL]]
        source_units = row[indexes[SOURCE_UNITS]]

        if not self.is_simple:
            type_ = row[indexes[TYPE_LEVEL]]
            status_tip = f"{key} | {type_} | {proxy_units}"
            vd = VariableData(key=key, type=type_, units=source_units, proxyunits=proxy_units)
        else:
            status_tip = f"{key} | {proxy_units}"
            vd = VariableData(key=key, type=None, units=source_units, proxyunits=proxy_units)

        # show all the info for each item in row
        for item in item_row:
            item.setStatusTip(status_tip)

        # first item holds the variable data used for search
        item_row[0].setData(vd, role=Qt.UserRole)
        parent.appendRow(item_row)

    def append_plain_rows(self, header_df: pd.DataFrame, indexes: Dict[str, int]) -> None:
        for row in header_df.values:
            item_row = [QStandardItem(item) for item in row]
            self._append_row(self, row, item_row, indexes)

    def append_tree_rows(self, header_df: pd.DataFrame, indexes: Dict[str, int]) -> None:
        """ Add rows for a tree like view. """
        grouped = header_df.groupby(by=[header_df.columns[0]])
        for parent, df in grouped:
            if len(df.index) == 1:
                self.append_plain_rows(df, indexes)
            else:
                parent_item = QStandardItem(parent)
                parent_item.setDragEnabled(False)
                self.invisibleRootItem().appendRow(parent_item)
                for row in df.values:
                    # first standard item is empty to avoid
                    # having parent string in the child row
                    item_row = [QStandardItem("")]
                    for item in row[1:]:
                        item_row.append(QStandardItem(item))
                    self._append_row(parent_item, row, item_row, indexes)

    def populate_model(
        self,
        header_df: pd.DataFrame,
        tree_node: Optional[str] = None,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        power_units: str = "W",
    ) -> None:
        """  Create a model and set up its appearance. """
        # make sure that model is empty
        self.clear()

        # tree node data is always None for 'Simple' views
        self.tree_node = tree_node if not self.is_simple else None
        self.rate_to_energy = rate_to_energy
        self.units_system = units_system
        self.energy_units = energy_units
        self.power_units = power_units
        self.dirty = False

        # id and table data are not required
        header_df = header_df.drop([ID_LEVEL, TABLE_LEVEL], axis=1)

        # add proxy units - these will be visible on ui
        header_df[SOURCE_UNITS] = header_df[UNITS_LEVEL]
        header_df[UNITS_LEVEL] = create_proxy_units_column(
            source_units=header_df[SOURCE_UNITS],
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            power_units=power_units,
        )
        if self.tree_node:
            # tree column needs to be first
            new_columns = header_df.columns.tolist()
            new_columns.insert(0, new_columns.pop(new_columns.index(tree_node)))
            header_df = header_df.loc[:, new_columns]

        columns = header_df.columns.tolist()
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        indexes = {k: columns.index(k) for k in columns}
        if self.tree_node:
            self.append_tree_rows(header_df, indexes)
        else:
            self.append_plain_rows(header_df, indexes)

    def update_units(
        self,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        power_units: str = "W",
    ):
        """ Assign proxy units. """
        # TODO
        pass


class FilterModel(QSortFilterProxyModel):
    """ Proxy model to be used with 'SimpleModel' model. """

    def __init__(self):
        super().__init__()
        self._filter_tuple = FilterTuple(key="", type="", units="")

    @property
    def filter_tuple(self) -> FilterTuple:
        return self._filter_tuple

    @filter_tuple.setter
    def filter_tuple(self, filter_tuple: FilterTuple) -> None:
        self._filter_tuple = filter_tuple
        self.invalidateFilter()

    def get_logical_names(self) -> List[str]:
        """ Get names sorted by logical index. """
        return [self.headerData(i, Qt.Horizontal).lower() for i in range(self.columnCount())]

    def get_logical_index(self, name: str) -> int:
        """ Get a logical index of a given section title. """
        return self.get_logical_names().index(name)

    def get_logical_indexes(self) -> Dict[str, int]:
        """ Return logical positions of header labels. """
        names = self.get_logical_names()
        return {k: names.index(k) for k in names}

    def data_at_index(self, proxy_index: QModelIndex) -> VariableData:
        """ Get item data from source model. """
        return self.item_at_index(proxy_index).data(Qt.UserRole)

    def item_at_index(self, proxy_index: QModelIndex) -> QStandardItem:
        """ Get item from source model. """
        source_index = self.mapToSource(proxy_index)
        return self.sourceModel().itemFromIndex(source_index)

    def map_to_source_lst(self, indexes: List[QModelIndex]) -> List[QModelIndex]:
        """ Map a list of indexes to the source model. """
        return [self.mapToSource(ix) for ix in indexes]

    def filterAcceptsRow(self, source_row: int, source_parent: QStandardItem) -> bool:
        """ Set up filtering rules for the model. """
        if not any(self._filter_tuple):
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
            for k, filter_string in self._filter_tuple._asdict().items():
                if not filter_string:
                    continue
                else:
                    filter_string = filter_string.strip()
                    val = variable_data.__getattribute__(k)

                if filter_string and val:
                    if filter_string.lower() in val.lower():
                        continue
                    else:
                        return False
                else:
                    return True

            return True

    def find_match(self, variables: List[VariableData]) -> QItemSelection:
        """ Check if output variables are available in a new model. """
        is_simple = self.sourceModel().is_simple
        tree_node = self.sourceModel().tree_node

        def check_var():
            v = var.key if is_simple else (var.key, var.type)
            return v in test_values

        if is_simple:
            test_values = {v.key for v in variables}
        else:
            test_values = {(v.key, v.type) for v in variables}

        # create a set which holds parent parts of currently
        # selected items, if the part of variable does not match,
        # than the variable (or any children) will not be selected
        quick_check = {v.__getattribute__(tree_node) for v in variables} if tree_node else set()

        selection = QItemSelection()
        for i in range(self.rowCount()):
            # loop through the first column
            p_ix = self.index(i, 0)
            if self.hasChildren(p_ix):
                if self.data(p_ix) in quick_check:
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

    def flags(self, index: QModelIndex) -> None:
        """ Set item flags. """
        if self.hasChildren(index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable


class TreeView(QTreeView):
    """ A simple tree view.

    This class should be used altogether with underlying
    'ViewModel' and 'FilterModel' which are
    set up to work with this class.


    Attributes
    ----------
    id_ : int
        An id identifier of the base file.
    models : dict of {str : ModelView}
        Available view models.

    Signals
    -------
    selectionCleared
        Is emitted when selection is canceled or any of preselected
        variables cannot be found in the model.
    selectionPopulated
        Is emitted when selection is canceled or any of preselected
        variables cannot be found in the model.
    itemDoubleClicked
        Is emitted on item double click.
    viewAppearanceChanged
        Is emitted when visual appearance changes.
    treeNodeChanged
        Is emitted if the view uses tree structure changes.

    """

    SIMPLE = "simple"
    TREE = "tree"

    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(VariableData)
    viewAppearanceChanged = Signal(str, dict)
    treeNodeChanged = Signal(str)

    def __init__(self, id_: int, models: Dict[str, ViewModel]):
        super().__init__()
        self.id_ = id_
        self.models = models
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.setMouseTracking(True)

        self.setDragEnabled(True)
        self.setWordWrap(False)  # not working at the moment
        self.setAlternatingRowColors(False)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.NoFocus)

        # install proxy model
        proxy_model = FilterModel()
        proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxy_model.setRecursiveFilteringEnabled(True)
        proxy_model.setDynamicSortFilter(False)
        self.setModel(proxy_model)

        # hold ui attributes
        self.indicator = (0, Qt.AscendingOrder)

        self.verticalScrollBar().valueChanged.connect(self.on_slider_moved)
        self.pressed.connect(self.on_pressed)
        self.doubleClicked.connect(self.on_double_clicked)

        self.header().setStretchLastSection(False)
        self.header().setFirstSectionMovable(True)
        self.header().sectionMoved.connect(self.on_section_moved)
        self.header().sortIndicatorChanged.connect(self.on_sort_order_changed)
        self.header().sectionResized.connect(self.on_view_resized)

        self.expanded.connect(self.on_item_expanded)
        self.collapsed.connect(self.on_item_collapsed)

    @property
    def current_model(self) -> ViewModel:
        return self.proxy_model.sourceModel()

    @property
    def proxy_model(self) -> FilterModel:
        return self.model()

    @property
    def view_type(self) -> str:
        return self.SIMPLE if self.current_model.is_simple else self.TREE

    @property
    def is_tree(self) -> bool:
        return bool(self.current_model.tree_node)

    @property
    def allow_rate_to_energy(self) -> bool:
        if self.current_model:
            return self.current_model.allow_rate_to_energy
        else:
            return True

    def mousePressEvent(self, event: QEvent) -> None:
        """ Handle mouse events. """
        btn = event.button()
        if btn == Qt.RightButton or btn == Qt.MiddleButton:
            return
        else:
            super().mousePressEvent(event)

    def startDrag(self, drop_actions: Qt.DropActions):
        """ Create custom drag event. """
        # default implementation:
        # https://code.qt.io/cgit/qt/qtbase.git/tree/src/widgets/itemviews/qabstractitemview.cpp#n3588
        mime_dt = QMimeData()
        mime_dt.setText("HELLO FROM CHARTIFY")
        pix = QPixmap("./icons/input.png")

        drag = QDrag(self)
        drag.setMimeData(mime_dt)
        drag.setPixmap(pix)
        drag.exec_(Qt.CopyAction)

    def setFirstTreeColumnSpanned(self) -> None:
        """ Set parent row to be spanned over all columns. """
        for i in range(self.proxy_model.rowCount()):
            ix = self.proxy_model.index(i, 0)
            if self.proxy_model.hasChildren(ix):
                super().setFirstColumnSpanned(i, self.rootIndex(), True)

    def filter_view(self, filter_tuple: FilterTuple) -> None:
        """ Filter the model using given filter tuple. """
        self.proxy_model.filter_tuple = filter_tuple
        if self.is_tree:
            # Expand all items when filter is applied
            self.expandAll()
            # it's required to reapply column span after each filter
            self.setFirstTreeColumnSpanned()

    def get_visual_names(self) -> Tuple[str, ...]:
        """ Return sorted column names (by visual index). """
        dct_items = sorted(self.get_visual_indexes().items(), key=lambda x: x[1])
        return tuple([t[0] for t in dct_items])

    def get_visual_indexes(self) -> Dict[str, int]:
        """ Get a dictionary of section visual index pairs. """
        log_ixs = self.proxy_model.get_logical_indexes()
        return {k: self.header().visualIndex(i) for k, i in log_ixs.items()}

    def reorder_columns(self, order: Tuple[str, ...]):
        """ Reset column positions to match last visual appearance. """
        for i, name in enumerate(order):
            vis_indexes = self.get_visual_indexes()
            j = vis_indexes[name]
            if i != j:
                self.header().moveSection(j, i)

    def update_scrollbar_position(self, pos: int):
        """ Set vertical scrollbar position. """
        # maximum is sometimes left as '0' which blocks
        # setting position and leaves slider on top
        if self.verticalScrollBar().maximum() < pos:
            self.verticalScrollBar().setMaximum(pos)
        self.verticalScrollBar().setValue(pos)
        # stored value changes on user action, need to store manually
        self.current_model.scroll_position = pos

    def update_sort_order(self) -> None:
        """ Set order for sort column. """
        indicator_column, order = self.indicator
        self.proxy_model.sort(indicator_column, order)
        self.header().setSortIndicator(indicator_column, order)

    def scroll_to(self, vd: VariableData) -> None:
        """ Scroll to the given variable. """
        proxy_selection = self.proxy_model.find_match([vd])
        if proxy_selection:
            self.scrollTo(proxy_selection.indexes()[0])

    def expand_items(self, expanded_set: Set[str]) -> None:
        """ Expand items which were previously expanded (on other models). """
        for i in range(self.proxy_model.rowCount()):
            ix = self.proxy_model.index(i, 0)
            if self.proxy_model.hasChildren(ix):
                data = self.proxy_model.data(ix)
                if data in expanded_set:
                    self.expand(ix)
                else:
                    self.collapse(ix)

    def resize_header(self, widths: Dict[str, int]) -> None:
        """ Define resizing behaviour. """
        # units column width is always fixed
        units_index = self.proxy_model.get_logical_index(UNITS_LEVEL)
        source_units_index = self.proxy_model.get_logical_index(SOURCE_UNITS)

        self.header().setSectionResizeMode(units_index, QHeaderView.Fixed)
        self.header().setSectionResizeMode(source_units_index, QHeaderView.Fixed)
        self.header().setStretchLastSection(False)

        self.header().resizeSection(units_index, widths["fixed"])
        self.header().resizeSection(source_units_index, widths["fixed"])

        if self.current_model.is_simple:
            stretch = self.proxy_model.get_logical_index(KEY_LEVEL)
            self.header().setSectionResizeMode(stretch, QHeaderView.Stretch)
        else:
            log_ixs = self.proxy_model.get_logical_indexes()
            vis_ixs = self.get_visual_indexes()

            # units column width is always fixed
            fixed = log_ixs[UNITS_LEVEL]
            self.header().setSectionResizeMode(fixed, QHeaderView.Fixed)
            self.header().setStretchLastSection(False)

            # key and type sections can be either Stretch or Interactive
            # Interactive section can be resized programmatically
            if vis_ixs[KEY_LEVEL] > vis_ixs[TYPE_LEVEL]:
                stretch = log_ixs[KEY_LEVEL]
                interactive = log_ixs[TYPE_LEVEL]
            else:
                stretch = log_ixs[TYPE_LEVEL]
                interactive = log_ixs[KEY_LEVEL]

            self.header().setSectionResizeMode(stretch, QHeaderView.Stretch)
            self.header().setSectionResizeMode(interactive, QHeaderView.Interactive)
            self.header().resizeSection(interactive, widths["interactive"])

    def hide_section(self, name: str, hide: bool):
        self.header().setSectionHidden(self.proxy_model.get_logical_index(name), hide)

    def update_appearance(
        self,
        header: Tuple[str, ...] = (TYPE_LEVEL, KEY_LEVEL, UNITS_LEVEL, SOURCE_UNITS),
        widths: Dict[str, int] = None,
        expanded: Set[str] = None,
        filter_tuple: FilterTuple = FilterTuple("", "", ""),
        selected: Optional[List[VariableData]] = None,
        scroll_pos: Optional[int] = None,
        scroll_to: Optional[VariableData] = None,
        hide_source_units: bool = False,
    ) -> None:
        """ Update the model appearance to be consistent with last view. """
        # filter expands all items so it's not required to use expanded set
        if any(filter_tuple) and filter_tuple != self.proxy_model.filter_tuple:
            self.filter_view(filter_tuple)
        elif expanded:
            self.expand_items(expanded)
        # handle custom units column visibility
        self.hide_section(SOURCE_UNITS, hide_source_units)
        # logical and visual indexes may differ so it's needed to update columns order
        self.reorder_columns(header)
        # update widths and order so columns appear consistently
        self.resize_header(widths)
        # TODO handle sort order and scrollbar
        self.update_sort_order()
        # make sure that parent column spans full width
        # and root is decorated for tree like structure
        if self.is_tree:
            self.setFirstTreeColumnSpanned()
            self.setRootIsDecorated(True)
        else:
            self.setRootIsDecorated(False)
        # clear selections to avoid having selected items from previous selection
        self.deselect_all_variables()
        if selected:
            self.select_variables(selected)
        # scroll takes precedence over scrollbar position
        if scroll_to:
            self.scroll_to(scroll_to)
        elif scroll_pos is not None:
            # check explicitly to avoid skipping '0' position
            self.update_scrollbar_position(scroll_pos)

    def set_model(self, table_name: str, **kwargs) -> ViewModel:
        """ Assign new model. """
        model = self.models[table_name]
        model.update_units(**kwargs)
        with SignalBlocker(self.verticalScrollBar()):
            self.proxy_model.setSourceModel(model)
        return model

    def set_and_update_model(
        self, header_df: pd.DataFrame, table_name: str, **kwargs
    ) -> ViewModel:
        model = self.models[table_name]
        model.populate_model(header_df, **kwargs)
        with SignalBlocker(self.verticalScrollBar()):
            self.proxy_model.setSourceModel(model)
        return model

    def update_model(self, header_df: pd.DataFrame, **kwargs) -> ViewModel:
        """ Update tree viw model. """
        self.current_model.populate_model(header_df, **kwargs)
        return self.current_model

    def update_units(self, **kwargs) -> ViewModel:
        """ Update tree viw model. """
        self.current_model.update_units(**kwargs)
        return self.current_model

    def on_item_expanded(self, index: QModelIndex):
        if self.proxy_model.hasChildren(index):
            name = self.proxy_model.data(index)
            self.current_model.expanded.add(name)

    def on_item_collapsed(self, index: QModelIndex):
        with contextlib.suppress(KeyError):
            name = self.proxy_model.data(index)
            self.current_model.expanded.remove(name)

    def on_sort_order_changed(self, log_ix: int, order: Qt.SortOrder) -> None:
        """ Store current sorting order. """
        self.indicator = (log_ix, order)

    def on_view_resized(self, log_ix: int, _, new_size: int) -> None:
        """ Store interactive section width in the main app. """
        if self.header().sectionResizeMode(log_ix) == self.header().Interactive:
            self.viewAppearanceChanged.emit(self.view_type, {"interactive": new_size})

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when first column changed. """
        names = self.get_visual_names()
        self.viewAppearanceChanged.emit(self.view_type, {"header": names})

        # view needs to be updated when the tree structure is applied and first item changes
        if (new_visual_ix == 0 or old_visual_ix == 0) and self.is_tree:
            self.treeNodeChanged.emit(names[0])
            # automatically sort first column based on last sort update
            self.header().setSortIndicator(0, self.proxy_model.sortOrder())

    def on_slider_moved(self, val: int) -> None:
        """ Handle moving view slider. """
        self.current_model.scroll_position = val

    def on_double_clicked(self, index: QModelIndex):
        """ Handle view double click. """
        source_item = self.proxy_model.item_at_index(index)
        if not source_item.hasChildren():
            # parent item cannot be renamed
            if source_item.column() > 0:
                index = index.siblingAtColumn(0)
            variable_data = self.proxy_model.data_at_index(index)
            if variable_data:
                self.itemDoubleClicked.emit(variable_data)

    def _select_children(self, source_item: QStandardItem, source_index: QModelIndex) -> None:
        """ Select all children of the parent row. """
        first_ix = source_index.child(0, 0)
        last_ix = source_index.child((source_item.rowCount() - 1), 0)
        selection = QItemSelection(first_ix, last_ix)
        proxy_selection = self.proxy_model.mapSelectionFromSource(selection)
        self._select_items(proxy_selection)

    def deselect_all_variables(self) -> None:
        """ Deselect all currently selected variables. """
        self.selectionModel().clearSelection()
        self.selectionCleared.emit()

    def select_variables(self, variables: List[VariableData]) -> None:
        """ Select rows with containing given variable data. """
        # Find matching items and select items on a new model
        proxy_selection = self.proxy_model.find_match(variables)
        # select items in view
        self._select_items(proxy_selection)
        proxy_rows = proxy_selection.indexes()
        variables_data = [self.proxy_model.data_at_index(index) for index in proxy_rows]
        if variables_data:
            self.selectionPopulated.emit(variables_data)
        else:
            self.selectionCleared.emit()

    def _deselect_item(self, proxy_index: QModelIndex) -> None:
        """ Select an item programmatically. """
        self.selectionModel().select(
            proxy_index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows
        )

    def _select_items(self, proxy_selection: QItemSelection) -> None:
        """ Select items given by given selection (model indexes). """
        self.selectionModel().select(
            proxy_selection, QItemSelectionModel.Select | QItemSelectionModel.Rows
        )

    def on_pressed(self) -> None:
        """ Handle pressing the view item or items. """
        proxy_rows = self.selectionModel().selectedRows()
        rows = self.proxy_model.map_to_source_lst(proxy_rows)
        if proxy_rows:
            # handle a case in which expanded parent node is clicked
            # note that desired behaviour is to select all the children
            # unless any of the children is included in the multi selection
            for index in proxy_rows:
                source_item = self.proxy_model.item_at_index(index)
                source_index = self.proxy_model.mapToSource(index)
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
            proxy_rows = self.selectionModel().selectedRows()
            variables_data = [self.proxy_model.data_at_index(index) for index in proxy_rows]
            if variables_data:
                self.selectionPopulated.emit(variables_data)
            else:
                self.selectionCleared.emit()
