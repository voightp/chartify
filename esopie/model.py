import os

from PySide2.QtCore import QThreadPool
from multiprocessing import Manager
from functools import partial
from copy import deepcopy

from esopie.threads import MonitorThread
from queue import Queue

from PySide2.QtCore import Signal, Qt
from PySide2.QtCore import QSize, Qt, Signal, QSettings

from esopie.eso_file_header import FileHeader
from esopie.utils.utils import generate_ids, get_str_identifier
from esopie.utils.process_utils import (create_pool, kill_child_processes,
                                        load_file, wait_for_results)
from esopie.threads import (EsoFileWatcher, GuiMonitor, ResultsFetcher,
                            IterWorker)


class AppModel:
    file_loaded = Signal(str, FileHeader, FileHeader)

    def __init__(self):
        settings = QSettings()

        # ~~~~ Intermediate settings ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.selected_variables = None
        self.all_files_selected = False
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
        self.database = {}

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
        self.manager.shutdown()

        kill_child_processes(os.getpid())

    def load_files(self, eso_file_paths):
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

        # copy header dicts as view and file should be independent
        std_header_dct = deepcopy(std_file.header_dct)
        tot_header_dct = deepcopy(tot_file.header_dct)

        std_header = FileHeader(std_id, std_header_dct)
        tot_header = FileHeader(tot_id, tot_header_dct)

        file_set = {std_id: std_file,
                    tot_id: tot_file}

        self.add_set_to_db(id_, file_set)

        self.file_loaded.emit(id_, name, std_header, tot_header)

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
