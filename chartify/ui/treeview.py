import contextlib
from collections import defaultdict
from functools import partial
from typing import Dict, List, Set, Tuple, Any

from PySide2.QtCore import (
    QMimeData,
    QEvent,
    QItemSelectionModel,
    QItemSelection,
    Signal,
    QModelIndex,
    Qt,
)
from PySide2.QtGui import QDrag, QPixmap
from PySide2.QtWidgets import QTreeView, QAbstractItemView, QHeaderView
from esofile_reader.df.level_names import *
from esofile_reader.typehints import Variable, SimpleVariable

from chartify.ui.treeview_model import ViewModel, FilterModel, PROXY_UNITS_LEVEL
from chartify.ui.widget_functions import SignalBlocker
from chartify.utils.utils import (
    FilterTuple,
    VariableData,
)

SIMPLE = "simple"
TREE = "tree"


class ViewState:
    def __init__(self):
        self.widths = {SIMPLE: {"fixed": 60,}, TREE: {"fixed": 60, "interactive": 200}}
        self.header = {
            SIMPLE: ["key", "proxy_units", "units"],
            TREE: ["type", "key", "proxy_units", "units"],
        }
        self.tree_node = "type"

    def save_interactive_width(self, view_type: str, width: int):
        """ Store current interactive column width. """
        self.widths[view_type]["interactive"] = width

    def save_header_order(self, view_type: str, header: Tuple[str, ...]):
        """ Store current header order. """
        self.header[view_type] = header

    def save_tree_node(self, name: str):
        """ Store current tree node. """
        self.tree_node = name

    def get_header(self, view_type: str):
        return self.header[view_type]

    def get_widths(self, view_type: str):
        return self.widths[view_type]

    def get_tree_node(self):
        return self.view_settings["TREE_NODE"]


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
    treeNodeChanged
        Is emitted if the view uses tree structure changes.

    """

    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(VariableData)
    treeNodeChanged = Signal(str)

    def __init__(self, id_: int, models: Dict[str, ViewModel], output_type: str):
        super().__init__()
        self.id_ = id_
        self.models = models
        self.output_type = output_type
        self.tree_node = None

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
        return SIMPLE if self.source_model.is_simple else TREE

    @property
    def is_tree(self) -> bool:
        return bool(self.source_model.tree_node)

    @property
    def allow_rate_to_energy(self) -> bool:
        if self.source_model:
            return self.source_model.allow_rate_to_energy
        else:
            return True

    @property
    def selected_variable_data(self) -> List[VariableData]:
        return self.get_selected_variable_data()

    @property
    def selected_variables(self) -> List[Variable]:
        variables = []
        for variable_data in self.selected_variable_data:
            variable = (
                SimpleVariable(
                    table=self.current_table_name,
                    key=variable_data.key,
                    units=variable_data.units,
                )
                if self.source_model.is_simple
                else Variable(
                    table=self.current_table_name,
                    key=variable_data.key,
                    type=variable_data.type,
                    units=variable_data.units,
                )
            )
            variables.append(variable)
        return variables

    @property
    def current_table_name(self) -> str:
        return self.source_model.name

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

    def get_widths(self) -> Dict[str, int]:
        """ Get current column interactive and fixed widths. """
        widths = {}
        for i in range(self.header().count()):
            if not self.header().isSectionHidden(i):
                if self.header().sectionResizeMode(i) == QHeaderView.Interactive:
                    widths["interactive"] = self.header().sectionSize(i)
                elif self.header().sectionResizeMode(i) == QHeaderView.Fixed:
                    widths["fixed"] = self.header().sectionSize(i)
        return widths

    def show_all_sections(self):
        """ Make all columns visible. """
        for i in range(self.header().count()):
            self.header().setSectionHidden(i, False)

    def hide_section(self, data: str, hide: bool):
        """ Hide section of a given name. """
        self.header().setSectionHidden(self.source_model.get_logical_column_number(data), hide)

    def set_appearance(
        self, header: Tuple[str, ...], widths: Dict[str, int], hide_source_units: bool = False,
    ) -> None:
        """ Update the model appearance to be consistent with last view. """
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

    def set_model(self, table_name: str, **kwargs) -> None:
        """ Assign new model. """
        model = self.models[table_name]
        model.populate_model(tree_node=self.tree_node, **kwargs)
        with SignalBlocker(self.verticalScrollBar()):
            self.proxy_model.setSourceModel(model)

    def update_model(self, **kwargs) -> None:
        """ Update tree view model. """
        self.source_model.populate_model(tree_node=self.tree_node, **kwargs)

    def update_units(self, **kwargs) -> None:
        """ Update tree viw model. """
        self.source_model.update_proxy_units(**kwargs)

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
        # TODO remove this
        if self.header().sectionResizeMode(log_ix) == self.header().Interactive:
            self.shared_properties.save_interactive_width(self.view_type, new_size)

    def tree_node_changed(self, old_visual_ix: int, new_visual_ix: int) -> bool:
        """ Check if tree node column changed. """
        return self.is_tree and (new_visual_ix == 0 or old_visual_ix == 0)

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when column order changes. """
        if self.tree_node_changed(old_visual_ix, new_visual_ix):
            self.tree_node = self.get_visual_column_data()[0]
            self.treeNodeChanged.emit()
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


