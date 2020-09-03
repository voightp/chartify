import os
from multiprocessing import Manager
from typing import List, Callable, Union, Any, Dict, Optional

from PySide2.QtCore import QThreadPool
from esofile_reader.base_file import VariableType
from esofile_reader.constants import UNITS_LEVEL
from esofile_reader.mini_classes import ResultsFileType, Variable
from esofile_reader.storages.pqt_storage import ParquetFile

from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.settings import Settings
from chartify.ui.main_window import MainWindow
from chartify.ui.treeview import ViewModel
from chartify.utils.process_utils import create_pool, kill_child_processes, load_file
from chartify.utils.threads import EsoFileWatcher, IterWorker, Monitor
from chartify.utils.utils import get_str_identifier, VariableData


class AppController:
    """
    Controller class to connect application
    view with application model.

    All background threads and processes are controlled
    in this class.

    Attributes & Parameters
    -----------------------
    v : MainWindow
        A main application view.
    m : AppModel
        An access to the application database.
    wvc : WebViewController
        A link to the application web controller.

    """

    def __init__(self, model: AppModel, view: MainWindow, wv_controller: WVController):
        self.v = view
        self.m = model
        self.wvc = wv_controller

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.manager = Manager()
        self.lock = self.manager.Lock()
        self.ids = self.manager.list([])
        self.progress_queue = self.manager.Queue()
        self.file_queue = self.manager.Queue()

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.watcher = EsoFileWatcher(self.file_queue)
        self.watcher.file_loaded.connect(self.on_file_loaded)
        self.watcher.all_loaded.connect(self.on_all_files_loaded)
        self.watcher.start()

        self.monitor = Monitor(self.progress_queue)
        self.monitor.start()

        # ~~~~ Thread executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.thread_pool = QThreadPool()

        # ~~~~ Process executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.pool = create_pool()

        # ~~~~ Connect signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.connect_view_signals()
        self.connect_model_signals()

    def tear_down(self) -> None:
        """ Clean up application resources. """
        # TODO enable once main window polished
        # Settings.save_settings_to_json()

        self.watcher.terminate()
        self.monitor.terminate()
        self.manager.shutdown()

        kill_child_processes(os.getpid())

        self.v._CLOSE_FLAG = True
        self.v.close()

    def connect_view_signals(self) -> None:
        """ Connect view signals. """
        self.v.paletteUpdated.connect(self.wvc.refresh_layout)
        self.v.selectionChanged.connect(self.on_selection_change)
        self.v.fileProcessingRequested.connect(self.on_file_processing_requested)
        self.v.syncFileProcessingRequested.connect(self.on_sync_file_processing_requested)
        self.v.fileRenameRequested.connect(self.on_file_rename_requested)
        self.v.variableRenameRequested.connect(self.on_variable_rename_requested)
        self.v.variableRemoveRequested.connect(self.on_variable_remove_requested)
        self.v.aggregationRequested.connect(self.on_aggregation_requested)
        self.v.fileRemoveRequested.connect(self.on_file_remove_requested)
        self.v.appCloseRequested.connect(self.tear_down)
        self.v.close_all_act.triggered.connect(lambda x: x)
        self.v.save_act.triggered.connect(self.on_save)
        self.v.save_as_act.triggered.connect(self.on_save_as)
        self.v.updateModelRequested.connect(self.on_update_model_requested)
        self.v.setModelRequested.connect(self.on_set_model_requested)

    def connect_model_signals(self) -> None:
        """ Create monitor signals. """
        self.monitor.file_added.connect(self.v.progress_cont.add_file)
        self.monitor.progress_updated.connect(self.v.progress_cont.update_progress)
        self.monitor.range_changed.connect(self.v.progress_cont.set_range)
        self.monitor.pending.connect(self.v.progress_cont.set_pending)
        self.monitor.failed.connect(self.v.progress_cont.set_failed)
        self.monitor.status_changed.connect(self.v.progress_cont.set_status)

    def on_selection_change(self, variable_data: List[tuple]) -> None:
        """ Handle selection update. """
        out_str = [" | ".join(var) for var in variable_data if var is not None]
        if out_str:
            print("Selected Variables:\n\t{}".format("\n\t".join(out_str)))
        self.m.selected_variable_data = variable_data

    def on_save(self):
        if not self.m.storage.path:
            self.on_save_as()
        else:
            self.m.storage.save()

    def on_save_as(self):
        path = self.v.save_storage_to_fs()
        if path:
            self.m.storage.save_as(path.parent, path.stem)

    def update_view_model(
        self,
        selected: Optional[List[VariableData]] = None,
        scroll_to: Optional[VariableData] = None,
    ):
        """ Force update of the current model. """
        old_model = self.v.current_view.source_model
        self.v.current_view.update_model(self.m.current_table, **Settings.units_dict())
        self.v.update_view_visual(
            selected=selected,
            scroll_to=scroll_to,
            old_model=old_model,
            hide_source_units=Settings.HIDE_SOURCE_UNITS,
        )

    def on_set_model_requested(self):
        """ Set a new model on current view. """
        old_model = self.v.current_view.source_model
        new_model = self.v.current_view.models[Settings.TABLE_NAME]
        if new_model.is_simple or Settings.TREE_NODE == new_model.tree_node:
            self.v.current_view.set_model(Settings.TABLE_NAME)
            self.v.current_view.update_units(
                self.m.current_table[UNITS_LEVEL], **Settings.units_dict()
            )
        else:
            self.v.current_view.set_and_update_model(
                self.m.current_table,
                Settings.TABLE_NAME,
                tree_node=Settings.TREE_NODE,
                **Settings.units_dict()
            )
        self.v.update_view_visual(
            old_model=old_model,
            selected=self.m.selected_variable_data,
            hide_source_units=Settings.HIDE_SOURCE_UNITS,
        )

    def on_update_model_requested(self):
        """ Update current model on current view. """
        if self.v.current_view:
            old_model = self.v.current_view.source_model
            new_model = self.v.current_view.models[Settings.TABLE_NAME]
            if new_model.is_simple or Settings.TREE_NODE == new_model.tree_node:
                self.v.current_view.update_units(
                    self.m.current_table[UNITS_LEVEL], **Settings.units_dict()
                )
            else:
                self.v.current_view.update_model(
                    self.m.current_table, tree_node=Settings.TREE_NODE, **Settings.units_dict()
                )
            self.v.update_view_visual(
                old_model=old_model,
                selected=self.m.selected_variable_data,
                hide_source_units=Settings.HIDE_SOURCE_UNITS,
            )

    def on_file_processing_requested(self, paths: List[str]) -> None:
        """ Load new files. """
        workdir = str(self.m.storage.workdir)
        for path in paths:
            self.pool.submit(
                load_file,
                path,
                workdir,
                self.progress_queue,
                self.file_queue,
                self.ids,
                self.lock,
            )

    def on_sync_file_processing_requested(self, paths: List[str]) -> None:
        """ Load new files. """
        workdir = str(self.m.storage.workdir)
        for path in paths:
            load_file(
                path, workdir, self.progress_queue, self.file_queue, self.ids, self.lock,
            )

    def on_all_files_loaded(self, monitor_id: str) -> None:
        """ Remove progress widget from ui. """
        self.v.progress_cont.remove_file(monitor_id)

    def on_file_loaded(self, file: ParquetFile, models: Dict[str, ViewModel]) -> None:
        """ Add results file into 'tab' widget. """
        # make sure that file name is unique
        names = self.m.get_all_file_names()
        name = get_str_identifier(file.file_name, names)
        file.rename(name)

        # store file reference in model
        self.m.storage.files[file.id_] = file

        # add new tab into tab widget
        self.v.add_new_tab(file.id_, name, models)

    def apply_async(self, id_: int, func: Callable, *args, **kwargs) -> Any:
        """ A wrapper to apply functions to current views. """
        file = self.m.get_file(id_)
        # apply function on the current file
        val = func(file, *args, **kwargs)

        # make sure that appropriate views will be updated
        views = self.v.all_views if Settings.ALL_FILES else [self.v.current_view]
        for view in views:
            # TODO set model dirty flags
            pass

        # apply function to all other widgets asynchronously
        if Settings.ALL_FILES:
            other_files = self.m.get_other_files()
            w = IterWorker(func, other_files, *args, **kwargs)
            self.thread_pool.start(w)

        return val

    @staticmethod
    def _update_variable_name(
        file: ResultsFileType, variable_name: str, key_name: str, variable: VariableType
    ) -> VariableType:
        """ Rename given 'Variable'. """
        # TODO handle None returned
        _, var = file.rename_variable(variable, variable_name, key_name)
        return var

    @staticmethod
    def _delete_variables(file: ResultsFileType, variables: List[VariableType]) -> None:
        """ Hide or remove selected variables. """
        # TODO return True or False
        file.remove_variables(variables)

    @staticmethod
    def _aggregate_variables(
        file: ResultsFileType,
        variables: List[VariableType],
        key: str,
        type_: str,
        func: Union[str, Callable],
    ) -> tuple:
        """ Add a new aggregated variable to the file. """
        # TODO catch CannotAggregate
        res = file.aggregate_variables(variables, func, key=key, type_=type_)
        if res:
            var_id, var = res
            return var

    def on_variable_rename_requested(self, variable_data: VariableData) -> None:
        """ Overwrite variable name. """
        old_type = variable_data.type
        old_key = variable_data.key
        res = self.v.confirm_rename_variable(old_key, old_type)
        if res:
            new_key, new_type = res
            if (new_type != old_type and new_type is not None) or new_key != old_key:
                var = self.m.selected_variables[0]
                new_variable = self.apply_async(
                    Settings.CURRENT_FILE_ID, self._update_variable_name, new_type, new_key, var
                )
                new_variable_data = VariableData(
                    key=new_variable.key,
                    type=new_variable.type if isinstance(new_variable, Variable) else None,
                    units=new_variable.units,
                    proxyunits=variable_data.proxyunits,
                )
                self.update_view_model(
                    selected=[new_variable_data], scroll_to=new_variable_data,
                )

    def on_variable_remove_requested(self) -> None:
        """ Remove variables from a file or all files. """
        variables = self.m.selected_variables
        res = self.v.confirm_remove_variables(
            variables, Settings.ALL_FILES, self.m.current_file.file_name
        )
        if res:
            self.apply_async(Settings.CURRENT_FILE_ID, self._delete_variables, variables)
            self.update_view_model()

    def on_file_rename_requested(self, tab_index: int, id_: int) -> None:
        """ Update file name. """
        name = self.m.get_file_name(id_)
        other_names = self.m.get_other_file_names()
        new_name = self.v.confirm_rename_file(name, other_names)
        if new_name is not None:
            self.v.rename_tab(tab_index, name)
            self.m.rename_file(id_, new_name)

    def on_aggregation_requested(self, func: Union[str, Callable]) -> None:
        """ Create a new variable using given aggregation function. """
        variables = self.m.selected_variables
        func_name = func if isinstance(func, str) else func.__name__
        if variables:
            res = self.v.confirm_aggregate_variables(variables, func_name)
            if res:
                new_key, new_type = res
                new_variable = self.apply_async(
                    Settings.CURRENT_FILE_ID,
                    self._aggregate_variables,
                    variables,
                    new_key,
                    new_type,
                    func,
                )
                # proxy units can be 'None' as model will be refreshed
                new_variable_data = VariableData(
                    key=new_variable.key,
                    type=new_variable.type if isinstance(new_variable, Variable) else None,
                    units=new_variable.units,
                    proxyunits=None,
                )
                self.update_view_model(
                    selected=[new_variable_data], scroll_to=new_variable_data,
                )

    def on_file_remove_requested(self, tab_index: int) -> None:
        """ Delete file from the database. """
        treeview = self.v.tab_wgt.widget(tab_index)
        id_ = treeview.id_
        file_name = self.m.get_file(id_).file_name
        res = self.v.confirm_delete_file(file_name)
        if res:
            treeview.deleteLater()
            self.m.delete_file(id_)
            self.ids.remove(id_)
            self.v.tab_wgt.removeTab(tab_index)
