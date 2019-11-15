import os

from multiprocessing import Manager
from queue import Queue
from typing import List, Callable, Union, Any
from functools import partial

from PySide2.QtCore import QThreadPool

from chartify.utils.typehints import ResultsFile
from chartify.settings import Settings
from chartify.utils.process_utils import (create_pool, kill_child_processes,
                                          load_file, wait_for_results)
from chartify.controller.threads import (EsoFileWatcher, GuiMonitor,
                                         IterWorker, Monitor)
from chartify.utils.utils import generate_ids, get_str_identifier
from chartify.view.css_theme import CssTheme


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
        An access to application database.

    """

    def __init__(self, model, view):
        self.v = view
        self.m = model

        # ~~~~ Application layout ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.update_appearance()

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.file_queue = Queue()
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()

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

    def update_appearance(self) -> None:
        """ Update application appearance. """
        palette = self.m.palettes[Settings.PALETTE_NAME]

        css = CssTheme(Settings.CSS_PATH)
        css.populate_content(palette)
        self.v.set_css(css)

        c1 = palette.get_color("PRIMARY_TEXT_COLOR", as_tuple=True)
        c2 = palette.get_color("SECONDARY_TEXT_COLOR", as_tuple=True)
        self.v.load_scheme_btn_icons(self.m.palettes)
        self.v.load_icons(c1, c2)

        self.m.appearanceUpdateRequested.emit(palette.get_all_colors())

    def connect_view_signals(self) -> None:
        """ Connect view signals. """
        self.v.paletteUpdateRequested.connect(self.update_appearance)
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

        self.v.save_act.triggered.connect(lambda x: print("SAVE ACT!"))
        self.v.save_as_act.triggered.connect(lambda x: print("SAVE AS ACT!"))

    def handle_selection_change(self, variables: List[tuple]) -> None:
        """ Handle selection update. """
        out_str = [" | ".join(var) for var in variables]
        print("handle_selection_change!\n\t{}".format("\n\t".join(out_str)))
        self.m.selected_variables = variables

    def connect_model_signals(self) -> None:
        """ Create monitor signals. """
        self.monitor.initialized.connect(self.v.progress_cont.add_file)
        self.monitor.started.connect(self.v.progress_cont.update_progress_text)
        self.monitor.bar_updated.connect(self.v.progress_cont.update_file_progress)
        self.monitor.preprocess_finished.connect(self.v.progress_cont.set_max_value)
        self.monitor.finished.connect(self.v.progress_cont.set_pending)
        self.monitor.failed.connect(self.v.progress_cont.set_failed)

    def handle_view_update(self, set_id: str) -> None:
        """ Update content of a newly selected tab. """
        file = self.m.fetch_file(set_id)

        # update interface to enable only available interval buttons
        # and rate to energy button when applicable
        self.v.toolbar.update_intervals_state(file.available_intervals)
        self.v.toolbar.update_rate_to_energy_state(Settings.INTERVAL)

        variables = self.m.fetch_header_variables(set_id, Settings.INTERVAL)
        selected = self.m.selected_variables

        self.v.build_view(variables, selected=selected)

    def handle_file_processing(self, paths: List[str]) -> None:
        """ Load new files. """
        used_ids = self.m.get_all_set_ids()
        ids = generate_ids(used_ids, n=len(paths))

        for path in paths:
            id_ = ids.pop(0)
            monitor = GuiMonitor(path, id_, self.progress_queue)
            future = self.pool.submit(load_file, path, monitor=monitor,
                                      suppress_errors=False)

            func = partial(wait_for_results, id_, self.file_queue)
            future.add_done_callback(func)

    def on_file_loaded(self, id_: str, file: ResultsFile, tot_file: ResultsFile) -> None:
        """ Add eso file into 'tab' widget. """
        names = self.m.get_all_file_names()
        name = get_str_identifier(file.file_name, names)

        file.rename(name)
        tot_file.rename(f"{name} - totals")

        self.m.add_file(f"s{id_}", file)
        self.m.add_file(f"t{id_}", tot_file)

        self.v.add_new_tab(id_, name)
        self.v.progress_cont.remove_file(id_)

    def apply_async(self, set_id: str, func: Callable, *args, **kwargs) -> Any:
        """ A wrapper to apply functions to current views. """
        file = self.m.fetch_file(set_id)
        other_files = None

        if Settings.ALL_FILES:
            other_files = self.m.fetch_all_files()
            other_files.remove(file)

        # apply function on the current file
        val = func(file, *args, **kwargs)

        # apply function to all other widgets asynchronously
        if other_files:
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

    def handle_rename_variable(self, set_id: str, variable: tuple,
                               var_nm: str, key_nm: str) -> None:
        """ Overwrite variable name. """
        var = self.apply_async(set_id, self.rename_var, var_nm, key_nm, variable)

        variables = self.m.fetch_header_variables(set_id, Settings.INTERVAL)
        self.v.build_view(variables, scroll_to=var, selected=[var])

    def handle_file_rename(self, set_id: str, name: str, totals_name: str) -> None:
        """ Update file name. """
        self.m.rename_set(set_id, name, totals_name)

    @staticmethod
    def dump_vars(file: ResultsFile, variables: List[tuple]) -> None:
        """ Hide or remove selected variables. """
        file.remove_outputs(variables)

    def handle_remove_variables(self, set_id: str, variables: List[tuple]) -> None:
        """ Remove variables from a file or all files. """
        self.apply_async(set_id, self.dump_vars, variables)
        variables = self.m.fetch_header_variables(set_id, Settings.INTERVAL)

        self.v.build_view(variables)

    @staticmethod
    def aggr_vars(file: ResultsFile, variables: List[tuple], var_nm: str,
                  key_nm: str, func: Union[str, Callable]) -> tuple:
        """ Add a new aggregated variable to the file. """
        res = file.aggregate_variables(variables, func,
                                       key_nm=key_nm,
                                       var_nm=var_nm,
                                       part_match=False)
        if res:
            var_id, var = res
            return var

    def handle_aggregate_variables(self, set_id: str, variables: List[tuple], var_nm: str,
                                   key_nm: str, func: Union[str, Callable]) -> None:
        """ Create a new variable using given aggregation function. """
        var = self.apply_async(set_id, self.aggr_vars, variables, var_nm, key_nm, func)
        variables = self.m.fetch_header_variables(set_id, Settings.INTERVAL)

        self.v.build_view(variables, scroll_to=var, selected=[var])

    def handle_close_tab(self, id_: str) -> None:
        """ Delete set from the database. """
        self.m.delete_sets(id_)
