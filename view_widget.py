import sys
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QWidget, QTabWidget, QTreeView, QSplitter, QHBoxLayout, QVBoxLayout, \
    QGridLayout, QToolButton, QSizePolicy, QLayout, QLabel, QGroupBox, QRadioButton, QToolBar, \
    QMenuBar, QAction, \
    QFileDialog, QDialog, QProgressBar, QFormLayout, QAbstractItemView, QSlider, QSpacerItem, \
    QSizePolicy, QLineEdit, QComboBox, QMdiArea, QHeaderView, QTableView, QApplication, QScrollArea
from PySide2.QtCore import QSize, Qt, QThreadPool, QThread, QObject, Signal, \
    QSortFilterProxyModel, QModelIndex, QItemSelectionModel, QRegExp, QUrl, QAbstractItemModel, \
    QItemSelection, QTimer, QItemSelectionRange, QSignalBlocker, QMimeData, QMimeType, QByteArray
from PySide2.QtGui import QDrag, QPixmap
import pickle

from PySide2.QtGui import QStandardItemModel, QStandardItem, QFont
from eso_file_header import EsoFileHeader


class View(QTreeView):
    units_section_width = 70

    def __init__(self, main_app, file_id, eso_file_header):
        super().__init__()
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)

        self.setDragEnabled(False)
        self.setWordWrap(False)  # not working at the moment
        self.setAlternatingRowColors(False)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.NoFocus)

        self.main_app = main_app
        self.eso_file_header = eso_file_header
        self._file_id = file_id

        self._initialized = False
        self._interval = None
        self._tree_key = None
        self._units_settings = None
        self._view_settings = None
        self._scrollbar_position = 0

        self.expanded.connect(self.handle_expanded)
        self.collapsed.connect(self.handle_collapsed)
        self.pressed.connect(self.handle_drag_attempt)
        self.verticalScrollBar().valueChanged.connect(self.slider_moved)

    @property
    def file_id(self):
        return self._file_id

    def filter_view(self, filter_str):
        """ Filter the model using given string. """
        model = self.model()
        model.setRecursiveFilteringEnabled(True)
        model.setFilterFixedString(filter_str)

        # Expand all items when filter is applied
        self.expand_all()
        self._set_first_col_spanned()

    def _store_interval(self, new_interval):
        """ Hold a value of the last interval settings. """
        self._interval = new_interval

    def _store_tree_key(self, new_key):
        """ Hold a value of the last grouping settings. """
        self._tree_key = new_key

    def _store_units_settings(self, new_units):
        """ Hold a data on the last units settings. """
        self._units_settings = new_units

    def expand_all(self):
        """ Expand all nested nodes. """
        self.expandAll()

    def collapse_all(self):
        """ Collapse all nested nodes. """
        self.collapseAll()

    def _set_first_col_spanned(self):
        """ Set parent row to be spanned over all columns. """
        model = self.model()
        for i in range(model.rowCount()):
            ix = model.index(i, 0)
            if model.hasChildren(ix):
                self.setFirstColumnSpanned(i, self.rootIndex(), True)

    def create_view_model(self, eso_file_header, units_settings,
                          tree_key, view_order, interval):
        """
        Create a model and set up its appearance.
        """
        model = ViewModel()
        model.populate_data(eso_file_header, units_settings,
                            tree_key, view_order, interval)

        proxy_model = FilterModel()
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)

        # define view appearance and behaviour
        self._set_header_labels(view_order)
        self._set_first_col_spanned()

        if not self._initialized:
            # create header actions only when view is created
            self._create_header_actions()
            self._initialized = True

    def _shuffle_columns(self, order):
        """ Reset column positions to match last visual appearance. """
        header = self.header()

        for i, nm in enumerate(order):
            vis_names = self._get_visual_names()
            j = vis_names.index(nm)
            if i != j:
                header.moveSection(j, i)

    def _update_sort_order(self, name, order):
        """ Set header order. """
        log_ix = self._get_logical_index(name)
        self.header().setSortIndicator(log_ix, order)

    def _expand_items(self, expanded_set):
        """ Expand items which were previously expanded (on other models). """
        model = self.model()
        for i in range(model.rowCount()):
            ix = model.index(i, 0)
            if model.hasChildren(ix):
                data = model.data(ix)
                if data in expanded_set:
                    self.expand(ix)

    def _update_selection(self, current_selection, tree_key):
        """ Select previously selected items when the model changes. """
        # Clear the container
        self.main_app.clear_current_selection()

        # Find matching items and return selection
        proxy_selection = self.model().find_match(current_selection,
                                                  tree_key=tree_key)
        # Select items on the new model
        self.select_items(proxy_selection)

        # Update main app outputs
        proxy_indexes = proxy_selection.indexes()
        self.update_app_outputs(proxy_indexes)

    def update_scroll_position(self):
        """ Update the slider position. """
        val = self._scrollbar_position
        self.verticalScrollBar().setValue(val)

    def update_view_appearance(self, view_settings):
        """ Update the model appearance to be consistent with last view. """
        sort_order = view_settings["order"]
        expanded_items = view_settings["expanded"]
        view_order = view_settings["header"]

        self.update_resize_behaviour()
        self.resize_header()
        self._update_sort_order(*sort_order)
        self.update_scroll_position()

        if expanded_items:
            self._expand_items(expanded_items)

        # it's required to adjust columns order to match the last applied order
        # the problematic part is updating tree structure as the logical indexes
        # change which causes the order to be broken
        self._shuffle_columns(view_order)

    def update_view_model(self, is_tree, interval, view_settings,
                          units_settings, select=None):
        """
        Set the model and define behaviour of the tree view.
        """
        eso_file_header = self.eso_file_header

        view_order = view_settings["header"]
        tree_key = view_order[0] if is_tree else None

        # Only update the model if the settings have changed
        conditions = [tree_key != self._tree_key,
                      interval != self._interval,
                      units_settings != self._units_settings, ]

        if any(conditions):
            self.create_view_model(eso_file_header, units_settings,
                                   tree_key, view_order, interval)

            # Store current sorting key and interval
            self._store_tree_key(tree_key)
            self._store_interval(interval)
            self._store_units_settings(units_settings)

        # clean up selection as this will be handled based on
        # currently selected list of items stored in main app
        self.clear_selection()
        if select:
            self._update_selection(select, tree_key)

        self.update_view_appearance(view_settings)

    def _set_header_labels(self, view_order):
        """ Assign header labels. """
        model = self.model().sourceModel()
        model.setHorizontalHeaderLabels(view_order)

    def resize_header(self):
        """ Update header sizes. """
        header = self.header()
        widths = self.main_app.stored_view_settings["widths"]
        interactive = widths["interactive"]
        fixed = widths["fixed"]

        for i in range(header.count()):
            mode = header.sectionResizeMode(i)
            if mode == header.Interactive:
                header.resizeSection(i, interactive)
            elif mode == header.Fixed:
                header.resizeSection(i, fixed)

    def update_resize_behaviour(self):
        """ Define resizing behaviour. """
        header = self.header()

        # both logical and visual indexes are ordered as 'key', 'variable', 'units
        log_ixs = self._get_logical_ixs()
        vis_ixs = [self.header().visualIndex(i) for i in log_ixs]

        # units column size is always fixed
        header.setSectionResizeMode(log_ixs[2], QHeaderView.Fixed)
        header.setStretchLastSection(False)

        if vis_ixs[0] > vis_ixs[1]:
            stretch = log_ixs[0]
            interactive = log_ixs[1]

        else:
            stretch = log_ixs[1]
            interactive = log_ixs[0]

        header.setSectionResizeMode(stretch, QHeaderView.Stretch)
        header.setSectionResizeMode(interactive, QHeaderView.Interactive)

    def _get_logical_names(self):
        """ Get names sorted by logical index. """
        model = self.model()
        num = model.columnCount()
        names = [model.headerData(i, Qt.Horizontal).lower() for i in range(num)]
        return names

    def _get_visual_names(self):
        """ Return sorted column names (by visual index). """
        num = self.model().columnCount()
        names = self._get_logical_names()
        vis_ixs = [self.header().visualIndex(i) for i in range(num)]

        z = list(zip(names, vis_ixs))
        z.sort(key=lambda x: x[1])
        sorted_names = list(zip(*z))[0]
        return sorted_names

    def _get_logical_index(self, name):
        """ Get a logical index of a given section title. """
        names = self._get_logical_names()
        return names.index(name)

    def _get_logical_ixs(self):
        """ Return logical positions of header labels. """
        names = self._get_logical_names()
        return (names.index("key"),
                names.index("variable"),
                names.index("units"))

    def _sort_order_changed(self, log_ix, order):
        """ Store current sorting order in main app. """
        name = self.model().headerData(log_ix, Qt.Horizontal)
        self.main_app.update_sort_order(name, order)

    def _view_resized(self):
        """ Store interactive section width in the main app. """
        header = self.header()
        for i in range(3):
            if header.sectionResizeMode(i) == header.Interactive:
                width = header.sectionSize(i)
                self.main_app.update_section_widths("interactive", width)

    def _section_moved(self, _logical_ix, old_visual_ix, new_visual_ix):
        """ Handle updating the model when first column changed. """
        names = self._get_visual_names()
        self.main_app.update_sections_order(names)

        if (new_visual_ix == 0 or old_visual_ix == 0) and self.main_app.is_tree():
            # need to update view as section has been moved
            # onto first position and tree key is applied
            print("Updating view")
            self.main_app.update_view()
            self._update_sort_order(names[0], Qt.AscendingOrder)

        self.update_resize_behaviour()
        self.resize_header()

    def _create_header_actions(self):
        """ Create header actions. """
        # When the file is loaded for the first time the header does not
        # contain required data to use 'view_resized' method.
        # Due to this, the action needs to be created only after the model
        # and its header has been created.
        self.header().setFirstSectionMovable(True)
        self.header().sectionResized.connect(self._view_resized)
        self.header().sortIndicatorChanged.connect(self._sort_order_changed)
        self.header().sectionMoved.connect(self._section_moved)

    def slider_moved(self, val):
        """ Handle moving view slider. """
        self._scrollbar_position = val

    def fetch_request(self):
        """ Get currently requested outputs. """
        file_ids, variables = self.main_app.current_request()
        return file_ids, variables

    def handle_drag_attempt(self):
        """ Handle pressing the view item or items. """
        # update selection
        self.handle_selection_change()
        file_ids, variables = self.fetch_request()

        if not variables:
            return

        print("HANDLING DRAG!\n{}".format(file_ids))
        print(variables)

        mimeData = QMimeData()
        mimeData.setText("HELLO FROM MAIN APP")
        pixmap = QPixmap("./icons/input.png")
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(pixmap)
        drag.exec_(Qt.CopyAction)
        # create a drag object with pixmap

    def handle_selection_change(self):
        """ Extract output information from the current selection. """
        print("Selection changed")
        proxy_model = self.model()
        selection_model = self.selectionModel()
        proxy_rows = selection_model.selectedRows()
        rows = proxy_model.map_to_source_lst(proxy_rows)

        if not proxy_rows:
            # break if there isn't any valid variable
            self.main_app.clear_current_selection()
            return

        # handle a case in which expanded parent node is clicked
        # note that desired behaviour is to select all the children
        # unless any of the children is included in the multi selection
        for index in proxy_rows:
            source_item = proxy_model.item_from_index(index)
            source_index = proxy_model.mapToSource(index)

            if source_item.hasChildren():
                expanded = self.isExpanded(index)

                if expanded and not any(map(lambda x: x.parent() == source_index, rows)):
                    self.select_children(source_item, source_index)

                # deselect all the parent nodes as these should not be
                # included in output variable data
                self.deselect_item(index)

        # updated selection
        proxy_rows = selection_model.selectedRows()
        self.update_app_outputs(proxy_rows)

    def update_app_outputs(self, proxy_indexes):
        """ Update outputs in the main app. """
        outputs = []
        proxy_model = self.model()

        for index in proxy_indexes:
            item = proxy_model.item_from_index(index)
            data = item.data(Qt.UserRole)
            outputs.append(data)

        if outputs:
            self.main_app.populate_current_selection(outputs)

        else:
            self.main_app.clear_current_selection()

    def select_children(self, source_item, source_index):
        """ Select all children of the parent row. """
        first_ix = source_index.child(0, 0)
        last_ix = source_index.child((source_item.rowCount() - 1), 0)
        selection = QItemSelection(first_ix, last_ix)
        proxy_selection = self.model().mapSelectionFromSource(selection)
        self.select_items(proxy_selection)

    def clear_selection(self):
        """ Clear all selected rows. """
        self.selectionModel().clearSelection()  # Note that this emits selectionChanged signal

    def deselect_item(self, proxy_index):
        """ Select an item programmatically. """
        self.selectionModel().select(proxy_index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)

    def select_item(self, proxy_index):
        """ Select an item programmatically. """
        self.selectionModel().select(proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def select_items(self, proxy_selection):
        """ Select items given by given selection (model indexes). """
        self.selectionModel().select(proxy_selection,
                                     QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def handle_state_change(self, name, collapsed=False):
        self.main_app.update_expanded_set(name, remove=collapsed)

    def handle_collapsed(self, index):
        """ Deselect the row when node collapses."""
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            self.handle_state_change(name, collapsed=True)

    def handle_expanded(self, index):
        """ Deselect the row when node is expanded. """
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            self.handle_state_change(name)


class ViewModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setSortRole(Qt.AscendingOrder)

    def mimeTypes(self):
        # TODO Double check if this is working
        return "application/json"

    @staticmethod
    def _append_rows(header_iterator, parent):
        """ Add plain rows to the model. """
        for data, proxy in header_iterator:
            i0 = QStandardItem(None)
            i0.setData(data, Qt.UserRole)  # First item in row holds all the information
            i1, i2 = QStandardItem(proxy[1]), QStandardItem(proxy[2])
            parent.appendRow([i0, i1, i2])

    @staticmethod
    def _append_plain_rows(header_iterator, parent):
        """ Add plain rows to the model. """
        for data, proxy in header_iterator:
            item_row = [QStandardItem(item) for item in proxy]
            item_row[0].setData(data, Qt.UserRole)  # First item in row holds all the information
            parent.appendRow(item_row)

    def _append_tree_rows(self, tree_header, root):
        """ Add rows for a tree like view. """
        for k, variables in tree_header.items():

            if len(variables) == 1:
                # append as a plain row
                self._append_plain_rows(variables, root)

            else:
                parent = QStandardItem(k)
                parent.setDragEnabled(False)
                root.appendRow(parent)
                self._append_rows(variables, parent)

    def populate_data(self, eso_file_header, units_settings, tree_key, view_order, interval):
        """ Feed the model with output variables. """
        root = self.invisibleRootItem()
        header = eso_file_header.get_header_iterator(units_settings, view_order, interval)

        if not tree_key:
            # tree like structure is not being used
            # append as a plain table
            self._append_plain_rows(header, root)

        else:
            # create a tree like structure
            tree_header = EsoFileHeader.tree_header(header, tree_key)
            self._append_tree_rows(tree_header, root)


class FilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()

    def item_from_index(self, index):
        """ Get item from source model. """
        source_index = self.mapToSource(index)
        return self.sourceModel().itemFromIndex(source_index)

    def map_to_source_lst(self, indexes):
        """ Map a list of indexes to the source model. """
        if not isinstance(indexes, list):
            indexes = [indexes]
        return [self.mapToSource(ix) for ix in indexes]

    def map_from_source_lst(self, indexes):
        """ Map a list of source indexes to the proxy model. """
        if not isinstance(indexes, list):
            indexes = [indexes]
        return [self.mapFromSource(ix) for ix in indexes]

    def filterAcceptsRow(self, source_row, source_parent):
        """ Set up filtering rules for the model. """
        source_model = self.sourceModel()

        if self.filterRegExp().pattern() in ["", " ", "\t"]:
            return True

        ix0 = source_model.index(source_row, 0, source_parent)
        ix1 = source_model.index(source_row, 1, source_parent)

        if self.sourceModel().data(ix1) is None:
            return False  # Exclude parent nodes (these are enabled due to recursive filter)

        else:
            item = source_model.itemFromIndex(ix0)
            data = item.data(Qt.UserRole)
            return self.filter_expression(data)

    def filter_expression(self, data):
        """ Check if input string matches a variable. """
        str_row = " ".join(data)
        filter = self.filterRegExp()
        pattern = filter.pattern().strip()
        return pattern.lower() in str_row.lower()

    @staticmethod
    def append_item(selection, proxy_index):
        """ Append an item to a given selection. """
        range = QItemSelectionRange(proxy_index)
        selection.append(range)

    def find_match(self, current_selection, tree_key=None):
        """ Check if output variables are available in a new model. """
        selection = QItemSelection()

        if not tree_key:
            # there isn't any preferred sorting applied so the first column is 'key'
            tree_key = "key"

        # create a list which holds parent parts of currently selected items
        # if the part of variable does not match, than the variable (or any children)
        # will not be selected
        quick_check = [var.__getattribute__(tree_key) for var in current_selection]

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
                    item = self.item_from_index(ix)
                    var = item.data(Qt.UserRole)
                    if var in current_selection:
                        self.append_item(selection, ix)
            else:
                item = self.item_from_index(p_ix)
                var = item.data(Qt.UserRole)
                if var in current_selection:
                    self.append_item(selection, p_ix)

        return selection

    def flags(self, index):
        """ Set item flags. """
        if self.hasChildren(index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable
