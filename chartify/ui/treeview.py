from enum import Enum
from typing import Dict, List, Set, Tuple, Optional, Union

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

from chartify.settings import OutputType
from chartify.ui.treeview_model import (
    ViewModel,
    FilterModel,
    PROXY_UNITS_LEVEL,
    convert_variable_data_to_variable,
)
from chartify.utils.utils import (
    FilterTuple,
    VariableData,
)


class ViewType(Enum):
    SIMPLE = "simple"
    TREE = "tree"


class TreeView(QTreeView):
    """ A simple tree view.

    This class should be used altogether with underlying
    'ViewModel' and 'FilterModel' which are
    set up to work with this class.


    Attributes
    ----------
    output_type : OutputType
        An output type of given file.
    model : ModelView
        Linked View Model.

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
    itemDoubleClicked = Signal(QTreeView, int, QModelIndex, VariableData)
    treeNodeChanged = Signal(QTreeView)

    def __init__(self, model: ViewModel, output_type: OutputType):
        super().__init__()
        self.output_type = output_type

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
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)

        self.pressed.connect(self.on_pressed)
        self.doubleClicked.connect(self.on_double_clicked)

        self.header().setStretchLastSection(False)
        self.header().setFirstSectionMovable(True)
        self.header().sectionMoved.connect(self.on_section_moved)

        self.entered.connect(self.on_item_entered)

    @property
    def id_(self) -> int:
        return self.source_model._file_ref.id_

    @property
    def source_model(self) -> ViewModel:
        return self.proxy_model.sourceModel()

    @property
    def proxy_model(self) -> FilterModel:
        return self.model()

    @property
    def view_type(self) -> ViewType:
        return ViewType.SIMPLE if self.source_model.is_simple else ViewType.TREE

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
    def selected_variables(self) -> List[Union[Variable, SimpleVariable]]:
        variables = []
        for variable_data in self.selected_variable_data:
            variable = convert_variable_data_to_variable(variable_data, self.current_table_name)
            variables.append(variable)
        return variables

    @property
    def initialized(self):
        return self.source_model.initialized

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

    def is_similar(self, other_treeview: "TreeView") -> bool:
        return self.source_model.is_similar(other_treeview.source_model)

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

    def get_sort_indicator(self) -> Tuple[int, Qt.SortOrder]:
        """ Get last sorted column and indicator. """
        return self.proxy_model.sortColumn(), self.proxy_model.sortOrder()

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

    def update_sort_order(self, indicator_column: int, order: Qt.SortOrder) -> None:
        """ Sort by given column. """
        self.sortByColumn(indicator_column, order)

    def scroll_to(self, variable_data: VariableData) -> None:
        """ Scroll to the given variable. """
        proxy_selection = self.proxy_model.find_matching_proxy_selection([variable_data])
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

    def get_expanded_labels(self) -> Set[str]:
        """ Get currently expanded item labels. """
        expanded = set()
        if self.source_model.tree_node is not None:
            for i in range(self.proxy_model.rowCount()):
                index = self.proxy_model.index(i, 0)
                if self.isExpanded(index):
                    expanded.add(self.proxy_model.data(index))
        return expanded

    def get_scroll_position(self) -> int:
        return self.verticalScrollBar().sliderPosition()

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
        self.show_all_sections()
        self.header().setSectionHidden(self.source_model.get_logical_column_number(data), hide)

    def set_span_and_decorate_root(self):
        if self.is_tree:
            self.set_parent_items_spanned()
            self.setRootIsDecorated(True)
        else:
            self.setRootIsDecorated(False)

    def update_model(
        self,
        tree_node: Optional[str],
        rate_to_energy: bool,
        units_system: str,
        energy_units: str,
        rate_units: str,
    ) -> None:
        """ Update tree view model. """
        units_kwargs = {
            "rate_to_energy": rate_to_energy,
            "units_system": units_system,
            "energy_units": energy_units,
            "rate_units": rate_units,
        }
        if self.source_model.needs_rebuild(tree_node):
            self.source_model.rebuild_model(tree_node, **units_kwargs)
            self.set_span_and_decorate_root()
        elif self.source_model.needs_units_update(**units_kwargs):
            self.update_proxy_units(**units_kwargs)

    def update_units(self, **kwargs) -> None:
        """ Update tree viw model. """
        self.source_model.update_proxy_units(**kwargs)

    def on_item_entered(self, proxy_index: QModelIndex) -> None:
        """ Set status tip for currently hovered item. """
        source_index = self.proxy_model.mapToSource(proxy_index)
        self.source_model.set_current_status_tip(source_index)

    def tree_node_changed(self, old_visual_ix: int, new_visual_ix: int) -> bool:
        """ Check if tree node column changed. """
        return self.is_tree and (new_visual_ix == 0 or old_visual_ix == 0)

    def on_section_moved(self, _logical_ix, old_visual_ix: int, new_visual_ix: int) -> None:
        """ Handle updating the model when column order changes. """
        if self.tree_node_changed(old_visual_ix, new_visual_ix):
            self.treeNodeChanged.emit(self)
            # automatically sort first column based on last sort update
            self.header().setSortIndicator(0, self.proxy_model.sortOrder())

    def on_double_clicked(self, proxy_index: QModelIndex):
        """ Handle view double click. """
        source_index = self.proxy_model.mapToSource(proxy_index)
        if not self.source_model.hasChildren(source_index):
            row_number = source_index.row()
            parent = source_index.parent()
            variable_data = self.source_model.get_row_variable_data(row_number, parent)
            self.itemDoubleClicked.emit(self, row_number, parent, variable_data)

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

    def get_current_column_data(self, column: str) -> List[str]:
        """ Get all item text for given column. """
        return self.source_model.get_column_data(column)

    def update_variable(
        self, row: int, parent_index: QModelIndex, new_variable_data: VariableData
    ) -> None:
        """ Update text of the variable identified by row and index. """
        self.source_model.update_variable(row, parent_index, new_variable_data)
        self.select_variables([new_variable_data])
        self.scroll_to(new_variable_data)

    def aggregate_variables(
        self,
        view_variables: List[VariableData],
        func: str,
        new_key: str,
        new_type: Optional[str] = None,
    ) -> None:
        """ Update text of the variable identified by row and index. """
        new_variable_data = self.source_model.aggregate_variables(
            view_variables, func, new_key, new_type
        )
        self.deselect_all_variables()
        self.select_variables([new_variable_data])
        self.scroll_to(new_variable_data)


def cache_properties(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        self = args[0]
        treeview = args[1]
        widths = treeview.get_widths()
        header = treeview.get_visual_column_data()
        self.set_cached_property(treeview, "widths", widths)
        self.set_cached_property(treeview, "header", header)
        return res

    return wrapper


class TreeViewAppearance:
    def __init__(
        self, treeview: TreeView,
    ):
        self.view_type = treeview.view_type
        self.header = treeview.get_visual_column_data()
        self.widths = treeview.get_widths()
        self.selected = treeview.get_selected_variable_data()
        self.scroll_position = treeview.get_scroll_position()
        self.expanded = treeview.get_expanded_labels()
        self.sort_indicator = treeview.get_sort_indicator()

    def apply_to(self, treeview: TreeView) -> None:
        treeview.reorder_columns(self.header)
        treeview.set_header_resize_mode(self.widths)
        # TODO handle sort column_order and scrollbar
        treeview.update_sort_order(*self.sort_indicator)
        if self.expanded:
            treeview.expand_items(self.expanded)
        treeview.update_scrollbar_position(self.scroll_position)


class CachedViewAppearance:
    default_header = {
        ViewType.SIMPLE: ("key", "proxy_units", "units"),
        ViewType.TREE: ("type", "key", "proxy_units", "units"),
    }
    default_widths = {
        ViewType.SIMPLE: {"fixed": 60,},
        ViewType.TREE: {"fixed": 60, "interactive": 200},
    }
    default_sort_order = {
        ViewType.SIMPLE: (-1, Qt.SortOrder.AscendingOrder),
        ViewType.TREE: (-1, Qt.SortOrder.AscendingOrder),
    }

    def cache_appearance(self, appearance: TreeViewAppearance):
        self.default_header[appearance.view_type] = appearance.header
        self.default_widths[appearance.view_type] = appearance.widths
        self.default_sort_order[appearance.view_type] = appearance.sort_indicator

    def apply_to(self, treeview: TreeView) -> None:
        treeview.reorder_columns(self.default_header[treeview.view_type])
        treeview.set_header_resize_mode(self.default_widths[treeview.view_type])
        treeview.update_sort_order(*self.default_sort_order[treeview.view_type])


class ViewMask:
    CACHED = {
        OutputType.STANDARD: CachedViewAppearance(),
        OutputType.TOTALS: CachedViewAppearance(),
        OutputType.DIFFERENCE: CachedViewAppearance(),
    }
    DISABLED = False

    def __init__(
        self,
        treeview: TreeView,
        ref_treeview: Optional[TreeView] = None,
        filter_tuple: FilterTuple = FilterTuple("", "", ""),
        show_source_units: bool = True,
    ):
        self.treeview = treeview
        self.appearance = TreeViewAppearance(treeview) if treeview.initialized else None
        self.ref_treeview = ref_treeview
        self.ref_appearance = TreeViewAppearance(ref_treeview) if ref_treeview else None
        self.filter_tuple = filter_tuple
        self.show_source_units = show_source_units

    def __enter__(self):
        if self.appearance is not None:
            self.CACHED[self.treeview.output_type].cache_appearance(self.appearance)
        if self.ref_treeview is not None:
            self.CACHED[self.ref_treeview.output_type].cache_appearance(self.ref_appearance)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.treeview.hide_section(UNITS_LEVEL, not self.show_source_units)
        if any(self.filter_tuple):
            self.treeview.filter_view(self.filter_tuple)

        if self.should_apply_cached():
            self.CACHED[self.treeview.output_type].apply_to(self.treeview)
        elif self.ref_appearance is not None and self.treeview.is_similar(self.ref_treeview):
            self.ref_appearance.apply_to(self.treeview)
        else:
            self.appearance.apply_to(self.treeview)

    def should_apply_cached(self) -> bool:
        return (
            self.DISABLED
            or (self.ref_appearance is None and self.appearance is None)
            or (
                self.ref_appearance is not None
                and not self.treeview.is_similar(self.ref_treeview)
            )
        )

    def get_tree_node(self, treeview: TreeView) -> str:
        return self.CACHED[treeview.output_type].default_header[treeview.view_type][0]

    def update_treeview(
        self, treeview: TreeView, is_tree: bool, units_kwargs: Dict[str, Union[str, bool]]
    ) -> None:
        if is_tree and not treeview.source_model.is_simple:
            tree_node = self.get_tree_node(treeview)
        else:
            tree_node = None
        treeview.update_model(tree_node=tree_node, **units_kwargs)
