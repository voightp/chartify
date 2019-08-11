from PySide2.QtWidgets import QTreeView, QAbstractItemView, QHeaderView
from PySide2.QtCore import (Qt, QSortFilterProxyModel, QItemSelectionModel,
                            QItemSelection, QItemSelectionRange, QMimeData,
                            Signal, QObject)
from PySide2.QtGui import QDrag, QPixmap

from PySide2.QtGui import QStandardItemModel, QStandardItem
from esopie.eso_file_header import FileHeader


class View(QTreeView):
    selectionCleared = Signal()
    selectionPopulated = Signal(list)
    itemDoubleClicked = Signal(object)
    updateView = Signal()
    totals = False

    settings = {"widths": {"interactive": 200,
                           "fixed": 70},
                "order": ("variable", Qt.AscendingOrder),
                "header": ("variable", "key", "units"),
                "expanded": set()}

    def __init__(self, id_, std_file_header, tot_file_header):
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
        self.headers = {
            "standard": std_file_header,
            "totals": tot_file_header
        }

        self._initialized = False
        self.temp_settings = {"interval": None,
                              "tree_key": None,
                              "units": None,
                              "totals": None,
                              "force_update": False}

        self._scrollbar_position = 0

        self.verticalScrollBar().valueChanged.connect(self.slider_moved)
        self.expanded.connect(self.handle_expanded)
        self.collapsed.connect(self.handle_collapsed)
        self.pressed.connect(self.handle_drag_attempt)
        self.doubleClicked.connect(self.handle_d_clicked)

    @property
    def file_header(self):
        """ Current file header. """
        key = "totals" if self.totals else "standard"
        return self.headers[key]

    def mousePressEvent(self, event):
        """ Handle mouse events. """
        btn = event.button()
        if btn == Qt.RightButton or btn == Qt.MiddleButton:
            return
        else:
            super().mousePressEvent(event)

    def get_available_intervals(self):
        """ Get currently available intervals. """
        return self.file_header.available_intervals

    def get_file_id(self):
        """ Get file id based on 'totals' request. """
        return self.file_header.id_

    def show_hidden_header_variables(self):
        """ Remove all hidden variables from the file. """
        for v in self.headers.values():
            v.show_hidden_variables()

    def remove_hidden_header_variables(self):
        """ Remove all hidden variables from the file. """
        for v in self.headers.values():
            v.remove_hidden_variables()

    def remove_header_variables(self, groups):
        """ Remove variables from the file. """
        self.file_header.remove_variables(groups)

    def hide_header_variables(self, groups):
        """ Temporarily hide a variable from the file. """
        self.file_header.hide_variables(groups)

    def add_header_variable(self, id_, variable):
        """ Add a new variable (from 'Variable' class) into file header. """
        self.file_header.add_variable(id_, variable)

    def filter_view(self, filter_str):
        """ Filter the model using given string. """
        model = self.model()
        model.setRecursiveFilteringEnabled(True)
        model.setFilterFixedString(filter_str)

        # Expand all items when filter is applied
        self.expandAll()
        self.set_first_col_spanned()

    def set_next_update_forced(self):
        """ Notify the view that it needs to be updated. """
        self.temp_settings["force_update"] = True

    def store_settings(self, interval, tree_key, units, totals):
        """ Store intermediate settings. """
        self.temp_settings = {"interval": interval,
                              "tree_key": tree_key,
                              "units": units,
                              "totals": totals,
                              "force_update": False}

    def set_first_col_spanned(self):
        """ Set parent row to be spanned over all columns. """
        model = self.model()
        for i in range(model.rowCount()):
            ix = model.index(i, 0)
            if model.hasChildren(ix):
                self.setFirstColumnSpanned(i, self.rootIndex(), True)

    def build_model(self, header, units_settings,
                    tree_key, view_order, interval):
        """
        Create a model and set up its appearance.
        """
        model = ViewModel()
        model.populate_data(header, units_settings,
                            tree_key, view_order, interval)

        proxy_model = FilterModel()
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)

        # define view appearance and behaviour
        self.set_header_labels(view_order)
        self.set_first_col_spanned()

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
        log_ix = self.get_logical_index(name)
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
                    # make sure that
                    self.collapse(ix)

    def update_selection(self, variables, key):
        """ Select previously selected items when the model changes. """
        proxy_model = self.model()

        # Find matching items and select items on a new model
        proxy_selection = proxy_model.find_match(variables, key)
        self.select_items(proxy_selection)

        proxy_rows = proxy_selection.indexes()
        outputs = [proxy_model.data_from_index(index) for index in proxy_rows]

        self.store_outputs(outputs)

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
        self.verticalScrollBar().valueChanged.disconnect(self.slider_moved)

    def reconnect_actions(self):
        """ Connect specific signals. """
        self.verticalScrollBar().valueChanged.connect(self.slider_moved)

    def update_model(self, is_tree, interval, units_settings,
                     select=None, filter_str=""):
        """
        Set the model and define behaviour of the tree view.
        """
        header = self.file_header
        totals = self.totals
        view_order = self.settings["header"]
        tree_key = view_order[0] if is_tree else None

        # Only update the model if the settings have changed
        conditions = [tree_key != self.temp_settings["tree_key"],
                      interval != self.temp_settings["interval"],
                      units_settings != self.temp_settings["units"],
                      self.totals != self.temp_settings["totals"],
                      self.temp_settings["force_update"]]

        if any(conditions):
            self.disconnect_actions()
            self.build_model(header, units_settings,
                             tree_key, view_order, interval)

            # Store current sorting key and interval
            self.store_settings(interval, tree_key, units_settings, totals)
            self.reconnect_actions()

        # clean up selection as this will be handled based on
        # currently selected list of items stored in main app
        self.clear_selected()
        if select:
            self.update_selection(select, view_order[0])

        if filter_str:
            self.filter_view(filter_str)

        self.update_view_appearance()

        if not self._initialized:
            # create header actions only when view is created
            self.initialize_header()
            self._initialized = True

    def set_header_labels(self, view_order):
        """ Assign header labels. """
        model = self.model().sourceModel()
        model.setHorizontalHeaderLabels(view_order)

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
        log_ixs = self.get_logical_ixs()
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

    def get_logical_names(self):
        """ Get names sorted by logical index. """
        model = self.model()
        num = model.columnCount()
        nms = [model.headerData(i, Qt.Horizontal).lower() for i in range(num)]
        return nms

    def get_visual_names(self):
        """ Return sorted column names (by visual index). """
        num = self.model().columnCount()
        vis_ixs = [self.header().visualIndex(i) for i in range(num)]

        z = list(zip(self.get_logical_names(), vis_ixs))
        z.sort(key=lambda x: x[1])
        sorted_names = list(zip(*z))[0]
        return sorted_names

    def get_logical_index(self, name):
        """ Get a logical index of a given section title. """
        return self.get_logical_names().index(name)

    def get_logical_ixs(self):
        """ Return logical positions of header labels. """
        names = self.get_logical_names()
        return (names.index("key"),
                names.index("variable"),
                names.index("units"))

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
            self.updateView.emit()
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

    def slider_moved(self, val):
        """ Handle moving view slider. """
        self._scrollbar_position = val

    def handle_d_clicked(self, index):
        """ Handle double click on the view. """
        proxy_model = self.model()
        source_item = proxy_model.item_from_index(index)

        if source_item.hasChildren():
            # parent item cannot be renamed
            return

        dt = proxy_model.data_from_index(index)
        if dt:
            self.itemDoubleClicked.emit(dt)

    def handle_drag_attempt(self):
        """ Handle pressing the view item or items. """
        outputs = self.get_outputs()

        if not outputs:
            return

        outputs_str_lst = [" | ".join(var) for var in outputs]
        print("HANDLING DRAG!\n\t{}".format("\n\t".join(outputs_str_lst)))

        mime_dt = QMimeData()
        mime_dt.setText("HELLO FROM PIE")
        pix = QPixmap("../icons/input.png")

        drag = QDrag(self)
        drag.setMimeData(mime_dt)
        drag.setPixmap(pix)
        drag.exec_(Qt.CopyAction)
        # create a drag object with pixmap

    def get_outputs(self):
        """ Extract output information from the current selection. """
        proxy_model = self.model()
        selection_model = self.selectionModel()
        proxy_rows = selection_model.selectedRows()
        rows = proxy_model.map_to_source_lst(proxy_rows)

        if not proxy_rows:
            # break if there isn't any valid variable
            self.selectionCleared.emit()
            return

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
                    self.select_children(source_item, source_index)

                # deselect all the parent nodes as these should not be
                # included in output variable data
                self.deselect_item(index)

        # needs to be called again to get updated selection
        proxy_rows = selection_model.selectedRows()

        outputs = [proxy_model.data_from_index(index) for index in proxy_rows]
        self.store_outputs(outputs)

        return outputs

    def store_outputs(self, outputs):
        """ Update outputs in the main app. """
        if outputs:
            self.selectionPopulated.emit(outputs)
        else:
            self.selectionCleared.emit()

    def select_children(self, source_item, source_index):
        """ Select all children of the parent row. """
        first_ix = source_index.child(0, 0)
        last_ix = source_index.child((source_item.rowCount() - 1), 0)

        selection = QItemSelection(first_ix, last_ix)
        proxy_selection = self.model().mapSelectionFromSource(selection)

        self.select_items(proxy_selection)

    def clear_selected(self):
        """ Clear all selected rows. """
        self.selectionCleared.emit()
        self.selectionModel().clearSelection()

    def deselect_item(self, proxy_index):
        """ Select an item programmatically. """
        self.selectionModel().select(proxy_index,
                                     QItemSelectionModel.Deselect |
                                     QItemSelectionModel.Rows)

    def select_item(self, proxy_index):
        """ Select an item programmatically. """
        self.selectionModel().select(proxy_index,
                                     QItemSelectionModel.Select |
                                     QItemSelectionModel.Rows)

    def select_items(self, proxy_selection):
        """ Select items given by given selection (model indexes). """
        self.selectionModel().select(proxy_selection,
                                     QItemSelectionModel.Select |
                                     QItemSelectionModel.Rows)

    def handle_collapsed(self, index):
        """ Deselect the row when node collapses."""
        proxy_model = self.model()
        if proxy_model.hasChildren(index):
            name = proxy_model.data(index)
            exp = self.settings["expanded"]
            try:
                exp.remove(name)
            except KeyError:
                pass

    def handle_expanded(self, index):
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
        tip = f"{var.key}  |  {var.variable}  |  {var.units}"
        item.setStatusTip(tip)

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

    def populate_data(self, header, units_settings, tree_key, view_order,
                      interval):
        """ Feed the model with output variables. """
        root = self.invisibleRootItem()
        header = header.get_iterator(units_settings, view_order, interval)

        if not tree_key:
            # tree like structure is not being used
            # append as a plain table
            self._append_rows(header, root)

        else:
            # create a tree like structure
            tree_header = FileHeader.get_tree_dct(header, tree_key)
            self._append_tree_rows(tree_header, root)


class FilterModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()

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

    def filterAcceptsRow(self, source_row, source_parent):
        """ Set up filtering rules for the model. """
        source_model = self.sourceModel()

        if self.filterRegExp().pattern() in ["", " ", "\t"]:
            return True

        ix0 = source_model.index(source_row, 0, source_parent)
        ix1 = source_model.index(source_row, 1, source_parent)

        if self.sourceModel().data(ix1) is None:
            # exclude parent nodes (these are enabled due to recursive filter)
            return False

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
