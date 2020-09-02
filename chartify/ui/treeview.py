import contextlib
from typing import Dict, List, Set, Optional, Tuple

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
from esofile_reader.convertor import create_conversion_tuples
from esofile_reader.mini_classes import ResultsFileType
from profilehooks import profile

from chartify.utils.utils import (
    FilterTuple,
    VariableData,
    SignalBlocker,
)

PROXY_UNITS_LEVEL = "proxy_units"


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
    name : str
        Usually a name of the original table.
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
    **kwargs
        Key word arguments passed to populate model method.

    """

    def __init__(
        self,
        name: str,
        header_df: pd.DataFrame,
        is_simple: bool = False,
        allow_rate_to_energy: bool = False,
        **kwargs,
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
        self.populate_model(header_df=header_df, **kwargs)

    @classmethod
    def models_from_file(cls, file: ResultsFileType, **kwargs) -> Dict[str, "ViewModel"]:
        """ Process results file to create models. """
        models = {}
        for table_name in file.table_names:
            header_df = file.get_header_df(table_name)
            is_simple = file.is_header_simple(table_name)
            allow_rate_to_energy = file.can_convert_rate_to_energy(table_name)
            models[table_name] = ViewModel(
                table_name, header_df, is_simple, allow_rate_to_energy, **kwargs
            )
        return models

    @staticmethod
    def create_proxy_units_column(
        source_units: pd.Series,
        rate_to_energy: bool,
        units_system: str,
        energy_units: str,
        power_units: str,
    ) -> pd.Series:
        """ Convert original units as defined by given parameters. """
        intermediate_units = source_units.copy()
        if rate_to_energy:
            intermediate_units[intermediate_units == "W"] = "J"
            intermediate_units[intermediate_units == "W/m2"] = "J/m2"
        conversion_tuples = create_conversion_tuples(
            intermediate_units,
            units_system=units_system,
            rate_units=power_units,
            energy_units=energy_units,
        )
        # no units are displayed as dash
        conversion_tuples.append(("", "-", 1))
        old_units, new_units, _ = zip(*conversion_tuples)
        proxy_units = intermediate_units.copy()
        proxy_units.name = PROXY_UNITS_LEVEL
        # populate proxy column with new units
        for old, new in zip(old_units, new_units):
            proxy_units.loc[intermediate_units == old] = new
        return proxy_units

    def count_rows(self) -> int:
        """ Calculate total number of rows (including child rows). """
        count = self.rowCount()
        if not self.is_simple:
            for i in range(self.rowCount()):
                item = self.item(i, 0)
                if item.hasChildren():
                    count += item.rowCount()
        return count

    def is_tree_node_row(self, row_number: int) -> bool:
        """ Check if the row is a parent row. """
        return self.item(row_number, 0).hasChildren()

    def get_display_data_at_index(self, index: QModelIndex):
        """ Get item displayed text. """
        return self.itemFromIndex(index).data(Qt.DisplayRole)

    def get_row_display_data(
        self, row_number: int, parent_index: Optional[QModelIndex] = None
    ) -> List[str]:
        """ Get item text as column name : text dictionary. """
        parent_index = parent_index if parent_index else QModelIndex()
        display_data = []
        for i in range(self.columnCount()):
            index = self.index(row_number, i, parent_index)
            display_data.append(self.get_display_data_at_index(index))
        # child item in first column is displayed as an empty string
        if parent_index.isValid():
            display_data[0] = self.get_display_data_at_index(parent_index)
        return display_data

    def get_row_display_data_mapping(
        self, row_number: int, parent_index: Optional[QModelIndex] = None
    ) -> Dict[str, str]:
        """ Get item text as column data : text dictionary. """
        row_display_data = self.get_row_display_data(row_number, parent_index=parent_index)
        column_mapping = self.get_logical_column_mapping()
        return {k: row_display_data[v] for k, v in column_mapping.items()}

    def get_row_variable_data(
        self, row_number: int, parent_index: Optional[QModelIndex] = None
    ) -> VariableData:
        """ Get row data as eso file Variable or SimpleVariable. """
        row_data_mapping = self.get_row_display_data_mapping(row_number, parent_index)
        return VariableData(
            key=row_data_mapping[KEY_LEVEL],
            type=None if self.is_simple else row_data_mapping[TYPE_LEVEL],
            units=row_data_mapping[UNITS_LEVEL],
        )

    def get_logical_column_data(self) -> List[str]:
        """ Get header data sorted by logical index. """
        return [
            self.headerData(i, Qt.Horizontal, Qt.UserRole) for i in range(self.columnCount())
        ]

    def get_logical_column_number(self, data: str) -> int:
        """ Get a logical index of a given section title. """
        return self.get_logical_column_data().index(data)

    def get_logical_column_mapping(self) -> Dict[str, int]:
        """ Return logical positions of header labels. """
        data = self.get_logical_column_data()
        return {k: data.index(k) for k in data}

    def get_parent_text_from_variables(
        self, variables: List[VariableData]
    ) -> Optional[Set[str]]:
        """ Extract parent part of variable from given list. """
        if self.tree_node and self.tree_node != PROXY_UNITS_LEVEL:
            return {v.__getattribute__(self.tree_node) for v in variables}

    def get_matching_selection(self, variables: List[VariableData]) -> QItemSelection:
        """ Find selection matching given list of variables. """

        def tree_node_matches():
            if self.tree_node == PROXY_UNITS_LEVEL:
                # proxy units are not stored in variable data
                return True
            else:
                parent_text = self.get_display_data_at_index(index)
                return parent_text in variables_parent_text

        def variable_matches():
            return row_variable_data in variables

        # this is used to quickly check if parent matches given list
        # if the parent does not match, any of children cannot match
        # and all the children can be therefore skipped
        variables_parent_text = self.get_parent_text_from_variables(variables)

        selection = QItemSelection()
        for i in range(self.rowCount()):
            index = self.index(i, 0)
            if self.is_tree_node_row(i) and tree_node_matches():
                for j in range(self.rowCount(index)):
                    row_variable_data = self.get_row_variable_data(j, index)
                    if variable_matches():
                        selection.append(QItemSelectionRange(self.index(j, 0, index)))
            else:
                row_variable_data = self.get_row_variable_data(i)
                if variable_matches():
                    selection.append(QItemSelectionRange(index))
        return selection

    def is_similar(self, other_model: "ViewModel", rows_diff: float = 0.05):
        """ Check if number of variables and structure matches the other model. """
        count = self.count_rows()
        diff = (count - other_model.count_rows()) / count
        return self.tree_node == other_model.tree_node and abs(diff) <= rows_diff

    @staticmethod
    def set_item_row_status_tip(status_tip: str, item_row: List[QStandardItem]) -> None:
        """ Set status tip on each item in row. """
        for item in item_row:
            item.setStatusTip(status_tip)

    def append_rows(self, rows: pd.DataFrame) -> None:
        """ Append rows to the root item. """
        column_mapping = self.get_logical_column_mapping()
        for row in rows.values:
            item_row = [QStandardItem(item) for item in row]
            status_tip = self.create_status_tip(row, column_mapping)
            self.set_item_row_status_tip(status_tip, item_row)
            self.invisibleRootItem().appendRow(item_row)

    def append_child_rows(self, parent: QStandardItem, rows: pd.DataFrame) -> None:
        """ Append rows to given parent item. """
        column_mapping = self.get_logical_column_mapping()
        for row in rows.values:
            # first standard item is empty to avoid having parent string in the child row
            item_row = [QStandardItem("")]
            for item in row[1:]:
                item_row.append(QStandardItem(item))
            status_tip = self.create_status_tip(row, column_mapping)
            self.set_item_row_status_tip(status_tip, item_row)
            parent.appendRow(item_row)

    def append_tree_rows(self, header_df: pd.DataFrame) -> None:
        """ Add rows for a tree like view. """
        grouped = header_df.groupby(by=[header_df.columns[0]])
        for parent, df in grouped:
            if len(df.index) == 1:
                self.append_rows(df)
            else:
                parent_item = QStandardItem(parent)
                parent_item.setDragEnabled(False)
                self.invisibleRootItem().appendRow(parent_item)
                self.append_child_rows(parent_item, df)

    def create_status_tip(
        self, row_display_data: List[str], column_mapping: Dict[str, int]
    ) -> str:
        """ Create status tip string. """
        key = row_display_data[column_mapping[KEY_LEVEL]]
        type_ = row_display_data[column_mapping[TYPE_LEVEL]] if not self.is_simple else None
        proxy_units = row_display_data[column_mapping[PROXY_UNITS_LEVEL]]
        if type_ is not None:
            status_tip = f"{key} | {type_} | {proxy_units}"
        else:
            status_tip = f"{key} | {proxy_units}"
        return status_tip

    def set_row_status_tip(
        self, status_tip: str, row_number: int, parent_index: Optional[QModelIndex] = None
    ) -> None:
        """ Set status tip on each item in row. """
        parent_index = parent_index if parent_index else QModelIndex()
        for column_number in range(self.columnCount()):
            index = self.index(row_number, column_number, parent_index)
            item = self.itemFromIndex(index)
            item.setStatusTip(status_tip)

    def set_row_text_as_status_tip(self):
        """ Apply status tip for each row in the model. """
        column_mapping = self.get_logical_column_mapping()
        for i in range(self.rowCount()):
            if self.is_tree_node_row(row_number=i):
                index = self.index(i, 0)
                for j in range(self.rowCount(index)):
                    row_display_data = self.get_row_display_data(j, index)
                    status_tip = self.create_status_tip(row_display_data, column_mapping)
                    self.set_row_status_tip(status_tip, j, index)
            else:
                row_display_data = self.get_row_display_data(i)
                status_tip = self.create_status_tip(row_display_data, column_mapping)
                self.set_row_status_tip(status_tip, i)

    def process_header_df(
        self,
        header_df: pd.DataFrame,
        rate_to_energy: bool,
        units_system: str,
        energy_units: str,
        power_units: str,
    ) -> pd.DataFrame:
        """ Process variables header DataFrame to be compatible with treeview model. """
        # id and table data are not required
        header_df = header_df.drop([ID_LEVEL, TABLE_LEVEL], axis=1)

        # add proxy units - these will be visible on ui
        header_df[PROXY_UNITS_LEVEL] = self.create_proxy_units_column(
            source_units=header_df[UNITS_LEVEL],
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            power_units=power_units,
        )
        if self.tree_node:
            # tree column needs to be first
            new_columns = header_df.columns.tolist()
            new_columns.insert(0, new_columns.pop(new_columns.index(self.tree_node)))
            header_df = header_df.loc[:, new_columns]
        return header_df

    def set_column_header_item_data(self, header_data: List[str]):
        """ Assign names to the horizontal header. """
        names = {
            KEY_LEVEL: "key",
            TYPE_LEVEL: "type",
            UNITS_LEVEL: "source units",
            PROXY_UNITS_LEVEL: "units",
        }
        for i, data in enumerate(header_data):
            item = QStandardItem()
            item.setData(data, Qt.UserRole)
            item.setData(names[data], Qt.DisplayRole)
            self.setHorizontalHeaderItem(i, item)

    @profile
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
        header_df = self.process_header_df(
            header_df,
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            power_units=power_units,
        )
        self.set_column_header_item_data(header_df.columns.tolist())
        if self.tree_node:
            self.append_tree_rows(header_df)
        else:
            self.append_rows(header_df)

    def create_conversion_look_up_table(
        self,
        source_units: pd.Series,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        power_units: str = "W",
    ) -> Optional[Dict[str, str]]:
        proxy_units = self.create_proxy_units_column(
            source_units,
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            power_units=power_units,
        )
        df = pd.concat([source_units, proxy_units], axis=1)
        # create look up dictionary with source units as keys and proxy units as values
        df.drop_duplicates(inplace=True)
        df = df.loc[df[UNITS_LEVEL] != df[PROXY_UNITS_LEVEL], :]
        if not df.empty:
            df.set_index(UNITS_LEVEL, inplace=True)
            return df.squeeze().to_dict()

    def update_proxy_units_parent_item(
        self, row_number: int, conversion_look_up: Dict[str, str],
    ) -> None:
        """ Update proxy units parent item accordingly to conversion lok up. """
        parent_index = self.index(row_number, 0)
        first_child_row_data = self.get_row_display_data_mapping(0, parent_index)
        source_units = first_child_row_data[UNITS_LEVEL]
        proxy_units = conversion_look_up.get(source_units, source_units)
        proxy_units_item = self.item(row_number, 0)
        proxy_units_item.setData(proxy_units, Qt.DisplayRole)

    def update_proxy_units_parent_column(self, conversion_look_up: Dict[str, str]):
        """ Update proxy units parent column accordingly to conversion look up. """
        for i in range(self.rowCount()):
            if self.is_tree_node_row(row_number=i):
                self.update_proxy_units_parent_item(i, conversion_look_up)
            else:
                self.update_proxy_units_item(i, 0, conversion_look_up, QModelIndex())

    def update_proxy_units_item(
        self,
        row_number: int,
        column_number: int,
        conversion_look_up: Dict[str, str],
        parent_index: QModelIndex,
    ) -> None:
        """ Update proxy units item accordingly to conversion pairs and source units. """
        row_mapping = self.get_row_display_data_mapping(row_number, parent_index)
        source_units = row_mapping[UNITS_LEVEL]
        proxy_units_item = self.itemFromIndex(
            self.index(row_number, column_number, parent_index)
        )
        proxy_units = conversion_look_up.get(source_units, source_units)
        proxy_units_item.setData(proxy_units, Qt.DisplayRole)

    def update_proxy_units_column(self, conversion_look_up: Dict[str, str]) -> None:
        """ Update proxy units column accordingly to conversion pairs and source units. """
        proxy_units_column_number = self.get_logical_column_number(PROXY_UNITS_LEVEL)
        for i in range(self.rowCount()):
            index = self.index(i, 0)
            if self.hasChildren(index):
                for j in range(self.rowCount(index)):
                    self.update_proxy_units_item(
                        j, proxy_units_column_number, conversion_look_up, index
                    )
            else:
                self.update_proxy_units_item(
                    i, proxy_units_column_number, conversion_look_up, QModelIndex()
                )

    @profile
    def update_proxy_units(
        self,
        source_units: pd.Series,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        power_units: str = "W",
    ):
        """ Update proxy units column. """
        self.rate_to_energy = rate_to_energy
        self.units_system = units_system
        self.energy_units = energy_units
        self.power_units = power_units
        conversion_look_up = self.create_conversion_look_up_table(
            source_units, rate_to_energy, units_system, energy_units, power_units
        )
        if conversion_look_up:
            if self.tree_node == PROXY_UNITS_LEVEL:
                self.update_proxy_units_parent_column(conversion_look_up)
            else:
                self.update_proxy_units_column(conversion_look_up)


class FilterModel(QSortFilterProxyModel):
    """ Proxy model to be used with 'SimpleModel' model. """

    def __init__(self):
        super().__init__()
        self._filter_tuple = FilterTuple(key="", type="", proxy_units="")

    @property
    def filter_tuple(self) -> FilterTuple:
        return self._filter_tuple

    @filter_tuple.setter
    def filter_tuple(self, filter_tuple: FilterTuple) -> None:
        self._filter_tuple = filter_tuple
        self.invalidateFilter()

    def data_at_proxy_index(self, proxy_index: QModelIndex) -> VariableData:
        """ Get item data from source model. """
        return self.item_at_proxy_index(proxy_index).data(Qt.UserRole)

    def item_at_proxy_index(self, proxy_index: QModelIndex) -> QStandardItem:
        """ Get item from source model. """
        source_index = self.mapToSource(proxy_index)
        return self.sourceModel().itemFromIndex(source_index)

    def map_to_source(self, indexes: List[QModelIndex]) -> List[QModelIndex]:
        """ Map a list of indexes to the source model. """
        return [self.mapToSource(ix) for ix in indexes]

    def filter_matches_row(self, row_data_mapping: Dict) -> bool:
        """ Check if current filter tuple matches row display data. """
        row_data_to_filter = {k: v for k, v in row_data_mapping.items() if k != UNITS_LEVEL}
        for field_name, item_text in row_data_to_filter.items():
            filter_text = self.filter_tuple.__getattribute__(field_name)
            filter_text = filter_text.strip()
            if filter_text:
                if filter_text.lower() not in item_text.lower():
                    return False
        return True

    def filterAcceptsRow(self, source_row_number: int, source_parent: QModelIndex) -> bool:
        """ Set up filtering rules for the model. """
        if not any(self.filter_tuple):
            return True
        # first item can be either parent for 'tree' structure or a normal item
        # parent rows can be excluded as valid items are displayed due to recursive filter
        if source_parent.isValid():
            row_data_mapping = self.sourceModel().get_row_display_data_mapping(
                source_row_number, source_parent
            )
            return self.filter_matches_row(row_data_mapping)
        return False

    def find_matching_proxy_selection(self, variables: List[VariableData]) -> QItemSelection:
        """ Check if output variables are available in a new model. """
        source_selection = self.sourceModel().get_matching_selection(variables)
        return self.mapSelectionFromSource(source_selection)

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
    viewColumnResized
        Is emitted when 'interactive' column width changes.
    viewColumnOrderChanged
        Is emitted when header column_order changes.
    viewTreeNodeChanged
        Is emitted if the view uses tree structure changes.

    """

    SIMPLE = "simple"
    TREE = "tree"

    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(VariableData)
    viewColumnResized = Signal(str, int)
    viewColumnOrderChanged = Signal(str, tuple)
    viewTreeNodeChanged = Signal(str)

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
    def source_model(self) -> ViewModel:
        return self.proxy_model.sourceModel()

    @property
    def proxy_model(self) -> FilterModel:
        return self.model()

    @property
    def view_type(self) -> str:
        return self.SIMPLE if self.source_model.is_simple else self.TREE

    @property
    def is_tree(self) -> bool:
        return bool(self.source_model.tree_node)

    @property
    def allow_rate_to_energy(self) -> bool:
        if self.source_model:
            return self.source_model.allow_rate_to_energy
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

    def set_parent_items_spanned(self) -> None:
        """ Set parent row to be spanned over all columns. """
        for i in range(self.proxy_model.rowCount()):
            if self.proxy_model.hasChildren(self.proxy_model.index(i, 0)):
                super().setFirstColumnSpanned(i, self.rootIndex(), True)

    def filter_view(self, filter_tuple: FilterTuple) -> None:
        """ Filter the model using given filter tuple. """
        self.proxy_model.filter_tuple = filter_tuple
        if self.is_tree:
            # Expand all items when filter is applied
            self.expandAll()
            # it's required to reapply column span after each filter
            self.set_parent_items_spanned()

    def get_visual_column_data(self) -> Tuple[str, ...]:
        """ Return sorted column data (by visual index). """
        dct_items = sorted(self.get_visual_column_mapping().items(), key=lambda x: x[1])
        return tuple([t[0] for t in dct_items])

    def get_visual_column_mapping(self) -> Dict[str, int]:
        """ Get a dictionary of section visual index pairs. """
        logical_mapping = self.source_model.get_logical_column_mapping()
        return {k: self.header().visualIndex(i) for k, i in logical_mapping.items()}

    def reorder_columns(self, column_order: Tuple[str, ...]):
        """ Reset column positions to match last visual appearance. """
        for i, name in enumerate(column_order):
            vis_indexes = self.get_visual_column_mapping()
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
        self.source_model.scroll_position = pos

    def update_sort_order(self) -> None:
        """ Set column_order for sort column. """
        indicator_column, order = self.indicator
        self.proxy_model.sort(indicator_column, order)
        self.header().setSortIndicator(indicator_column, order)

    def scroll_to(self, vd: VariableData) -> None:
        """ Scroll to the given variable. """
        proxy_selection = self.proxy_model.find_matching_proxy_selection([vd])
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

    def set_header_resize_mode(self, widths: Dict[str, int]) -> None:
        """ Define resizing behaviour. """
        # units column width is always fixed
        proxy_units_index = self.source_model.get_logical_column_number(PROXY_UNITS_LEVEL)
        source_units_index = self.source_model.get_logical_column_number(UNITS_LEVEL)

        self.header().setSectionResizeMode(proxy_units_index, QHeaderView.Fixed)
        self.header().setSectionResizeMode(source_units_index, QHeaderView.Fixed)
        self.header().setStretchLastSection(False)

        self.header().resizeSection(proxy_units_index, widths["fixed"])
        self.header().resizeSection(source_units_index, widths["fixed"])

        if self.source_model.is_simple:
            stretch = self.source_model.get_logical_column_number(KEY_LEVEL)
            self.header().setSectionResizeMode(stretch, QHeaderView.Stretch)
        else:
            log_ixs = self.source_model.get_logical_column_mapping()
            vis_ixs = self.get_visual_column_mapping()

            # units column width is always fixed
            fixed = log_ixs[PROXY_UNITS_LEVEL]
            self.header().setSectionResizeMode(fixed, QHeaderView.Fixed)

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

    def show_all_sections(self):
        """ Make all columns visible. """
        for i in range(self.header().count()):
            self.header().setSectionHidden(i, False)

    def hide_section(self, data: str, hide: bool):
        """ Hide section of a given name. """
        self.header().setSectionHidden(self.source_model.get_logical_column_number(data), hide)

    def update_appearance(
        self,
        header: Tuple[str, ...] = (TYPE_LEVEL, KEY_LEVEL, PROXY_UNITS_LEVEL, UNITS_LEVEL),
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
        # handle custom units column visibility, need to show all
        # as switching between simple and tree view may cause that
        # another section will be hidden
        self.show_all_sections()
        self.hide_section(UNITS_LEVEL, hide_source_units)
        # logical and visual indexes may differ so it's needed to update columns column_order
        self.reorder_columns(header)
        # update widths and column_order so columns appear consistently
        self.set_header_resize_mode(widths)
        # TODO handle sort column_order and scrollbar
        self.update_sort_order()
        # make sure that parent column spans full width
        # and root is decorated for tree like structure
        if self.is_tree:
            self.set_parent_items_spanned()
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

    def set_model(self, table_name: str) -> None:
        """ Assign new model. """
        model = self.models[table_name]
        with SignalBlocker(self.verticalScrollBar()):
            self.proxy_model.setSourceModel(model)

    def set_and_update_model(self, header_df: pd.DataFrame, table_name: str, **kwargs) -> None:
        model = self.models[table_name]
        model.populate_model(header_df, **kwargs)
        with SignalBlocker(self.verticalScrollBar()):
            self.proxy_model.setSourceModel(model)

    def update_model(self, header_df: pd.DataFrame, **kwargs) -> None:
        """ Update tree viw model. """
        self.source_model.populate_model(header_df, **kwargs)

    def update_units(self, source_units: pd.Series, **kwargs) -> None:
        """ Update tree viw model. """
        self.source_model.update_proxy_units(source_units, **kwargs)

    def on_item_expanded(self, proxy_index: QModelIndex):
        if self.proxy_model.hasChildren(proxy_index):
            name = self.proxy_model.data(proxy_index)
            self.source_model.expanded.add(name)

    def on_item_collapsed(self, proxy_index: QModelIndex):
        with contextlib.suppress(KeyError):
            name = self.proxy_model.data(proxy_index)
            self.source_model.expanded.remove(name)

    def on_sort_order_changed(self, log_ix: int, order: Qt.SortOrder) -> None:
        """ Store current sorting column_order. """
        self.indicator = (log_ix, order)

    def on_view_resized(self, log_ix: int, _, new_size: int) -> None:
        """ Store interactive section width in the main app. """
        if self.header().sectionResizeMode(log_ix) == self.header().Interactive:
            self.viewColumnResized.emit(self.view_type, new_size)

    def tree_node_changed(self, old_visual_ix: int, new_visual_ix: int) -> bool:
        """ Check if tree node column changed. """
        return self.is_tree and (new_visual_ix == 0 or old_visual_ix == 0)

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when column order changes. """
        names = self.get_visual_column_data()
        self.viewColumnOrderChanged.emit(self.view_type, names)
        if self.tree_node_changed(old_visual_ix, new_visual_ix):
            self.viewTreeNodeChanged.emit(names[0])
            # automatically sort first column based on last sort update
            self.header().setSortIndicator(0, self.proxy_model.sortOrder())

    def on_slider_moved(self, val: int) -> None:
        """ Handle moving view slider. """
        self.source_model.scroll_position = val

    def on_double_clicked(self, proxy_index: QModelIndex):
        """ Handle view double click. """
        source_index = self.proxy_model.mapToSource(proxy_index)
        if not self.source_model.hasChildren(source_index):
            row_number = source_index.row()
            row_variable_data = self.source_model.get_row_variable_data(
                row_number, source_index.parent()
            )
            self.itemDoubleClicked.emit(row_variable_data)

    def select_all_children(self, source_index: QModelIndex) -> None:
        """ Select all children of the parent row. """
        first_index = source_index.child(0, 0)
        last_index = source_index.child((self.source_model.rowCount(source_index) - 1), 0)
        source_selection = QItemSelection(first_index, last_index)
        self.select_model_items(source_selection)

    def deselect_all_variables(self) -> None:
        """ Deselect all currently selected variables. """
        self.selectionModel().clearSelection()
        self.selectionCleared.emit()

    def select_variables(self, variables: List[VariableData]) -> None:
        """ Select rows with containing given variable data. """
        source_selection = self.source_model.get_matching_selection(variables)
        if source_selection.indexes():
            self.select_model_items(source_selection)
            variable_data = self.get_selected_variable_data()
            self.selectionPopulated.emit(variable_data)

    def deselect_item(self, source_index: QModelIndex) -> None:
        """ Deselect an item programmatically. """
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.selectionModel().select(
            proxy_index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows
        )

    def select_model_items(self, source_selection: QItemSelection) -> None:
        """ Select items given by given selection (model indexes). """
        proxy_selection = self.proxy_model.mapSelectionFromSource(source_selection)
        self.selectionModel().select(
            proxy_selection, QItemSelectionModel.Select | QItemSelectionModel.Rows
        )

    def can_select_all_children(
        self, parent_source_index: QModelIndex, selected_source_indexes: List[QModelIndex]
    ) -> bool:
        """ Check if all child items should be selected on parent click. """
        is_any_child_selected = any(
            map(lambda x: x.parent() == parent_source_index, selected_source_indexes)
        )
        parent_proxy_index = self.proxy_model.mapFromSource(parent_source_index)
        return self.isExpanded(parent_proxy_index) and not is_any_child_selected

    def get_selected_variable_data(self) -> List[VariableData]:
        """ Get currently selected variable data. """
        proxy_row_indexes = self.selectionModel().selectedRows()
        source_row_indexes = self.proxy_model.map_to_source(proxy_row_indexes)
        variable_data = []
        for source_index in source_row_indexes:
            row_number = source_index.row()
            if not self.source_model.hasChildren(source_index):
                row_variable_data = self.source_model.get_row_variable_data(
                    row_number, source_index.parent()
                )
                variable_data.append(row_variable_data)
        return variable_data

    def update_parent_selection(self, source_row_indexes: List[QModelIndex]) -> None:
        """
        Update parent item selection.

        Desired behaviour is to select all the children unless
        any of the children is already included in the multi-selection

        """
        for source_index in source_row_indexes:
            if self.source_model.hasChildren(source_index):
                # select all the children if the item is expanded
                # and none of its children has been already selected
                if self.can_select_all_children(source_index, source_row_indexes):
                    self.select_all_children(source_index)
                # deselect all the parent nodes as these should not be
                # included in output variable data
                self.deselect_item(source_index)

    def on_pressed(self) -> None:
        """ Handle pressing the view item or items. """
        proxy_row_indexes = self.selectionModel().selectedRows()
        source_row_indexes = self.proxy_model.map_to_source(proxy_row_indexes)
        self.update_parent_selection(source_row_indexes)
        variable_data = self.get_selected_variable_data()
        if variable_data:
            self.selectionPopulated.emit(variable_data)
        else:
            self.selectionCleared.emit()
