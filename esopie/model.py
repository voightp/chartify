import os

from PySide2.QtCore import QThreadPool
from multiprocessing import Manager
from functools import partial
from copy import deepcopy

from esopie.threads import MonitorThread
from queue import Queue

from PySide2.QtCore import Signal, Qt
from PySide2.QtCore import QSize, Qt, Signal, QSettings

from esopie.utils.utils import generate_ids, get_str_identifier
from esopie.utils.process_utils import (create_pool, kill_child_processes,
                                        load_file, wait_for_results)
from esopie.threads import (EsoFileWatcher, GuiMonitor, ResultsFetcher,
                            IterWorker)


class AppModel:
    fileLoaded = Signal(str, str)

    def __init__(self):
        settings = QSettings()

        # ~~~~ Intermediate settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.selected_variables = None
        self.all_files_selected = False
        self.totals_selected = False
        self.units_settings = {
            "energy_units": settings.value("Toolbar/energyUnits", "kWh"),
            "power_units": settings.value("Toolbar/powerUnits", "kW"),
            "units_system": settings.value("Toolbar/unitsSystem", "SI"),
            "rate_to_energy": bool(settings.value("Toolbar/rateToEnergy", 0))
        }

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.file_queue = Queue()
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()

        # ~~~~ Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.database = {"standard": {},
                         "totals": {}}

        # ~~~~ Process executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.pool = create_pool()

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.watcher = EsoFileWatcher(self.file_queue)
        self.watcher.loaded.connect(self.on_file_loaded)
        self.watcher.start()

        self.monitor = MonitorThread(self.progress_queue)
        self.monitor.start()

        # ~~~~ Thread executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.thread_pool = QThreadPool()

    def tear_down(self):
        self.watcher.terminate()
        self.monitor.terminate()
        self.manager.shutdown()

        kill_child_processes(os.getpid())

    def process_eso_files(self, eso_file_paths):
        """ Start eso file processing. """
        used_ids = self.get_used_ids_from_db()
        ids = generate_ids(used_ids, n=len(eso_file_paths))

        for path in eso_file_paths:
            # create a monitor to report progress on the ui
            id_ = ids.pop(0)
            monitor = GuiMonitor(path, id_, self.progress_queue)

            # create a new process to load eso file
            future = self.pool.submit(load_file, path, monitor=monitor,
                                      suppress_errors=False)

            func = partial(wait_for_results, id_, monitor, self.file_queue)
            future.add_done_callback(func)

    def get_current_file_ids(self):
        """ Return current file id or ids based on 'all files btn' state. """
        if self.all_files_requested():
            return [f.get_file_id() for f in self.all_view_wgts]

        return [self.current_view_wgt.get_file_id()]

    def on_file_loaded(self, id_, std_file, tot_file):
        """ Add eso file into 'tab' widget. """
        std_id = f"s{id_}"
        tot_id = f"t{id_}"

        # create unique file name
        names = self.get_all_names_from_db()
        name = get_str_identifier(std_file.file_name, names)

        std_file.rename(name)
        tot_file.rename(f"{name} - totals")

        file_set = {std_id: std_file,
                    tot_id: tot_file}

        self.add_set_to_db(id_, file_set)

        self.fileLoaded.emit(id_, name)

    def remove_vars(self):
        """ Remove variables from a file. """
        variables = self.get_current_request()

        if not variables:
            return

        all_ = self.toolbar.all_files_requested()
        nm = self.tab_wgt.tabText(self.tab_wgt.currentIndex())

        files = "all files" if all_ else f"file '{nm}'"
        text = f"Delete following variables from {files}: "

        inf_text = "\n".join([" | ".join(var[1:3]) for var in variables])

        dialog = ConfirmationDialog(self, text, det_text=inf_text)
        res = dialog.exec_()

        if res == 0:
            return

        self.apply_async(self.dump_vars, variables, remove=True)
        self.rebuild_view()

    def hide_vars(self):
        """ Temporarily hide variables. """
        variables = self.get_current_request()
        self.apply_async(self.dump_vars, variables)

        # allow showing variables again
        self.show_hidden_act.setEnabled(True)
        self.toolbar.hide_btn.setEnabled(True)

        self.rebuild_view()

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

    def aggr_vars(self, view, var_nm, key_nm, variables, func):
        """ Add a new aggreagated variable to the file. """
        file_id = view.get_file_id()

        # files are always returned as list
        file = self.get_files_from_db(file_id)[0]

        res = file.aggregate_variables(variables, func,
                                       key_nm=key_nm,
                                       var_nm=var_nm,
                                       part_match=False)
        if res:
            var_id, var = res
            view.set_next_update_forced()

            return var

    def dump_vars(self, view, variables, remove=False):
        """ Hide or remove selected variables. """
        file_id = view.get_file_id()
        file = self.get_files_from_db(file_id)[0]

        groups = file.find_pairs(variables)

        if not groups:
            return

        if remove:
            view.remove_header_variables(groups)
            file.remove_outputs(variables)
        else:
            view.hide_header_variables(groups)

        view.set_next_update_forced()

    def apply_async(self, func, *args, **kwargs):
        """ A wrapper to apply functions to current views. """
        # apply function to the current widget
        view = self.current_view_wgt
        val = func(view, *args, **kwargs)

        # apply function to all other widgets asynchronously
        others = self.all_other_view_wgts
        if others:
            w = IterWorker(func, others, *args, **kwargs)
            self.thread_pool.start(w)

        return val

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

    def rename_var(self, view, var_nm, key_nm, variable):
        """ Rename given 'Variable'. """
        file_id = view.get_file_id()
        file = self.get_files_from_db(file_id)[0]

        res = file.rename_variable(variable, var_nm, key_nm)
        if res:
            var_id, var = res
            # add variable will replace current variable
            view.add_header_variable(var_id, var)
            view.set_next_update_forced()

            return var

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

    def get_all_names_from_db(self):
        """ Get all file names. """
        names = []
        for file_set in self.database.values():
            for f in file_set.values():
                names.append(f.name)
        return names

    def get_used_ids_from_db(self):
        """ Get a list of already used set ids. """
        return self.database.keys()

    def delete_sets_from_db(self, *args):
        """ Delete the eso file from the database. """
        for id_ in args:
            try:
                print(f"Deleting file id: '{id_}' from database.")
                del self.database[id_]
            except KeyError:
                print(f"Cannot delete eso file: id '{id_}',"
                      f"\nFile was not found in database.")

    def rename_file_in_db(self, id_, f_name, totals_f_name):
        """ Rename file in the databases. """
        try:
            f_set = self.database[id_]
            f_set[f"s{id_}"].rename(f_name)
            f_set[f"t{id_}"].rename(totals_f_name)
        except KeyError:
            print(f"Cannot rename eso file: id '{id_}',"
                  f"\nFile was not found in database.")

    def get_files_from_db(self, *args):
        """ Fetch eso files from the database. """
        files = []

        for set_id, file_dct in self.database.items():
            try:
                f = next(f for f_id, f in file_dct.items() if f_id in args)
                files.append(f)
            except StopIteration:
                pass

        if len(args) != len(files):
            diff = set(args).difference(set(files))
            diff_str = ", ".join(list(diff))
            print(f"Cannot find '{diff_str}' files in db!")

        return files

    def add_set_to_db(self, id_, file_set):
        """ Add processed eso file to the database. """
        try:
            self.database[id_] = file_set
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")
