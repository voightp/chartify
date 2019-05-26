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


def output_piece(variable, identifier):
    """ Identify and return a part of variable for given identifier.  """
    return variable.__getattribute__(identifier)


class GuiEsoFile(QTreeView):
    def __init__(self, main_app, file_id, eso_file_header):
        super().__init__()
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setUniformRowHeights(True)
        self.setWordWrap(False)  # not working at the moment
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setDragEnabled(False)
        self.setSortingEnabled(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.NoFocus)

        self.main_app = main_app
        self.eso_file_header = eso_file_header
        self._file_id = file_id
        self._interval = None
        self._group_by = None

        self.expanded.connect(self.handle_expanded)
        self.collapsed.connect(self.handle_collapsed)
        self.pressed.connect(self.handle_drag_attempt)

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

    def _store_interval(self, current_interval):
        """ Hold a value of the last interval settings. """
        self._interval = current_interval

    def _store_group_by_key(self, current_key):
        """ Hold a value of the last interval settings. """
        self._group_by = current_key

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

    def _set_ascending_order(self):
        """ Set first column sort order to be 'ascending'. """
        self.sortByColumn(0, Qt.AscendingOrder)

    def create_view_model(self, eso_file_header, group_by_key,
                          interval_request, is_fresh=False):
        """
        Create a model and set up its appearance.
        """
        model = MyModel(eso_file_header,
                        group_by_key=group_by_key,
                        interval_request=interval_request)

        proxy_model = MyFilterModel()
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)

        # define view appearance and behaviour
        self._set_header_labels(group_by_key)
        self._set_resize_behaviour(group_by_key)
        self._set_first_col_spanned()
        self._set_ascending_order()

        if is_fresh:
            # create header actions (only once)
            self._create_header_actions()

    def _update_sort_order(self, index, order):
        """ Set header order. """
        self.header().setSortIndicator(index, order)

    def _expand_items(self, expanded_set):
        """ Expand items which were previously expanded (on other models). """
        model = self.model()
        for i in range(model.rowCount()):
            ix = model.index(i, 0)
            if model.hasChildren(ix):
                data = model.data(ix)
                if data in expanded_set:
                    self.expand(ix)

    def _update_selection(self, current_selection, group_by_key):
        """ Select previously selected items when the model changes. """
        # Clear the container
        self.main_app.clear_current_selection()

        # Find matching items and return selection
        proxy_selection = self.model().find_match(current_selection,
                                                  group_by_key=group_by_key)
        # Select items on the new model
        self.select_items(proxy_selection)

        # Update main app outputs
        proxy_indexes = proxy_selection.indexes()
        self.update_app_outputs(proxy_indexes)

    def update_view_model(self, group_by_key, interval_request, view_settings,
                          units_settings, select=None, is_fresh=False):
        """
        Set the model and define behaviour of the tree view.
        """

        eso_file_header = self.eso_file_header
        column_width_dct = view_settings["widths"]
        sort_order = view_settings["order"]
        expanded_items = view_settings["expanded"]

        if group_by_key != self._group_by or interval_request != self._interval:
            # Only update the model if the settings have been changed
            self.create_view_model(eso_file_header, group_by_key,
                                   interval_request, is_fresh=is_fresh)

        if column_width_dct:
            self._resize_columns(column_width_dct)

        # clean up selection as this will be handled based on
        # currently selected list of items stored in main app
        self.clear_selection()
        if select:
            self._update_selection(select, group_by_key)

        if expanded_items:
            self._expand_items(expanded_items)

        if sort_order:
            self._update_sort_order(*sort_order)

        # Store current sorting key and interval
        self._store_group_by_key(group_by_key)
        self._store_interval(interval_request)

    def _set_header_labels(self, group_by_key):
        """ Assign header labels. """
        model = self.model().sourceModel()
        column_labels_dct = {"key": "Key", "variable": "Variable", "units": "Units"}
        labels = list(column_labels_dct.values())

        if group_by_key != "raw":
            # switch labels to reflect the arrange key input
            parent_label = column_labels_dct.pop(group_by_key)
            labels.remove(parent_label)
            labels.insert(0, parent_label)

        model.setHorizontalHeaderLabels(labels)

    def _set_resize_behaviour(self, group_by_key):
        """ Define resizing behaviour. """
        header = self.header()
        units_ix = 2

        if group_by_key == "units":
            # Units index is always '2', unless
            # it's used as an arrange key
            units_ix = 0

        header.setStretchLastSection(False)
        # units column size is always fixed
        header.setSectionResizeMode(units_ix, QHeaderView.Fixed)
        header.resizeSection(units_ix, 50)

        if units_ix == 0:
            # units are being used as arrange key
            # set other fields to be stretched
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Interactive)
        else:
            # units are stored in the last column
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(0, QHeaderView.Interactive)

    def _get_column_ixs(self):
        """ Return integer value of header labels. """
        model = self.model()
        cols = [model.headerData(i, Qt.Horizontal) for i in range(model.columnCount())]
        key_ix = cols.index("Key")
        var_ix = cols.index("Variable")
        units_ix = cols.index("Units")
        return key_ix, var_ix, units_ix

    def _resize_columns(self, column_width_dct):
        """ Set tree view column width. """
        header = self.header()
        key_ix, var_ix, units_ix = self._get_column_ixs()
        header.resizeSection(key_ix, column_width_dct["Key"])
        header.resizeSection(var_ix, column_width_dct["Variable"])
        header.resizeSection(units_ix, column_width_dct["Units"])

    def _sort_order_changed(self, index, order):
        """ Store current sorting order in main app. """
        self.main_app.update_sort_order(index, order)

    def _view_resized(self):
        """ Store column widths in the main app. """
        widths = self._get_column_widths()
        self.main_app.update_section_widths(widths)

    def _create_header_actions(self):
        """ Create header actions. """
        # When the file is loaded for the first time the header does not
        # contain required data to use 'view_resized' method.
        # Due to this, the action needs to be created only after the model
        # and its header has been created.
        self.header().sectionResized.connect(self._view_resized)
        self.header().sortIndicatorChanged.connect(self._sort_order_changed)

    def _get_column_widths(self):
        """ Extract a dictionary containing current column widths. """
        key_ix, var_ix, units_ix = self._get_column_ixs()
        header = self.header()
        return {
            "Key": header.sectionSize(key_ix),
            "Variable": header.sectionSize(var_ix),
            "Units": header.sectionSize(units_ix)
        }

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

        proxy_rows = selection_model.selectedRows()  # updated selection
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
        selection_model = self.selectionModel()
        selection_model.clearSelection()  # Note that this emits selectionChanged signal

    def deselect_item(self, proxy_index):
        """ Select an item programmatically. """
        selection_model = self.selectionModel()
        selection_model.select(proxy_index, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)

    def select_item(self, proxy_index):
        """ Select an item programmatically. """
        selection_model = self.selectionModel()
        selection_model.select(proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def select_items(self, proxy_selection):
        """ Select items given by given qselection (model indexes). """
        selection_model = self.selectionModel()
        selection_model.select(proxy_selection,
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


class MyModel(QStandardItemModel):
    def __init__(self, eso_file_header, group_by_key=None, interval_request=None):
        super().__init__()
        self.populate_data(eso_file_header, group_by_key, interval_request)
        self.setSortRole(Qt.AscendingOrder)

    def mimeTypes(self):
        # TODO Double check if this is working
        return "application/json"

    @staticmethod
    def _get_identifiers(group_by_key):
        """ Rearrange variable order. . """
        identifiers = ["key", "variable", "units"]
        identifiers.remove(group_by_key)
        identifiers.insert(0, group_by_key)
        return identifiers

    @staticmethod
    def _append_rows(data_lst, parent):
        """ Add plain rows to the model. """
        for row in data_lst:
            item_row = [QStandardItem(item) for item in row]
            item_row[0].setData(row, Qt.UserRole)  # First item in row holds all the information
            parent.appendRow(item_row)

    @staticmethod
    def _append_tree_rows(data_lst, parent, identifiers, flat=False):
        """ Add plain rows for tree like view. """
        for row in data_lst:
            if not flat:
                item_0 = QStandardItem(None)
            else:
                item_0 = QStandardItem(output_piece(row, identifiers[0]))

            item_0.setData(row, Qt.UserRole)  # First item in row holds all the information
            item_1 = QStandardItem(output_piece(row, identifiers[1]))
            item_2 = QStandardItem(output_piece(row, identifiers[2]))
            parent.appendRow([item_0, item_1, item_2])

    @staticmethod
    def append_item(selection, proxy_index):
        """ Append an item to a given selection. """
        range = QItemSelectionRange(proxy_index)
        selection.append(range)

    def populate_data(self, eso_file_header, group_by_key, interval_request):
        """ Feed the model with output variables. """
        root = self.invisibleRootItem()
        header_dict = eso_file_header.header_view(group_by_key=group_by_key,
                                                  interval_request=interval_request)

        if group_by_key == "raw":
            # tree like structure is not being used
            # all the variable info is stored as header keys
            self._append_rows(header_dict.keys(), root)

        else:
            identifiers = self._get_identifiers(group_by_key)
            for key, variables in header_dict.items():
                if len(variables) == 1:
                    # there is only one variable in the container
                    # insert the data as a simple row
                    self._append_tree_rows(variables, root, identifiers, flat=True)
                else:
                    parent = QStandardItem(key)
                    parent.setDragEnabled(False)
                    root.appendRow(parent)
                    self._append_tree_rows(variables, parent, identifiers, flat=False)


class MyFilterModel(QSortFilterProxyModel):
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

    def find_match(self, current_selection, group_by_key="raw"):
        """ Check if output variables are available in a new model. """
        selection = QItemSelection()

        if group_by_key == "raw":
            # there isn't any preferred sorting applied so the first column is 'key'
            group_by_key = "key"

        # create a list which holds parent parts of currently selected items
        # if the part of variable does not match, than the variable (or any children)
        # will not be selected
        quick_check = [output_piece(var, group_by_key) for var in current_selection]

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
