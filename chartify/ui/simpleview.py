from typing import Dict, List, Sequence

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
    QModelIndex,
)
from PySide2.QtGui import QStandardItemModel, QStandardItem, QDrag, QPixmap
from PySide2.QtWidgets import QTreeView, QAbstractItemView, QHeaderView

from chartify.utils.utils import (
    FilterTuple,
    VariableData,
    create_proxy_units_column,
    SignalBlocker,
)


class SimpleModel(QStandardItemModel):
    """ A simple view table model.

    Model only shows two columns 'variable' and 'units'.
    The 'VariableData' named tuple containing variable
    information is stored as 'UserData' on the first
    item in row.

    Source Variables DataFrame must include three columns
    'variable', 'units' and 'source units'.

    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def _append_row(
            parent: QStandardItem,
            row: Sequence[str],
            item_row: List[QStandardItem],
            indexes: Dict[str, int],
    ) -> None:
        """ Append row to the given parent. """
        # assign status tip for all items in row
        variable = row[indexes["variable"]]
        proxy_units = row[indexes["units"]]
        source_units = row[indexes["source units"]]
        status_tip = f"{variable} | {proxy_units}"

        # show all the info for each item in row
        for item in item_row:
            item.setStatusTip(status_tip)

        # first item holds the variable data used for search
        item_row[0].setData(
            VariableData(key="", variable=variable, units=source_units, proxyunits=proxy_units),
            role=Qt.UserRole,
        )

        parent.appendRow(item_row)

    def append_plain_rows(self, variables_df: pd.DataFrame, indexes: Dict[str, int]) -> None:
        for row in variables_df.values:
            item_row = [QStandardItem(item) for item in row[:-1]]
            self._append_row(self, row, item_row, indexes)

    def populate_model(self, variables_df: pd.DataFrame, **kwargs) -> None:
        """  Create a model and set up its appearance. """
        columns = variables_df.columns.tolist()
        indexes = {
            "variable": columns.index("variable"),
            "units": columns.index("units"),
            "source units": columns.index("source units"),
        }
        # create plain table when tree structure not requested
        self.append_plain_rows(variables_df, indexes)


class SimpleFilterModel(QSortFilterProxyModel):
    """ Proxy model to be used with 'SimpleModel' model. """

    def __init__(self):
        super().__init__()
        self._filter_tuple = FilterTuple(key="", variable="", units="")

    @property
    def filter_tuple(self) -> FilterTuple:
        return self._filter_tuple

    @filter_tuple.setter
    def filter_tuple(self, filter_tuple: FilterTuple) -> None:
        self._filter_tuple = filter_tuple
        self.invalidateFilter()

    def get_logical_names(self) -> List[str]:
        """ Get names sorted by logical index. """
        num = self.columnCount()
        return [self.headerData(i, Qt.Horizontal).lower() for i in range(num)]

    def get_logical_index(self, name: str) -> int:
        """ Get a logical index of a given section title. """
        return self.get_logical_names().index(name)

    def get_logical_indexes(self) -> Dict[str, int]:
        """ Return logical positions of header labels. """
        names = self.get_logical_names()
        return {
            "variable": names.index("variable"),
            "units": names.index("units"),
        }

    def data_at_index(self, index: QModelIndex) -> VariableData:
        """ Get item data from source model. """
        return self.item_at_index(index).data(Qt.UserRole)

    def item_at_index(self, index: QModelIndex) -> QStandardItem:
        """ Get item from source model. """
        source_index = self.mapToSource(index)
        return self.sourceModel().itemFromIndex(source_index)

    def map_to_source_lst(self, indexes: List[QModelIndex]) -> List[QModelIndex]:
        """ Map a list of indexes to the source model. """
        return [self.mapToSource(ix) for ix in indexes]

    def filterAcceptsRow(self, source_row: int, source_parent: QStandardItem) -> bool:
        """ Set up filtering rules for the model. """

        def valid():
            if filter_string and val:
                return filter_string.lower() in val.lower()
            else:
                return True

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

                if not valid():
                    # condition fails if any of filter fields does not match
                    return False

            return True

    def find_match(self, variables: List[VariableData], key: str) -> QItemSelection:
        """ Check if output variables are available in a new model. """
        selection = QItemSelection()
        test_variables = [var.variable for var in variables]
        num_rows = self.rowCount()
        for i in range(num_rows):
            p_ix = self.index(i, 0)
            var = self.data_at_index(p_ix)
            if var.variable in test_variables:
                selection.append(QItemSelectionRange(p_ix))

        return selection

    def flags(self, index: QModelIndex) -> None:
        """ Set item flags. """
        if self.hasChildren(index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable


class SimpleView(QTreeView):
    """ A simple table view.

    This class should be used altogether with underlying
    'SimpleModel' and 'SimpleFilterModel' which are
    set up to work with this class.

    Parameters
    ----------
    id_: int
        An id identifier of the base file.

    Attributes
    ----------
    id_ : int
    next_update_forced : bool
        Automatically schedules next full view rebuild.
    is_tree : bool
        Specifies if current view has a tree structure.
    interval : str
        Current view interval.
    rate_to_energy : bool
        Checks if rate is transposed to energy.
    units_system : str
        Current view units system {SI, IP}.
    energy_units : str
        Used energy units.
    power_units : str
        Used power units.
    scrollbar_position : int
        Last scrollbar position.
    indicator : tuple
        Last column index and direction.

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
    viewSettingsChanged
        Is emitted when visual appearance changes.

    """

    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(list)
    viewSettingsChanged = Signal(str, dict)

    def __init__(self, id_: int, model_cls=SimpleModel, proxymodel_cls=SimpleFilterModel):
        super().__init__()
        self.id_ = id_
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

        # create initial view model
        model = model_cls()

        # install proxy model
        proxy_model = proxymodel_cls()
        proxy_model.setSourceModel(model)
        proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        proxy_model.setRecursiveFilteringEnabled(True)
        proxy_model.setDynamicSortFilter(False)
        self.setModel(proxy_model)

        # flag to force next update
        self.next_update_forced = True

        self.is_tree = False
        self.interval = None
        self.rate_to_energy = None
        self.units_system = None
        self.energy_units = None
        self.power_units = None

        # hold ui attributes
        self.scrollbar_position = 0
        self.indicator = (0, Qt.AscendingOrder)

        self.verticalScrollBar().valueChanged.connect(self.on_slider_moved)
        self.pressed.connect(self.on_pressed)
        self.doubleClicked.connect(self.on_double_clicked)

        self.header().setFirstSectionMovable(True)
        self.header().sectionMoved.connect(self.on_section_moved)
        self.header().sortIndicatorChanged.connect(self.on_sort_order_changed)

    @property
    def class_type(self) -> str:
        return self.__class__.__name__.lower()

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

    def filter_view(self, filter_tup: FilterTuple) -> None:
        """ Filter the model using given filter tuple. """
        self.model().filter_tuple = filter_tup

    def get_visual_names(self) -> tuple:
        """ Return sorted column names (by visual index). """
        dct_items = sorted(self.get_visual_indexes().items(), key=lambda x: x[1])
        return tuple([t[0] for t in dct_items])

    def get_visual_indexes(self) -> Dict[str, int]:
        """ Get a dictionary of section visual index pairs. """
        log_ixs = self.model().get_logical_indexes()
        return {k: self.header().visualIndex(i) for k, i in log_ixs.items()}

    def update_view_appearance(
            self, header: tuple = ("variable", "units"), widths: Dict[str, int] = None, **kwargs
    ) -> None:
        """ Update the model appearance to be consistent with last view. """
        # it's required to adjust columns order to match the last applied order
        if not widths:
            widths = {"fixed": 70}

        self.reshuffle_columns(header)

        # resize sections
        self.resize_header(widths)

        # update vertical order
        self.update_sort_order()

        # update slider position
        self.update_scrollbar_position()

    def reshuffle_columns(self, order: tuple):
        """ Reset column positions to match last visual appearance. """
        for i, nm in enumerate(order):
            vis_names = self.get_visual_names()
            j = vis_names.index(nm)
            if i != j:
                self.header().moveSection(j, i)

    def update_scrollbar_position(self):
        """ Set vertical scrollbar position. """
        pos = self.scrollbar_position
        # maximum is sometimes left as '0' which blocks
        # setting position and leaves slider on top
        if self.verticalScrollBar().maximum() < pos:
            self.verticalScrollBar().setMaximum(pos)
        self.verticalScrollBar().setValue(pos)

    def update_sort_order(self) -> None:
        """ Set order for sort column. """
        indicator_column, order = self.indicator
        self.model().sort(indicator_column, order)
        self.header().setSortIndicator(indicator_column, order)

    def scroll_to(self, var: VariableData, first_col: str) -> None:
        """ Scroll to the given variable. """
        proxy_model = self.model()

        # var needs to be passed as a list
        proxy_selection = proxy_model.find_match([var], first_col)

        if proxy_selection:
            self.scrollTo(proxy_selection.indexes()[0])

    def resize_header(self, widths) -> None:
        """ Define resizing behaviour. """
        # units column width is always fixed
        fixed = self.model().get_logical_index("units")
        stretch = self.model().get_logical_index("variable")
        self.header().setSectionResizeMode(fixed, QHeaderView.Fixed)
        self.header().setSectionResizeMode(stretch, QHeaderView.Stretch)
        self.header().setStretchLastSection(False)

        # resize sections programmatically
        self.header().resizeSection(fixed, widths["fixed"])

    def populate_view(
            self,
            variables_df: pd.DataFrame,
            interval: str,
            rate_to_energy: bool = False,
            units_system: str = "SI",
            energy_units: str = "J",
            power_units: str = "W",
            header: tuple = ("variable", "units"),
            **kwargs,
    ) -> None:
        """ Set the model and define behaviour of the tree view. """
        # store current setup as instance attributes
        self.interval = interval
        self.rate_to_energy = rate_to_energy
        self.units_system = units_system
        self.energy_units = energy_units
        self.power_units = power_units
        self.next_update_forced = False

        # deactivate signals as those would override settings
        with SignalBlocker(self.verticalScrollBar()):
            model = self.model().sourceModel()
            model.clear()

            # assign header attributes
            model.setColumnCount(len(header))
            model.setHorizontalHeaderLabels(header)

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
            view_order = header + ("source units",)
            variables_df = variables_df[list(view_order)]

            # feed the data
            model.populate_model(variables_df, **kwargs)

    def on_sort_order_changed(self, log_ix: int, order: Qt.SortOrder) -> None:
        """ Store current sorting order. """
        self.indicator = (log_ix, order)

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when first column changed. """
        names = self.get_visual_names()
        self.viewSettingsChanged.emit(self.class_type, {"header": names})

    def on_slider_moved(self, val: int) -> None:
        """ Handle moving view slider. """
        self.scrollbar_position = val

    def on_double_clicked(self, index: QModelIndex):
        """ Handle view double click. """
        proxy_model = self.model()
        source_item = proxy_model.item_at_index(index)

        if source_item.column() > 0:
            index = index.siblingAtColumn(0)

        # deselect all base variables
        self.deselect_all_variables()

        dt = proxy_model.data_at_index(index)
        if dt:
            self.select_variables([dt])
            self.itemDoubleClicked.emit(dt)

    def on_pressed(self) -> None:
        """ Handle pressing the view item or items. """
        proxy_model = self.model()
        proxy_rows = self.selectionModel().selectedRows()

        variables_data = [proxy_model.data_at_index(index) for index in proxy_rows]

        if variables_data:
            self.selectionPopulated.emit(variables_data)
        else:
            self.selectionCleared.emit()

    def deselect_all_variables(self) -> None:
        """ Deselect all currently selected variables. """
        self.selectionModel().clearSelection()
        self.selectionCleared.emit()

    def select_variables(self, variables: List[VariableData]) -> None:
        """ Select rows with containing given variable data. """
        proxy_model = self.model()
        key = self.get_visual_names()[0]

        # Find matching items and select items on a new model
        proxy_selection = proxy_model.find_match(variables, key)

        # select items in view
        self._select_items(proxy_selection)

        proxy_rows = proxy_selection.indexes()
        variables_data = [proxy_model.data_at_index(index) for index in proxy_rows]

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