class ViewMask:
    _cached = defaultdict(lambda: defaultdict(dict))
    _default = {
        "widths": {SIMPLE: {"fixed": 60,}, TREE: {"fixed": 60, "interactive": 200}},
        "header": {
            SIMPLE: ["key", "proxy_units", "units"],
            TREE: ["type", "key", "proxy_units", "units"],
        },
    }

    def __init__(self, treeview: TreeView, filter_tuple: FilterTuple, hide_source_units: bool):
        self.treeview = treeview
        self.old_model = treeview.source_model
        self.filter_tuple = filter_tuple
        self.hide_source_units = hide_source_units

        self.old_widths = None
        self.old_header = None
        self.old_selected = None

    def __enter__(self):
        if self.old_model is not None:
            self.old_widths = self.treeview.get_widths()
            self.old_header = self.treeview.get_visual_column_data()
            self.old_selected = self.treeview.get_selected_variable_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        is_similar = self.treeview.source_model.is_similar(self.old_model, rows_diff=0.05)
        if is_similar:
            expanded = self.old_model.expanded
            scroll_position = self.old_model.scroll_position
            widths = self.old_widths
            header = self.old_header
            selected = self.old_selected
        else:
            expanded = self.treeview.source_model.expanded
            scroll_position = self.treeview.source_model.scroll_position
            widths = self.get_cached_property("widths")
            header = self.get_cached_property("header")
            selected = self.treeview.get_selected_variable_data()

        self.update_item_visibility(expanded, scroll_position)
        self.treeview.deselect_all_variables()
        if selected:
            self.treeview.select_variables(selected)
        self.treeview.set_appearance(header, widths, self.hide_source_units)
        self.set_cached_property("widths", self.treeview.get_widths())
        self.set_cached_property("header", self.treeview.get_visual_column_data())

    def get_cached_property(self, key: str) -> Any:
        """ Retrieve given property, returns default if not yet cached."""
        try:
            val = self._cached[self.treeview.output_type][key][self.treeview.view_type]
        except KeyError:
            val = self._default[key][self.treeview.view_type]
        return val

    def set_cached_property(self, property: str, value: Any) -> None:
        self._cached[self.treeview.output_type][property][self.treeview.view_type] = value

    def update_item_visibility(self, expanded: Set[str], scroll_position: int):
        """ Show, expand items and scroll to previous position. """
        if (
            any(self.filter_tuple)
            and self.filter_tuple != self.treeview.proxy_model.filter_tuple
        ):
            self.treeview.filter_view(self.filter_tuple)
        # filter expands all items so it's not required to use expanded set
        elif expanded:
            self.treeview.expand_items(expanded)

        if scroll_position is not None:
            # check explicitly to avoid skipping '0' position
            self.treeview.update_scrollbar_position(scroll_position)
