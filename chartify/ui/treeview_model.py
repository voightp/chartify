import contextlib
from collections import namedtuple
from typing import Dict, Optional, List, Set, Tuple

import pandas as pd
from PySide2.QtCore import (
    QModelIndex,
    Qt,
    QItemSelection,
    QItemSelectionRange,
    QSortFilterProxyModel,
)
from PySide2.QtGui import QStandardItemModel, QStandardItem
from esofile_reader import get_results
from esofile_reader.convertor import can_convert_rate_to_energy, create_conversion_dict
from esofile_reader.df.level_names import (
    KEY_LEVEL,
    TYPE_LEVEL,
    UNITS_LEVEL,
    ID_LEVEL,
    TABLE_LEVEL,
)
from esofile_reader.exceptions import CannotAggregateVariables
from esofile_reader.results_processing.table_formatter import TableFormatter
from esofile_reader.typehints import ResultsFileType, Variable, SimpleVariable, VariableType

PROXY_UNITS_LEVEL = "proxy_units"

ViewVariable = namedtuple("VV", "key type units")
FilterTuple = namedtuple("FilterTuple", ["key", "type", "proxy_units"])
VV = ViewVariable


def stringify_view_variable(view_variable: VV) -> str:
    return " | ".join([v for v in view_variable if v is not None])


def convert_view_variable_to_variable(view_variable: VV, table_name: str) -> VariableType:
    return (
        SimpleVariable(table=table_name, key=view_variable.key, units=view_variable.units)
        if view_variable.type is None
        else Variable(
            table=table_name,
            key=view_variable.key,
            type=view_variable.type,
            units=view_variable.units,
        )
    )


def convert_variable_to_view_variable(variable: VariableType) -> VV:
    return VV(
        key=variable.key,
        type=variable.type if isinstance(variable, Variable) else None,
        units=variable.units,
    )


def convert_view_variables_to_variables(
    view_variables: List[VV], table_name: str
) -> List[VariableType]:
    return [convert_view_variable_to_variable(v, table_name) for v in view_variables]


def is_variable_attr_identical(view_variables: List[VV], attr: str) -> bool:
    """ Check if all variables use the same attribute text. """
    first_attr = view_variables[0].__getattribute__(attr)
    return all(map(lambda x: x.__getattribute__(attr) == first_attr, view_variables))


def order_view_variable_by_header(view_variable: VV, column_data: List[str]) -> List[str]:
    """ Transform view variable to list sorted by column order. """
    return [
        view_variable.__getattribute__(name)
        for name in column_data
        if name != PROXY_UNITS_LEVEL
    ]


class FileModelMismatch(Exception):
    """ Raised when variable is included in file but not in view or vice versa. """

    pass


