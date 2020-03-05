import os
from multiprocessing import Manager
from typing import List, Callable, Union, Any, Dict

from PySide2.QtCore import QThreadPool
from esofile_reader.storage.storage_files import ParquetFile
from esofile_reader.utils.mini_classes import ResultsFile
from profilehooks import profile

from chartify.settings import Settings
from chartify.utils.process_utils import create_pool, kill_child_processes, load_file
from chartify.utils.threads import EsoFileWatcher, IterWorker, Monitor
from chartify.utils.utils import get_str_identifier


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
        self.watcher.loaded.connect(self.on_file_loaded)
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
        self.v.viewUpdateRequested.connect(self.handle_view_update)
        self.v.fileProcessingRequested.connect(self.handle_file_processing)
        self.v.fileRenamed.connect(self.handle_file_rename)
        self.v.variableRenamed.connect(self.handle_rename_variable)
        self.v.variablesRemoved.connect(self.handle_remove_variables)
        self.v.variablesAggregated.connect(self.handle_aggregate_variables)
        self.v.tabClosed.connect(self.handle_close_tab)
        self.v.appClosedRequested.connect(self.tear_down)
        self.v.selectionChanged.connect(self.handle_selection_change)
        self.v.close_all_act.triggered.connect(lambda x: x)
        self.v.save_act.triggered.connect(self.on_save)
        self.v.save_as_act.triggered.connect(self.on_save_as)

    def handle_selection_change(self, variables: List[tuple]) -> None:
        """ Handle selection update. """
        out_str = [" | ".join(var) for var in variables]
        print("handle_selection_change!\n\t{}".format("\n\t".join(out_str)))
        self.m.selected_variables = variables

    def connect_model_signals(self) -> None:
        """ Create monitor signals. """
        self.monitor.file_added.connect(self.v.progress_cont.add_file)
        self.monitor.bar_updated.connect(self.v.progress_cont.update_progress)
        self.monitor.range_changed.connect(self.v.progress_cont.set_range)
        self.monitor.pending.connect(self.v.progress_cont.set_pending)
        self.monitor.failed.connect(self.v.progress_cont.set_failed)

    def on_save(self):
        if not self.m.storage.path:
            self.on_save_as()
        else:
            self.m.storage.save()

    def on_save_as(self):
        path = self.v.save_storage_to_fs()
        if path:
            self.m.storage.save_as(path.parent, path.stem)

    @profile(sort="time")
    def handle_view_update(self, id_: int) -> None:
        """ Update content of a newly selected tab. """
        file = self.m.get_file(id_)

        # update interface to enable only available interval buttons
        # and rate to energy button when applicable
        self.v.toolbar.update_intervals_state(file.available_intervals)
        self.v.toolbar.update_rate_to_energy_state(Settings.INTERVAL)

        self.v.build_view(file.get_header_dictionary(Settings.INTERVAL).values(),
                          selected=self.m.selected_variables)

    def handle_file_processing(self, paths: List[str]) -> None:
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
                self.lock
            )

    def on_file_loaded(self, monitor_id: str, files: Dict[int, ParquetFile]) -> None:
        """ Add eso file into 'tab' widget. """
        for id_, file in files.items():
            # make sure that file name is unique
            names = self.m.get_all_file_names()
            name = get_str_identifier(file.file_name, names)
            file.rename(name)

            # store file reference in model
            self.m.storage.files[id_] = file

            # add new tab into tab widget
            self.v.add_new_tab(id_, name)

        # remove progress bar from ui
        self.v.progress_cont.remove_file(monitor_id)

    def _apply_async(self, id_: int, func: Callable, *args, **kwargs) -> Any:
        """ A wrapper to apply functions to current views. """
        file = self.m.get_file(id_)

        # apply function on the current file
        val = func(file, *args, **kwargs)

        # apply function to all other widgets asynchronously
        if Settings.ALL_FILES:
            other_files = self.m.get_other_files()
            w = IterWorker(func, other_files, *args, **kwargs)
            self.thread_pool.start(w)

        return val

    @staticmethod
    def rename_var(file: ResultsFile, var_nm: str,
                   key_nm: str, variable: tuple) -> tuple:
        """ Rename given 'Variable'. """
        res = file.rename_variable(variable, var_nm, key_nm)
        if res:
            var_id, var = res
            return var

    def handle_rename_variable(self, id_: int, variable: tuple,
                               var_nm: str, key_nm: str) -> None:
        """ Overwrite variable name. """
        variable = self._apply_async(id_, self.rename_var, var_nm, key_nm, variable)
        self.v.build_view(
            self.m.get_file(id_).get_header_dictionary(Settings.INTERVAL).values(),
            selected=[variable], scroll_to=variable
        )

    def handle_file_rename(self, id_: int, name: str) -> None:
        """ Update file name. """
        self.m.rename_file(id_, name)

    @staticmethod
    def dump_vars(file: ResultsFile, variables: List[tuple]) -> None:
        """ Hide or remove selected variables. """
        file.remove_outputs(variables)

    def handle_remove_variables(self, id_: int, variables: List[tuple]) -> None:
        """ Remove variables from a file or all files. """
        self._apply_async(id_, self.dump_vars, variables)
        self.v.build_view(
            self.m.get_file(id_).get_header_dictionary(Settings.INTERVAL).values()
        )

    @staticmethod
    def aggr_vars(file: ResultsFile, variables: List[tuple], var_nm: str,
                  key_nm: str, func: Union[str, Callable]) -> tuple:
        """ Add a new aggregated variable to the file. """
        res = file.aggregate_variables(variables, func,
                                       key_name=key_nm,
                                       var_name=var_nm,
                                       part_match=False)
        if res:
            var_id, var = res
            return var

    def handle_aggregate_variables(self, id_: int, variables: List[tuple], var_nm: str,
                                   key_nm: str, func: Union[str, Callable]) -> None:
        """ Create a new variable using given aggregation function. """
        variable = self._apply_async(id_, self.aggr_vars, variables, var_nm, key_nm, func)
        self.v.build_view(
            self.m.get_file(id_).get_header_dictionary(Settings.INTERVAL).values(),
            selected=[variable], scroll_to=variable
        )

    def handle_close_tab(self, id_: int) -> None:
        """ Delete file from the database. """
        self.ids.remove(id_)
        self.m.delete_file(id_)
