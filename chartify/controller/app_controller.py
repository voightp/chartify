import os
from multiprocessing import Manager
from typing import List, Callable, Union, Any

from PySide2.QtCore import QThreadPool
from esofile_reader.mini_classes import ResultsFile, Variable
from esofile_reader.storage.storage_files import ParquetFile

from chartify.settings import Settings
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

    def __init__(self, model, view, wv_controller):
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
        Settings.SIZE = self.v.size()
        Settings.POSITION = self.v.pos()
        Settings.write_reg_settings()

        self.watcher.terminate()
        self.monitor.terminate()
        self.manager.shutdown()

        kill_child_processes(os.getpid())

        self.v._CLOSE_FLAG = True
        self.v.close()

    def connect_view_signals(self) -> None:
        """ Connect view signals. """
        self.v.paletteUpdated.connect(self.wvc.refresh_layout)
        self.v.viewUpdateRequested.connect(self.on_view_update_requested)
        self.v.selectionChanged.connect(self.on_selection_change)
        self.v.fileProcessingRequested.connect(self.on_file_processing_requested)
        self.v.fileRenameRequested.connect(self.on_file_rename_requested)
        self.v.variableRenameRequested.connect(self.on_variable_rename_requested)
        self.v.variableRemoveRequested.connect(self.handle_remove_variables)
        self.v.variableAggregateRequested.connect(self.handle_aggregate_variables)
        self.v.fileRemoveRequested.connect(self.handle_close_tab)
        self.v.appCloseRequested.connect(self.tear_down)
        self.v.close_all_act.triggered.connect(lambda x: x)
        self.v.save_act.triggered.connect(self.on_save)
        self.v.save_as_act.triggered.connect(self.on_save_as)

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
        out_str = [" | ".join(var) for var in variable_data]
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

    def on_view_update_requested(self, id_: int) -> None:
        """ Update content of a newly selected tab. """
        file = self.m.get_file(id_)
        # update interface to enable only available interval buttons
        # and rate to energy button when applicable
        self.v.toolbar.update_intervals_state(file.available_intervals)
        self.v.toolbar.update_rate_to_energy_state(Settings.INTERVAL)
        self.v.build_treeview(
            file.get_header_df(Settings.INTERVAL), selected=self.m.selected_variable_data
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

    def on_all_files_loaded(self, monitor_id: str) -> None:
        """ Remove progress widget from ui. """
        self.v.progress_cont.remove_file(monitor_id)

    def on_file_loaded(self, file: ParquetFile) -> None:
        """ Add eso file into 'tab' widget. """
        # make sure that file name is unique
        names = self.m.get_all_file_names()
        name = get_str_identifier(file.file_name, names)
        file.rename(name)

        # store file reference in model
        self.m.storage.files[file.id_] = file

        # number of columns can be either 2 or 3
        simpleview = file.type_ in []

        # add new tab into tab widget
        self.v.add_new_tab(file.id_, name, simpleview=simpleview)

    def _apply_async(self, id_: int, func: Callable, *args, **kwargs) -> Any:
        """ A wrapper to apply functions to current views. """
        file = self.m.get_file(id_)
        # apply function on the current file
        val = func(file, *args, **kwargs)

        # make sure that appropriate views will be updated
        views = self.v.all_views if Settings.ALL_FILES else [self.v.current_view]
        for view in views:
            view.next_update_forced = True

        # apply function to all other widgets asynchronously
        if Settings.ALL_FILES:
            other_files = self.m.get_other_files()
            w = IterWorker(func, other_files, *args, **kwargs)
            self.thread_pool.start(w)

        return val

    @staticmethod
    def update_variable_name(
            file: ResultsFile, variable_name: str, key_name: str, variable: Variable
    ) -> Variable:
        """ Rename given 'Variable'. """
        _, var = file.rename_variable(variable, variable_name, key_name)
        return var

    @staticmethod
    def delete_variables(file: ResultsFile, variables: List[Variable]) -> None:
        """ Hide or remove selected variables. """
        file.remove_outputs(variables)

    @staticmethod
    def aggregate_variables(
            file: ResultsFile,
            variables: List[Variable],
            var_name: str,
            key_name: str,
            func: Union[str, Callable],
    ) -> tuple:
        """ Add a new aggregated variable to the file. """
        res = file.aggregate_variables(
            variables, func, key_name=key_name, var_name=var_name, part_match=False
        )
        if res:
            var_id, var = res
            return var

    def on_variable_rename_requested(self, id_: int, variable_data: VariableData) -> None:
        """ Overwrite variable name. """
        old_variable_name = variable_data.type
        old_key_name = variable_data.key
        res = self.v.confirm_rename_variable(old_variable_name, old_key_name)
        if res:
            new_variable_name, new_key_name = res
            if new_variable_name != old_variable_name or new_key_name != old_key_name:
                var = self.m.selected_variables[0]
                new_variable = self._apply_async(
                    id_, self.update_variable_name, new_variable_name, new_key_name, var
                )
                new_variable_data = VariableData(
                    key=new_variable.key,
                    type=new_variable.type,
                    units=variable_data.units,
                    proxyunits=variable_data.proxyunits
                )
                self.v.build_treeview(
                    self.m.get_file(id_).get_header_df(Settings.INTERVAL),
                    selected=[new_variable_data],
                    scroll_to=new_variable_data,
                )

    def on_file_rename_requested(self, id_: int) -> None:
        """ Update file name. """
        name = self.m.get_file_name(id_)
        other_names = self.m.get_other_file_names()
        new_name = self.m.confirm_rename_file(name, other_names)
        if new_name:
            self.m.rename_file(id_, name)

    def handle_remove_variables(self, id_: int, variables: List[tuple]) -> None:
        """ Remove variables from a file or all files. """
        self._apply_async(id_, self.delete_variables, variables)
        self.v.build_treeview(self.m.get_file(id_).get_header_df(Settings.INTERVAL))

    def handle_aggregate_variables(
            self,
            id_: int,
            variables: List[tuple],
            var_nm: str,
            key_nm: str,
            func: Union[str, Callable],
    ) -> None:
        """ Create a new variable using given aggregation function. """
        variable = self._apply_async(id_, self.aggregate_variables, variables, var_nm, key_nm,
                                     func)
        self.v.build_treeview(
            self.m.get_file(id_).get_header_df(Settings.INTERVAL),
            selected=[variable],
            scroll_to=variable,
        )

    def handle_close_tab(self, id_: int) -> None:
        """ Delete file from the database. """
        self.ids.remove(id_)
        self.m.delete_file(id_)