class ViewModel(QStandardItemModel):
    """ View models allowing 'tree' like structure.

    Model can show up to four columns 'key', 'type', units' and
    'source units'. 'Type' column is optional.

    Tree items which would only have one child are automatically
    treated as plain table rows.

    Attributes
    ----------
    name : str
        A name of the original table.
    tree_node : str
        Current tree column node, may be 'None' for
        plain table structure.
    rate_to_energy : bool
        Checks if rate is transposed to energy.
    units_system : str
        Current view units system {SI, IP}.
    energy_units : str
        Used energy units.
    rate_units : str
        Used power units.
    _file_ref : ResultFileType
        A reference to source file.

    """

    def __init__(self, name: str, file_ref: ResultsFileType):
        super().__init__()
        self.name = name
        self.tree_node = None
        self.rate_to_energy = False
        self.units_system = "SI"
        self.energy_units = "J"
        self.rate_units = "W"
        self._file_ref = file_ref

    @property
    def is_simple(self) -> bool:
        return self._file_ref.is_header_simple(self.name)

    @property
    def allow_rate_to_energy(self) -> bool:
        return can_convert_rate_to_energy(self._file_ref, self.name)

    @property
    def header_df(self) -> pd.DataFrame:
        return self._file_ref.get_header_df(self.name)

    @property
    def initialized(self) -> bool:
        return self.columnCount() != 0

    def get_column_data(self, column: str) -> List[str]:
        """ Get all column items. """
        return self.header_df.loc[:, column]

    def count_rows(self) -> int:
        """ Calculate total number of rows (including child rows). """
        count = self.rowCount()
        if not self.is_simple:
            for i in range(self.rowCount()):
                item = self.item(i, 0)
                if item.hasChildren():
                    count += item.rowCount()
        return count

    def needs_rebuild(self, tree_node: Optional[str]) -> bool:
        """ Check if the model needs full update. """
        required = True
        if self.initialized:
            if self.is_simple:
                required = False
            else:
                required = self.tree_node != tree_node
        return required

    def needs_units_update(
        self, energy_units: str, rate_units: str, units_system: str, rate_to_energy: bool
    ) -> bool:
        """ Check if the model needs to update units. """
        return any(
            [
                self.energy_units != energy_units,
                self.rate_units != rate_units,
                self.units_system != units_system,
                (self.rate_to_energy != rate_to_energy) if self.allow_rate_to_energy else False,
            ]
        )

    def get_display_data_at_index(self, index: QModelIndex):
        """ Get item displayed text. """
        if index.parent().isValid() and index.column() == 0:
            data = self.itemFromIndex(index.parent()).data(Qt.DisplayRole)
        else:
            data = self.itemFromIndex(index).data(Qt.DisplayRole)
        return data

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
        column_indexes = self.get_logical_column_indexes()
        return {k: row_display_data[v] for k, v in column_indexes.items()}

    def get_row_view_variable(
        self, row_number: int, parent_index: Optional[QModelIndex] = None
    ) -> VV:
        """ Get row data as eso file Variable or SimpleVariable. """
        row_data_mapping = self.get_row_display_data_mapping(row_number, parent_index)
        return VV(
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

    def get_logical_column_indexes(self) -> Dict[str, int]:
        """ Return logical positions of header labels, ordered by values. """
        data = self.get_logical_column_data()
        return dict(sorted({k: data.index(k) for k in data}.items(), key=lambda x: x[0]))

    def get_parent_text_from_variables(self, variables: List[VV]) -> Optional[Set[str]]:
        """ Extract parent part of variable from given list. """
        if self.tree_node and self.tree_node != PROXY_UNITS_LEVEL:
            return {v.__getattribute__(self.tree_node) for v in variables}

    def is_tree_node_row(self, row_number: int) -> bool:
        """ Check if the row is a parent row. """
        return self.item(row_number, 0).hasChildren()

    def find_check_columns(self) -> Tuple[str, List[str]]:
        column_data = self.get_logical_column_data()
        if column_data[0] == PROXY_UNITS_LEVEL:
            first_check_column = column_data[1]
            second_check_columns = column_data[2:]
        else:
            first_check_column = column_data[0]
            second_check_columns = [c for c in column_data[1:] if c != PROXY_UNITS_LEVEL]
        return first_check_column, second_check_columns

    def get_matching_selection(self, view_variables: List[VV]) -> QItemSelection:
        first_check_column, second_check_columns = self.find_check_columns()
        column_indexes = self.get_logical_column_indexes()
        first_check_column_number = column_indexes[first_check_column]
        second_check_column_numbers = [column_indexes[name] for name in second_check_columns]
        column_data = self.get_logical_column_data()
        selection = QItemSelection()
        for view_variable in view_variables:
            ordered = order_view_variable_by_header(view_variable, column_data)
            first_check = ordered[0]
            second_check = ordered[1:]
            if self.tree_node == PROXY_UNITS_LEVEL:
                items = [self.item(i, 0) for i in range(self.rowCount())]
            else:
                items = self.findItems(first_check, column=first_check_column_number)

            for item in items:
                index = self.indexFromItem(item)
                if self.hasChildren(index):
                    for i in range(item.rowCount()):
                        child_items = [item.child(i, j) for j in second_check_column_numbers]
                        child_text = [child_item.text() for child_item in child_items]
                        if child_text == second_check:
                            child_index = self.indexFromItem(child_items[0])
                            selection.append(QItemSelectionRange(child_index))
                else:
                    text = [
                        self.data(self.index(index.row(), j))
                        for j in second_check_column_numbers
                    ]
                    if text == second_check:
                        selection.append(QItemSelectionRange(index))
        return selection

    def is_similar(self, other_model: Optional["ViewModel"], rows_diff: float = 0.05):
        """ Check if number of variables and structure matches the other model. """
        similar = False
        if other_model is not None:
            if self is other_model:
                similar = False
            else:
                count = self.count_rows()
                diff = (count - other_model.count_rows()) / count
                similar = self.tree_node == other_model.tree_node and abs(diff) <= rows_diff
        return similar

    def append_rows(self, rows: pd.DataFrame) -> None:
        """ Append rows to the root item. """
        for row in rows.values:
            item_row = [QStandardItem(item) for item in row]
            self.invisibleRootItem().appendRow(item_row)

    def append_child_rows(self, parent: QStandardItem, rows: pd.DataFrame) -> None:
        """ Append rows to given parent item. """
        for row in rows.values:
            # first standard item is empty to avoid having parent string in the child row
            item_row = [QStandardItem("")]
            for item in row[1:]:
                item_row.append(QStandardItem(item))
            parent.appendRow(item_row)

    def append_tree_rows(self, header_df: pd.DataFrame) -> None:
        """ Add rows for a tree like view. """
        grouped = header_df.groupby(by=[header_df.columns[0]], sort=False)
        for parent, df in grouped:
            if len(df.index) == 1:
                self.append_rows(df)
            else:
                parent_item = QStandardItem(parent)
                parent_item.setDragEnabled(False)
                self.invisibleRootItem().appendRow(parent_item)
                self.append_child_rows(parent_item, df)

    def create_status_tip_from_row(self, row_display_data: List[str]) -> str:
        """ Create status tip string from row text. """
        column_indexes = self.get_logical_column_indexes()
        key = row_display_data[column_indexes[KEY_LEVEL]]
        type_ = row_display_data[column_indexes[TYPE_LEVEL]] if not self.is_simple else None
        proxy_units = row_display_data[column_indexes[PROXY_UNITS_LEVEL]]
        if type_ is None:
            status_tip = f"{key} | {proxy_units}"
        else:
            status_tip = f"{key} | {type_} | {proxy_units}"
        return status_tip

    @staticmethod
    def create_proxy_units_column(
        source_units: pd.Series,
        rate_to_energy: bool,
        units_system: str,
        energy_units: str,
        rate_units: str,
    ) -> pd.Series:
        """ Convert original units as defined by given parameters. """
        intermediate_units = source_units.copy()
        if rate_to_energy:
            intermediate_units[intermediate_units == "W"] = "J"
            intermediate_units[intermediate_units == "W/m2"] = "J/m2"
        conversion_dict = create_conversion_dict(
            intermediate_units,
            units_system=units_system,
            rate_units=rate_units,
            energy_units=energy_units,
        )
        # no units are displayed as dash
        conversion_dict[""] = ("-", 1)
        proxy_units = intermediate_units.copy()
        proxy_units.name = PROXY_UNITS_LEVEL
        # populate proxy column with new units
        for old, v in conversion_dict.items():
            proxy_units.loc[intermediate_units == old] = v[0]
        return proxy_units

    def create_tree_compatible_header_df(
        self, rate_to_energy: bool, units_system: str, energy_units: str, rate_units: str,
    ) -> pd.DataFrame:
        """ Process variables header DataFrame to be compatible with treeview model. """
        # id and table data are not required
        header_df = self.header_df.drop([ID_LEVEL, TABLE_LEVEL], axis=1)

        # add proxy units - these will be visible on ui
        header_df[PROXY_UNITS_LEVEL] = self.create_proxy_units_column(
            source_units=header_df[UNITS_LEVEL],
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            rate_units=rate_units,
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

    def rebuild_model(
        self,
        tree_node: Optional[str] = None,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        rate_units: str = "W",
    ) -> None:
        """  Create a model and set up its appearance. """
        if self.rowCount() > 0:
            self.clear()

        # tree node data is always None for 'Simple' views
        tree_node = tree_node if not self.is_simple else None
        rate_to_energy = rate_to_energy if self.allow_rate_to_energy else False

        self.tree_node = tree_node
        self.rate_to_energy = rate_to_energy
        self.units_system = units_system
        self.energy_units = energy_units
        self.rate_units = rate_units
        header_df = self.create_tree_compatible_header_df(
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            rate_units=rate_units,
        )
        column_labels = header_df.columns.tolist()
        header_df = header_df.sort_values(by=column_labels, ascending=True)
        self.set_column_header_item_data(column_labels)
        if self.tree_node:
            self.append_tree_rows(header_df)
        else:
            self.append_rows(header_df)

    def create_conversion_look_up_table(
        self,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        rate_units: str = "W",
    ) -> Dict[str, str]:
        source_units = self.header_df[UNITS_LEVEL]
        proxy_units = self.create_proxy_units_column(
            source_units,
            rate_to_energy=rate_to_energy,
            units_system=units_system,
            energy_units=energy_units,
            rate_units=rate_units,
        )
        df = pd.concat([source_units, proxy_units], axis=1)
        # create look up dictionary with source units as keys and proxy units as values
        df.drop_duplicates(inplace=True)
        df.set_index(UNITS_LEVEL, inplace=True)
        return df.loc[:, PROXY_UNITS_LEVEL].to_dict()

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
        row: int,
        proxy_column: int,
        source_column: int,
        conversion_look_up: Dict[str, str],
        parent_index: QModelIndex,
    ) -> None:
        """ Update proxy units item accordingly to conversion pairs and source units. """
        source_units = self.get_display_data_at_index(
            self.index(row, source_column, parent_index)
        )
        proxy_units_item = self.itemFromIndex(self.index(row, proxy_column, parent_index))
        proxy_units = conversion_look_up.get(source_units, source_units)
        proxy_units_item.setData(proxy_units, Qt.DisplayRole)

    def update_proxy_units_column(self, conversion_look_up: Dict[str, str]) -> None:
        """ Update proxy units column accordingly to conversion pairs and source units. """
        proxy_units_column_number = self.get_logical_column_number(PROXY_UNITS_LEVEL)
        source_units_column_number = self.get_logical_column_number(UNITS_LEVEL)
        for i in range(self.rowCount()):
            index = self.index(i, 0)
            if self.hasChildren(index):
                for j in range(self.rowCount(index)):
                    self.update_proxy_units_item(
                        j,
                        proxy_units_column_number,
                        source_units_column_number,
                        conversion_look_up,
                        index,
                    )
            else:
                self.update_proxy_units_item(
                    i,
                    proxy_units_column_number,
                    source_units_column_number,
                    conversion_look_up,
                    QModelIndex(),
                )

    def update_proxy_units(
        self,
        rate_to_energy: bool = False,
        units_system: str = "SI",
        energy_units: str = "J",
        rate_units: str = "W",
    ):
        """ Update proxy units column. """
        rate_to_energy = rate_to_energy if self.allow_rate_to_energy else False
        self.rate_to_energy = rate_to_energy
        self.units_system = units_system
        self.energy_units = energy_units
        self.rate_units = rate_units

        conversion_look_up = self.create_conversion_look_up_table(
            rate_to_energy, units_system, energy_units, rate_units
        )
        if self.tree_node == PROXY_UNITS_LEVEL:
            self.update_proxy_units_parent_column(conversion_look_up)
        else:
            self.update_proxy_units_column(conversion_look_up)

    def set_current_status_tip(self, index: QModelIndex) -> None:
        if not self.hasChildren(index):
            row = index.row()
            parent = index.parent()
            display_data = self.get_row_display_data(row, parent)
            status_tip = self.create_status_tip_from_row(display_data)
            item = self.itemFromIndex(index)
            item.setStatusTip(status_tip)

    def variable_tree_node_text_changed(
        self, new_view_variable: VV, old_view_variable: [VV]
    ) -> bool:
        """ Check if text of the 'tree' columns has changed. """
        name = new_view_variable.__getattribute__(self.tree_node)
        old_name = old_view_variable.__getattribute__(self.tree_node)
        return name != old_name

    def delete_row_from_model(self, row: int, parent_index: Optional[QModelIndex]) -> None:
        """ Delete given row from model. """
        self.removeRow(row, parent_index)

    def get_row_text(self, view_variable: VV) -> List[str]:
        """ Get variable data attributes ordered following column order. """
        proxy_units = self.create_proxy_units_column(
            pd.Series([view_variable.units]),
            rate_to_energy=self.rate_to_energy,
            units_system=self.units_system,
            energy_units=self.energy_units,
            rate_units=self.rate_units,
        ).iloc[0]
        unordered_items = {**view_variable._asdict(), PROXY_UNITS_LEVEL: proxy_units}
        if self.is_simple:
            unordered_items.pop(TYPE_LEVEL)
        row = [""] * len(unordered_items)
        for column, index in self.get_logical_column_indexes().items():
            row[index] = unordered_items[column]
        return row

    def add_row_to_model(self, view_variable: VV) -> None:
        """ Add row to the model. """
        row_text = self.get_row_text(view_variable)
        if self.tree_node is not None:
            tree_items = self.findItems(row_text[0], flags=Qt.MatchExactly, column=0)
            if tree_items:
                parent = tree_items[0]
                row_text[0] = ""
                parent.appendRow([QStandardItem(text) for text in row_text])
            else:
                self.appendRow([QStandardItem(text) for text in row_text])
        else:
            self.appendRow([QStandardItem(text) for text in row_text])

    def update_row(self, view_variable: VV, row: int, parent_index: QModelIndex,) -> None:
        """ Set text on the given row. """
        row_text = self.get_row_text(view_variable)
        if parent_index.isValid():
            row_text[0] = ""
        for i, text in enumerate(row_text):
            item = self.itemFromIndex(self.index(row, i, parent_index))
            item.setText(text)

    def update_variable_in_model(
        self,
        old_view_variable: VV,
        new_variable: VariableType,
        row: int,
        parent_index: QModelIndex,
    ) -> None:
        new_view_variable = convert_variable_to_view_variable(new_variable)
        if self.tree_node is not None and self.variable_tree_node_text_changed(
            new_view_variable, old_view_variable
        ):
            self.delete_row_from_model(row, parent_index)
            self.add_row_to_model(new_view_variable)
        else:
            self.update_row(new_view_variable, row, parent_index)

    def update_variable_in_file(
        self, old_view_variable: VV, new_key: str, new_type: Optional[str]
    ) -> VariableType:
        old_variable = convert_view_variable_to_variable(old_view_variable, self.name)
        res = self._file_ref.rename_variable(old_variable, new_key, new_type)
        if res is not None:
            return res[1]

    def update_variable(self, row: int, parent_index: QModelIndex, view_variable: VV) -> None:
        """ Update row identified by row and parent index. """
        old_view_variable = self.get_row_view_variable(row, parent_index)
        new_variable = self.update_variable_in_file(
            old_view_variable, view_variable.key, view_variable.type
        )
        if new_variable:
            self.update_variable_in_model(old_view_variable, new_variable, row, parent_index)

    def update_variable_if_exists(self, old_view_variable: VV, view_variable: VV,) -> None:
        """ Update row identified by VV. """
        old_variable = convert_view_variable_to_variable(old_view_variable, self.name)
        if self._file_ref.search_tree.variable_exists(old_variable):
            new_variable = self.update_variable_in_file(
                old_view_variable, view_variable.key, view_variable.type
            )
            if self.initialized and new_variable:
                indexes = self.get_matching_selection([view_variable]).indexes()
                row = indexes[0].row()
                parent = indexes[0].parent()
                self.update_variable_in_model(old_view_variable, new_variable, row, parent)

    def delete_rows_from_model(self, view_variables: List[VV]):
        """ Delete given variables from model. """
        for selection_range in self.get_matching_selection(view_variables):
            parent = selection_range.parent()
            self.removeRows(selection_range.top(), selection_range.height(), parent)
            if parent.isValid() and not self.hasChildren(parent):
                self.removeRow(parent.row())

    def delete_variables(self, view_variables: List[VV]) -> None:
        """ Delete given variables. """
        self._file_ref.remove_variables(
            convert_view_variables_to_variables(view_variables, self.name)
        )
        if self.initialized:
            self.delete_rows_from_model(view_variables)

    def aggregate_variables(
        self, view_variables: List[VV], func: str, new_key: str, new_type: Optional[str] = None,
    ) -> VV:
        variables = convert_view_variables_to_variables(view_variables, self.name)
        with contextlib.suppress(CannotAggregateVariables):
            _, variable = self._file_ref.aggregate_variables(variables, func, new_key, new_type)
            view_variable = convert_variable_to_view_variable(variable)
            if self.initialized:
                self.add_row_to_model(view_variable)
            return view_variable

    def get_results(
        self,
        view_variables: List[VV],
        units_system: str,
        rate_units: str,
        energy_units: str,
        rate_to_energy: bool,
    ) -> pd.DataFrame:
        variables = convert_view_variables_to_variables(view_variables, self.name)
        formatter = TableFormatter(
            file_name_position="column",
            include_table_name=True,
            include_day=False,
            include_id=False,
            timestamp_format="default",
        )
        return get_results(
            self._file_ref,
            variables,
            units_system=units_system,
            rate_units=rate_units,
            energy_units=energy_units,
            rate_to_energy=rate_to_energy,
            table_formatter=formatter,
        )

    def variable_exists(self, view_variable: VariableType) -> bool:
        """ Check if given variable exists in reference model and view. """
        variable = convert_view_variable_to_variable(view_variable, self.name)
        file_check = self._file_ref.search_tree.variable_exists(variable)
        if self.initialized:
            selection = self.get_matching_selection([view_variable])
            ui_check = bool(selection.indexes())
            if ui_check is file_check:
                return ui_check
            else:
                raise FileModelMismatch(
                    f"Variable '{variable}' is included in {'view model' if ui_check else 'file'}"
                    f" but not in  {'file' if ui_check else 'view model'}."
                )
        else:
            return file_check

    def variables_exist(self, view_variables: List[VariableType]) -> List[bool]:
        """ Check if given variables exists in reference model and view. """
        return [self.variable_exists(v) for v in view_variables]


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

    def data_at_proxy_index(self, proxy_index: QModelIndex) -> VV:
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

    def find_matching_proxy_selection(self, variables: List[VV]) -> QItemSelection:
        """ Check if output variables are available in a new model. """
        source_selection = self.sourceModel().get_matching_selection(variables)
        return self.mapSelectionFromSource(source_selection)

    def flags(self, index: QModelIndex) -> None:
        """ Set item flags. """
        if self.hasChildren(index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable
