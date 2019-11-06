import os
from multiprocessing import Manager
from queue import Queue

from PySide2.QtCore import QThreadPool
from functools import partial

from esopie.settings import Settings
from esopie.utils.process_utils import (create_pool, kill_child_processes,
                                        load_file, wait_for_results)
from esopie.controller.threads import (EsoFileWatcher, GuiMonitor, ResultsFetcher,
                                       IterWorker, Monitor)
from esopie.utils.utils import generate_ids, get_str_identifier


class AppController:
    def __init__(self, model, view):
        self.v = view
        self.m = model

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

    def tear_down(self):
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

    def connect_view_signals(self):
        self.v.viewUpdateRequested.connect(self.handle_view_update)
        self.v.paletteChanged.connect(lambda x: x)
        self.v.fileProcessingRequested.connect(self.handle_file_processing)
        self.v.fileRenamed.connect(self.handle_file_rename)
        self.v.variableRenamed.connect(self.handle_rename_variable)
        self.v.variablesRemoved.connect(self.handle_remove_variables)
        self.v.variablesAggregated.connect(self.handle_aggregate_variables)
        self.v.tabClosed.connect(self.handle_close_tab)
        self.v.appClosedRequested.connect(self.tear_down)
        self.v.close_all_act.triggered.connect(lambda x: x)

        self.v.save_act.triggered.connect(lambda x: print("SAVE ACT!"))
        self.v.save_as_act.triggered.connect(lambda x: print("SAVE AS ACT!"))

    def connect_model_signals(self):
        """ Create monitor actions. """
        self.monitor.initialized.connect(self.v.progress_cont.add_file)
        self.monitor.started.connect(self.v.progress_cont.update_progress_text)
        self.monitor.bar_updated.connect(self.v.progress_cont.update_file_progress)
        self.monitor.preprocess_finished.connect(self.v.progress_cont.set_max_value)
        self.monitor.finished.connect(self.v.progress_cont.set_pending)
        self.monitor.failed.connect(self.v.progress_cont.set_failed)

    def handle_view_update(self, id_):
        """ Update content of a newly selected tab. """
        file = self.m.fetch_file(id_)

        # update interface to enable only available interval buttons
        # and rate to energy button when applicable
        self.v.toolbar.update_intervals_state(file.available_intervals)
        self.v.toolbar.update_rate_to_energy_state(Settings.INTERVAL)

        variables = self.m.fetch_file_header_variables(id_, Settings.INTERVAL)
        self.v.build_view(variables)

    def handle_file_processing(self, paths):
        """ Load new files. """
        used_ids = self.m.get_all_set_ids()
        ids = generate_ids(used_ids, n=len(paths))

        for path in paths:
            id_ = ids.pop(0)
            monitor = GuiMonitor(path, id_, self.progress_queue)
            future = self.pool.submit(load_file, path, monitor=monitor,
                                      suppress_errors=False)

            func = partial(wait_for_results, id_, monitor, self.file_queue)
            future.add_done_callback(func)

    def on_file_loaded(self, id_, std_file, tot_file):
        """ Add eso file into 'tab' widget. """
        names = self.m.get_all_file_names()
        name = get_str_identifier(std_file.file_name, names)

        std_file.rename(name)
        tot_file.rename(f"{name} - totals")

        self.m.add_file(f"s{id_}", std_file)
        self.m.add_file(f"t{id_}", tot_file)

        self.v.add_new_tab(id_, name)
        self.v.progress_cont.remove_file(id_)

    def apply_async(self, id_, func, *args, **kwargs):
        """ A wrapper to apply functions to current views. """
        file = self.m.fetch_file(id_)
        other_files = None

        if Settings.ALL_FILES:
            ids = self.m.get_all_file_ids()
            ids.remove(id_)
            other_files = self.m.fetch_files(*ids)

        # apply function on the current file
        val = func(file, *args, **kwargs)

        # apply function to all other widgets asynchronously
        if other_files:
            w = IterWorker(func, other_files, *args, **kwargs)
            self.thread_pool.start(w)

        return val

    @staticmethod
    def rename_var(file, var_nm, key_nm, variable):
        """ Rename given 'Variable'. """
        res = file.rename_variable(variable, var_nm, key_nm)
        if res:
            var_id, var = res
            return var

    def handle_rename_variable(self, id_, variable, var_nm, key_nm):
        """ Overwrite variable name. """
        var = self.apply_async(id_, self.rename_var, var_nm, key_nm, variable)

        variables = self.m.fetch_file_header_variables(id_, Settings.INTERVAL)
        self.v.build_view(variables, scroll_to=var)

    def handle_file_rename(self, id_, name, totals_name):
        """ Update file name. """
        self.m.rename_set(id_, name, totals_name)

    @staticmethod
    def dump_vars(file, variables):
        """ Hide or remove selected variables. """
        file.remove_outputs(variables)

    def handle_remove_variables(self, id_, variables):
        """ Remove variables from a file or all files. """
        self.apply_async(id_, self.dump_vars, variables)
        variables = self.m.fetch_file_header_variables(id_, Settings.INTERVAL)

        self.v.build_view(variables)

    @staticmethod
    def aggr_vars(file, variables, var_nm, key_nm, func):
        """ Add a new aggregated variable to the file. """
        res = file.aggregate_variables(variables, func,
                                       key_nm=key_nm,
                                       var_nm=var_nm,
                                       part_match=False)
        if res:
            var_id, var = res
            return var

    def handle_aggregate_variables(self, id_, variables, var_nm, key_nm, func):
        """ Create a new variable using given aggregation function. """
        var = self.apply_async(id_, self.aggr_vars, variables, var_nm, key_nm, func)
        variables = self.m.fetch_file_header_variables(id_, Settings.INTERVAL)

        self.v.build_view(variables, scroll_to=var)

    def handle_close_tab(self, id_):
        """ Delete set from the database. """
        self.m.delete_sets(id_)

    def get_results(self, callback=None, **kwargs):
        """ Get output values for given variables. """
        rate_to_energy, units_system, energy, power = self.get_units_settings()
        rate_to_energy_dct = {self.get_current_interval(): rate_to_energy}

        ids = self.get_current_file_ids()
        files = self.get_files_from_db(*ids)

        args = (files, self.selected_variables)
        kwargs = {"rate_units": power, "energy_units": energy,
                  "add_file_name": "column",
                  "rate_to_energy_dct": rate_to_energy_dct,
                  **kwargs}

        self.thread_pool.start(ResultsFetcher(get_results, *args,
                                              callback=callback, **kwargs))
