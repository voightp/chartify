from functools import partial
import os
from queue import Queue

from PySide2.QtCore import QThreadPool
from multiprocessing import Manager
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

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.watcher = EsoFileWatcher(self.file_queue)
        self.watcher.loaded.connect(self.on_file_loaded)
        self.watcher.start()

        self.monitor = Monitor(self.progress_queue)
        self.monitor.start()

        # ~~~~ Thread executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.thread_pool = QThreadPool()

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.file_queue = Queue()
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()

        # ~~~~ Process executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.pool = create_pool()

    def tear_down(self):
        self.watcher.terminate()
        self.monitor.terminate()
        self.manager.shutdown()

        # terminate background processes
        kill_child_processes(os.getpid())

    def connect_view_signals(self):
        self.v.viewUpdateRequested.connect(self.handle_view_update)
        self.v.paletteChanged.connect()
        self.v.fileProcessingRequested.connect(self.handle_file_processing)
        self.v.fileRenamed.connect()
        self.v.variableRenamed.connect(self.handle_rename_variable)
        self.v.variablesRemoved.connect(self.handle_remove_variables)
        self.v.tabClosed.connect()

        self.v.close_all_act.triggered.connect(self.close_all_tabs)
        self.v.hide_act.triggered.connect(self.hide_vars)
        self.v.remove_hidden_act.triggered.connect(self.remove_hidden_vars)
        self.v.show_hidden_act.triggered.connect(self.show_hidden_vars)

        self.v.sum_act.triggered.connect(partial(self.add_var, "sum"))
        self.v.mean_act.triggered.connect(partial(self.add_var, "mean"))
        self.v.save_act.triggered.connect(lambda x: print("SAVE ACT!"))
        self.v.save_as_act.triggered.connect(lambda x: print("SAVE AS ACT!"))

    def connect_model_signals(self):
        """ Create monitor actions. """
        self.monitor.initialized.connect(self.v.progress_cont.add_file)
        self.monitor.started.connect(self.v.progress_cont.update_progress_text)
        self.monitor.text_updated.connect(self.v.progress_cont.update_progress_text)
        self.monitor.bar_updated.connect(self.v.progress_cont.update_file_progress)
        self.monitor.preprocess_finished.connect(self.v.progress_cont.set_max_value)
        self.monitor.failed.connect(self.v.progress_cont.set_failed)

    def handle_view_update(self, id_):
        """ Update content of a newly selected tab. """
        file = self.m.fetch_file(id_)

        # update interface to enable only available interval buttons
        # and rate to energy button when applicable
        self.v.toolbar.update_intervals_state(file.available_intervals)
        self.v.toolbar.update_rate_to_energy_state()

        self.v.build_view(list(file.header_dct[Settings.INTERVAL].values()))

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
        names = self.m.get_all_names_from_db()
        name = get_str_identifier(std_file.file_name, names)

        std_file.rename(name)
        tot_file.rename(f"{name} - totals")

        self.m.add_file_to_db(f"s{id_}", std_file)
        self.m.add_file_to_db(f"t{id_}", tot_file)

        self.v.progress_cont.remove_file(id_)

    @staticmethod
    def rename_var(file, var_nm, key_nm, variable):
        """ Rename given 'Variable'. """
        return file.rename_variable(variable, var_nm, key_nm)

    def handle_rename_variable(self, id_, var_nm, key_nm, variable):
        current_file = self.m.fetch_file(id_)
        other_files = None

        if Settings.ALL_FILES:
            ids = self.m.get_all_file_ids(Settings.TOTALS)
            ids.remove(id_)
            other_files = self.m.fetch_files(*ids)

        var = self.apply_async(self.rename_var, current_file, var_nm,
                               key_nm, variable, others=other_files)

        self.v.current_view.select_variables(var)
        self.v.current_view.scroll_to(var)

        variables = list(current_file.header_dct[Settings.INTERVAL].values())
        self.v.build_view(variables)

    def handle_file_rename(self):
        pass

    @staticmethod
    def dump_vars(file, variables):
        """ Hide or remove selected variables. """
        file.remove_outputs(variables)

    def handle_remove_variables(self, id_, variables):
        """ Remove variables from a file or all files. """
        file = self.m.fetch_file(id_)
        other_files = None

        if Settings.ALL_FILES:
            ids = self.m.get_all_file_ids(Settings.TOTALS)
            ids.remove(id_)
            other_files = self.m.fetch_files(*ids)

        self.apply_async(self.dump_vars, file,
                         variables, others=other_files)

        self.v.build_view(list(file.header_dct[Settings.INTERVAL].values()))

    @staticmethod
    def aggr_vars(file, var_nm, key_nm, variables, func):
        """ Add a new aggregated variable to the file. """
        res = file.aggregate_variables(variables, func,
                                       key_nm=key_nm,
                                       var_nm=var_nm,
                                       part_match=False)
        if res:
            var_id, var = res
            return var

    def add_var(self, aggr_func):
        """ Create a new variable using given aggr function. """
        variables = self.get_current_request()

        # retrieve variable name from ui
        msg = "Enter details of the new variable: "
        res = self.get_new_name(variables, msg=msg)

        if res:
            var_nm, key_nm = res
            var = self.apply_async(self.aggr_vars, var_nm, key_nm,
                                   variables, aggr_func)

            self.selected = [var]
            self.rebuild_view()
            self.current_view_wgt.scroll_to(var)

    def apply_async(self, func, first, *args, others=None, **kwargs):
        """ A wrapper to apply functions to current views. """
        # apply function to the current file
        val = func(first, *args, **kwargs)

        # apply function to all other widgets asynchronously
        if others:
            w = IterWorker(func, others, *args, **kwargs)
            self.thread_pool.start(w)

        return val

    def hide_vars(self):
        """ Temporarily hide variables. """
        variables = self.get_current_request()
        self.apply_async(self.dump_vars, variables)

        # allow showing variables again
        self.show_hidden_act.setEnabled(True)
        self.toolbar.hide_btn.setEnabled(True)

        self.rebuild_view()

    def show_hidden_vars(self):
        """ Show previously hidden variables. """
        for view in self.current_view_wgts:
            view.show_hidden_header_variables()
            view.set_next_update_forced()

        self.show_hidden_act.setEnabled(False)
        self.toolbar.hide_btn.setEnabled(False)

        self.rebuild_view()

    def remove_hidden_vars(self):
        """ Remove hidden variables. """
        for view in self.current_view_wgts:
            view.remove_hidden_header_variables()
