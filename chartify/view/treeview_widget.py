from PySide2.QtCore import (Qt, QSortFilterProxyModel, QItemSelectionModel,
                            QItemSelection, QItemSelectionRange, QMimeData,
                            Signal)
from PySide2.QtGui import QStandardItemModel, QStandardItem, QDrag, QPixmap
from PySide2.QtWidgets import QTreeView, QAbstractItemView, QHeaderView, QMenu

from chartify.view.treeview_functions import as_tree_dct


class View(QTreeView):
    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(object)
    treeNodeChanged = Signal()

    settings = {"widths": {"interactive": 200, "fixed": 70},
                "order": ("variable", Qt.AscendingOrder),
                "header": ("variable", "key", "units"),
                "expanded": set()}

    def __init__(self, id_, name):
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

        self._initialized = False
        self.temp_settings = {"interval": None,
                              "tree_key": None,
                              "units": None,
                              "filter": None,
                              "force_update": True}

        self._scrollbar_position = 0

        self.verticalScrollBar().valueChanged.connect(self.on_slider_moved)
        self.expanded.connect(self.on_expanded)
        self.collapsed.connect(self.on_collapsed)
        self.pressed.connect(self.on_pressed)
        self.doubleClicked.connect(self.on_double_clicked)

    def mousePressEvent(self, event):
        """ Handle mouse events. """
        btn = event.button()
        if btn == Qt.RightButton or btn == Qt.MiddleButton:
            return
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """ Manage context menu. """
        menu = QMenu(self)
        menu.setObjectName("contextMenu")
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)

        menu.exec_(self.mapToGlobal(event.pos()))

    def filter_view(self, filter_tup):
        """ Filter the model using given filter tuple. """
        self.model().setRecursiveFilteringEnabled(True)
        self.model().setFilterTuple(filter_tup)
        self.model().invalidateFilter()

        # Expand all items when filter is applied
        self.expandAll()
        self.set_first_col_spanned()

    def set_next_update_forced(self):
        """ Notify the view that it needs to be updated. """
        self.temp_settings["force_update"] = True

    def store_settings(self, interval, tree_key, units, filter_tup):
        """ Store intermediate settings. """
        self.temp_settings = {"interval": interval,
                              "tree_key": tree_key,
                              "units": units,
                              "filter": filter_tup,
                              "force_update": False}

    def set_first_col_spanned(self):
        """ Set parent row to be spanned over all columns. """
        model = self.model()
        for i in range(model.rowCount()):
            ix = model.index(i, 0)
            if model.hasChildren(ix):
                self.setFirstColumnSpanned(i, self.rootIndex(), True)

    def build_model(self, variables, proxy_variables, tree_key, view_order):
        """  Create a model and set up its appearance. """
        model = ViewModel()
        model.populate_data(variables, proxy_variables, tree_key)
        model.setHorizontalHeaderLabels(view_order)

        proxy_model = FilterModel()
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)

        self.set_first_col_spanned()

    def get_visual_names(self):
        """ Return sorted column names (by visual index). """
        num = self.model().columnCount()
        vis_ixs = [self.header().visualIndex(i) for i in range(num)]

        z = list(zip(self.model().get_logical_names(), vis_ixs))
        z.sort(key=lambda x: x[1])
        sorted_names = list(zip(*z))[0]
        return sorted_names

    def reshuffle_columns(self, order):
        """ Reset column positions to match last visual appearance. """
        header = self.header()
        for i, nm in enumerate(order):
            vis_names = self.get_visual_names()
            j = vis_names.index(nm)
            if i != j:
                header.moveSection(j, i)

    def update_sort_order(self, name, order):
        """ Set header order. """
        log_ix = self.model().get_logical_index(name)
        self.header().setSortIndicator(log_ix, order)

    def expand_items(self, expanded_set):
        """ Expand items which were previously expanded (on other models). """
        model = self.model()
        for i in range(model.rowCount()):
            ix = model.index(i, 0)
            if model.hasChildren(ix):
                data = model.data(ix)
                if data in expanded_set:
                    self.expand(ix)
                else:
                    self.collapse(ix)

    def update_scroll_position(self):
        """ Update the slider position. """
        self.verticalScrollBar().setValue(self._scrollbar_position)

    def scroll_to(self, var):
        """ Scroll to the given var. """
        proxy_model = self.model()
        key = self.settings["header"][0]

        # var needs to be passed as a list
        proxy_selection = proxy_model.find_match([var], key)

        if proxy_selection:
            ix = proxy_selection.indexes()[0]
            self.scrollTo(ix)

    def update_view_appearance(self):
        """ Update the model appearance to be consistent with last view. """
        name, order = self.settings["order"]
        expanded_items = self.settings["expanded"]
        view_order = self.settings["header"]
        widths = self.settings["widths"]

        self.update_resize_behaviour()
        self.resize_header(widths)
        self.update_sort_order(name, order)

        if expanded_items:
            self.expand_items(expanded_items)

        # it's required to adjust columns order to match the last applied order
        self.reshuffle_columns(view_order)
        self.update_scroll_position()

    def disconnect_actions(self):
        """ Disconnect specific signals to avoid overriding stored values. """
        self.verticalScrollBar().valueChanged.disconnect(self.on_slider_moved)

    def reconnect_actions(self):
        """ Connect specific signals. """
        self.verticalScrollBar().valueChanged.connect(self.on_slider_moved)

    def deselect_variables(self):
        """ Deselect all currently selected variables. """
        self.selectionModel().clearSelection()
        self.selectionCleared.emit()

    def select_variables(self, variables):
        """ Select previously selected items when the model changes. """
        variables = variables if isinstance(variables, list) else [variables]

        proxy_model = self.model()
        key = self.settings["header"][0]

        # Find matching items and select items on a new model
        proxy_selection = proxy_model.find_match(variables, key)
        self._select_items(proxy_selection)

        proxy_rows = proxy_selection.indexes()
        variables = [proxy_model.data_from_index(index) for index in proxy_rows]

        if variables:
            self.selectionPopulated.emit(variables)
        else:
            self.selectionCleared.emit()

    def update_model(self, variables, proxy_variables, is_tree, interval,
                     units, filter_tup=None, selected=None, scroll_to=None):
        """ Set the model and define behaviour of the tree view. """
        view_order = self.settings["header"]
        tree_key = view_order[0] if is_tree else None

        # Only update the model if the settings have changed
        conditions = [tree_key != self.temp_settings["tree_key"],
                      interval != self.temp_settings["interval"],
                      units != self.temp_settings["units"],
                      filter_tup != self.temp_settings["filter"],
                      self.temp_settings["force_update"]]

        if any(conditions):
            print("UPDATING MODEL")
            self.disconnect_actions()
            self.build_model(variables, proxy_variables, tree_key, view_order)

            # Store current sorting key and interval
            self.store_settings(interval, tree_key, units, filter_tup)
            self.reconnect_actions()

        # clear selections to avoid having visually
        # selected items from previous selection
        self.deselect_variables()

        if selected:
            self.select_variables(selected)

        if any(filter_tup):
            self.filter_view(filter_tup)

        if scroll_to:
            self.scroll_to(scroll_to)

        # update visual appearance of the view to be consistent
        # with previously displayed View
        self.update_view_appearance()

        if not self._initialized:
            # create header actions only when view is created
            self.initialize_header()
            self._initialized = True

    def resize_header(self, widths):
        """ Update header sizes. """
        header = self.header()
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

        # both logical and visual indexes are ordered
        # as 'key', 'variable', 'units'
        log_ixs = self.model().get_logical_ixs()
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

    def on_sort_order_changed(self, log_ix, order):
        """ Store current sorting order in main app. """
        name = self.model().headerData(log_ix, Qt.Horizontal)
        self.settings["order"] = (name, order)

    def on_view_resized(self):
        """ Store interactive section width in the main app. """
        header = self.header()

        for i in range(header.count()):
            if header.sectionResizeMode(i) == header.Interactive:
                width = header.sectionSize(i)
                self.settings["widths"]["interactive"] = width

    def on_section_moved(self, _logical_ix, old_visual_ix, new_visual_ix):
        """ Handle updating the model when first column changed. """
        names = self.get_visual_names()
        is_tree = self.temp_settings["tree_key"]
        self.settings["header"] = names

        if (new_visual_ix == 0 or old_visual_ix == 0) and is_tree:
            # need to update view as section has been moved
            # onto first position and tree key is applied
            self.treeNodeChanged.emit()
            self.update_sort_order(names[0], Qt.AscendingOrder)

        self.update_resize_behaviour()
        self.resize_header(self.settings["widths"])

    def initialize_header(self):
        """ Create header actions. """
        # When the file is loaded for the first time, the header does not
        # contain required data to use 'view_resized' method.
        # Due to this, the action needs to be created only after the model
        # and its header have been created.
        self.header().setFirstSectionMovable(True)
        self.header().sectionResized.connect(self.on_view_resized)
        self.header().sortIndicatorChanged.connect(self.on_sort_order_changed)
        self.header().sectionMoved.connect(self.on_section_moved)

    def on_slider_moved(self, val):
        """ Handle moving view slider. """
        self._scrollbar_position = val

    def on_double_clicked(self, index):
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

    def on_pressed(self):
        """ Handle pressing the view item or items. """
        outputs = self.get_selected_variables()

        if outputs:
            mime_dt = QMimeData()
            mime_dt.setText("HELLO FROM PIE")
            pix = QPixmap("./icons/input.png")

            drag = QDrag(self)
            drag.setMimeData(mime_dt)
            drag.setPixmap(pix)
            drag.exec_(Qt.CopyAction)

            self.selectionPopulated.emit(outputs)
        else:
            self.selectionCleared.emit()

    def get_selected_variables(self):
        """ Extract output information from the current selection. """
        proxy_model = self.model()
        selection_model = self.selectionModel()
        proxy_rows = selection_model.selectedRows()
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
            proxy_rows = selection_model.selectedRows()

            return [proxy_model.data_from_index(index) for index in proxy_rows]

    def _select_children(self, source_item, source_index):
        """ Select all children of the parent row. """
        first_ix = source_index.child(0, 0)
        last_ix = source_index.child((source_item.rowCount() - 1), 0)

        selection = QItemSelection(first_ix, last_ix)
        proxy_selection = self.model().mapSelectionFromSource(selection)

        self._select_items(proxy_selection)

    def _deselect_item(self, proxy_index):
        """ Select an item programmatically. """
        self.selectionModel().select(proxy_index,
                                     QItemSelectionModel.Deselect |
                                     QItemSelectionModel.Rows)

    def _select_item(self, proxy_index):
        """ Select an item programmatically. """
        self.selectionModel().select(proxy_index,
                                     QItemSelectionModel.Select |
                                     QItemSelectionModel.Rows)

    def _select_items(self, proxy_selection):
        """ Select items given by given selection (model indexes). """
        self.selectionModel().select(proxy_selection,
                                     QItemSelectionModel.Select |
                                     QItemSelectionModel.Rows)

    def on_collapsed(self, index):
        """ Deselect the row when node collapses."""
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            exp = self.settings["expanded"]
            try:
                exp.remove(name)
            except KeyError:
                pass

    def on_expanded(self, index):
        """ Deselect the row when node is expanded. """
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            exp = self.settings["expanded"]
            exp.add(name)


class ViewModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setSortRole(Qt.AscendingOrder)

    def mimeTypes(self):
        # TODO Double check if this is working
        return "application/json"

    @staticmethod
    def set_status_tip(item, var):
        """ Parse variable to create a status tip. """
        item.setStatusTip(f"{var.key}  |  {var.variable}  |  {var.units}")

    def _append_rows(self, header_iterator, parent, tree=False):
        """ Add rows to the model. """
        for data, proxy in header_iterator:
            proxy_dt = [None, proxy[1], proxy[2]] if tree else proxy

            row = [QStandardItem(item) for item in proxy_dt]

            # first item in row holds all the information
            row[0].setData(data, Qt.UserRole)

            _ = [self.set_status_tip(item, proxy) for item in row]
            parent.appendRow(row)

    def _append_tree_rows(self, tree_header, root):
        """ Add rows for a tree like view. """
        for k, variables in tree_header.items():

            if len(variables) == 1:
                # append as a plain row
                self._append_rows(variables, root)

            else:
                parent = QStandardItem(k)
                parent.setDragEnabled(False)
                root.appendRow(parent)
                self._append_rows(variables, parent, tree=True)

    def populate_data(self, variables, proxy_variables, tree_key):
        """ Feed the model with output variables. """
        root = self.invisibleRootItem()
        header_zip = zip(variables, proxy_variables)

        if not tree_key:
            # create plain table when tree structure not requested
            self._append_rows(header_zip, root)

        else:
            # create a tree like structure
            tree_header = as_tree_dct(header_zip, tree_key)
            self._append_tree_rows(tree_header, root)


class FilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter_tup = (None, None, None)

    def get_logical_names(self):
        """ Get names sorted by logical index. """
        num = self.columnCount()
        nms = [self.headerData(i, Qt.Horizontal).lower() for i in range(num)]
        return nms

    def get_logical_index(self, name):
        """ Get a logical index of a given section title. """
        return self.get_logical_names().index(name)

    def get_logical_ixs(self):
        """ Return logical positions of header labels. """
        names = self.get_logical_names()
        return (names.index("key"),
                names.index("variable"),
                names.index("units"))

    def data_from_index(self, index):
        """ Get item data from source model. """
        item = self.item_from_index(index)
        return item.data(Qt.UserRole)

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

    def setFilterTuple(self, filter_tup):
        self._filter_tup = filter_tup

    def filterAcceptsRow(self, source_row, source_parent):
        """ Set up filtering rules for the model. """

        def valid(fval, val):
            fval = fval.strip()
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
            t = self._filter_tup
            ixs = self.get_logical_ixs()
            for col, fval in zip(ixs, t):
                ix = self.sourceModel().index(source_row, col, source_parent)
                it = self.sourceModel().itemFromIndex(ix)

                if col == 0 and it.parent() is not None:
                    if it.parent() is not self.sourceModel().invisibleRootItem():
                        val = it.parent().text()
                    else:
                        val = it.text()
                else:
                    val = it.text()

                if not valid(fval, val):
                    return False

            return True

    def find_match(self, variables, key):
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

    def flags(self, index):
        """ Set item flags. """
        if self.hasChildren(index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable
