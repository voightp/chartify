import os

from PySide2.QtCore import QThreadPool
from multiprocessing import Manager
from functools import partial

from esopie.controller.threads import Monitor
from queue import Queue

from PySide2.QtCore import Signal

from esopie.utils.utils import generate_ids, get_str_identifier
from esopie.settings import Settings
from esopie.utils.process_utils import (create_pool, kill_child_processes,
                                        load_file, wait_for_results)
from esopie.controller.threads import (EsoFileWatcher, GuiMonitor, ResultsFetcher,
                                       IterWorker)


class AppModel:
    def __init__(self):
        # ~~~~ Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.database = {}

    def fetch_file(self, id_):
        """ Fetch file from database. """
        id_ = f"t{id_}" if Settings.TOTALS else f"s{id_}"
        try:
            return self.database[id_]
        except KeyError:
            raise KeyError(f"Cannot find file {id_} in database!")

    def fetch_files(self, *args):
        """ Fetch eso files from the database. """
        files = []
        for id_ in args:
            f = self.fetch_file(id_)
            if f:
                files.append(f)
        return files

    def get_all_file_ids(self, totals):
        """ Return all file ids for given state. """
        ids = []
        for id_ in self.database.keys():
            if id_.startswith("t" if totals else "s"):
                ids.append(id_)
        return ids

    def get_all_set_ids(self):
        """ Get a list of already used ids (without s,t identifier). """
        return [id_[1:] for id_ in self.get_all_file_ids(False)]

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

    def add_file_to_db(self, id_, file):
        """ Add processed eso file to the database. """
        try:
            self.database[id_] = file
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")
