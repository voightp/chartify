from chartify.settings import Settings
from chartify.view.css_theme import parse_palette, Palette
from chartify.charts.trace import Trace
from chartify.charts.chart import Chart
from chartify.utils.typehints import ResultsFile

from eso_reader.eso_file import get_results
from PySide2.QtCore import Signal, QObject

from typing import List, Union
import pandas as pd


class AppModel(QObject):
    """
    A class which holds and provides access to the
    application database.

    The database is being held in memory as it works
    as a standard python  dictionary at the moment.

    """
    fullUpdateRequested = Signal(dict)

    def __init__(self):
        super().__init__()
        # ~~~~ File Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.database = {}

        # ~~~~ Temporary ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.selected_variables = []

        # ~~~~ Webview Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.traces = []
        self.components = {}
        self.items = {}

        # ~~~~ Palettes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.palettes = parse_palette(Settings.PALETTE_PATH)

    def get_results(self, **kwargs) -> pd.DataFrame:
        """ Get output values for given variables. """
        if Settings.ALL_FILES:
            files = self.fetch_all_files()
        else:
            files = self.fetch_file(Settings.CURRENT_SET_ID)

        args = (files, self.selected_variables)
        kwargs = {
            "rate_units": Settings.POWER_UNITS,
            "energy_units": Settings.ENERGY_UNITS,
            "add_file_name": "column",
            "rate_to_energy_dct": {
                Settings.INTERVAL: Settings.RATE_TO_ENERGY
            },
            **kwargs
        }

        return get_results(*args, **kwargs)

    def fetch_all_trace_ids(self) -> List[str]:
        """ Get all used trace ids. """
        return [trace.trace_id for trace in self.traces]

    def fetch_trace(self, trace_id: str) -> Trace:
        """ Get trace of a given id. """
        for trace in self.traces:
            if trace.trace_id == trace_id:
                return trace

    def fetch_traces(self, item_id: str) -> List[Trace]:
        """ Get traces assigned for a given item. """
        traces = []
        for trace in self.traces:
            if trace.item_id == item_id:
                traces.append(trace)

        return traces

    def fetch_all_item_ids(self) -> List[str]:
        """ Get all used item ids. """
        return list(self.items.keys())

    def fetch_component(self, item_id: str) -> Union[Chart]:
        """ Get displayed object from the database."""
        try:
            return self.components[item_id]
        except KeyError:
            raise KeyError(f"Cannot find component '{item_id}'.")

    def fetch_palette(self, name: str) -> Palette:
        """ Get 'Palette' object with a specified name. """
        try:
            return self.palettes[name]
        except KeyError:
            raise KeyError(f"Cannot find palette '{name}'.")

    def fetch_file(self, set_id: str) -> ResultsFile:
        """ Fetch a single file from the database. """
        file_id = f"t{set_id}" if Settings.TOTALS else f"s{set_id}"
        try:
            return self.database[file_id]
        except KeyError:
            raise KeyError(f"Cannot find file {file_id} in database!")

    def fetch_files(self, *args: str) -> List[ResultsFile]:
        """ Fetch multiple files from the database. """
        files = []
        for set_id in args:
            f = self.fetch_file(set_id)
            if f:
                files.append(f)
        return files

    def fetch_all_files(self) -> List[ResultsFile]:
        """ Fetch all files from the database. """
        files = []
        for set_id in self.get_all_set_ids():
            f = self.fetch_file(set_id)
            if f:
                files.append(f)
        return files

    def fetch_header_variables(self, set_id: str, interval: str) -> List[tuple]:
        """ Fetch a file header variables for a given interval. """
        file = self.fetch_file(set_id)
        if file:
            return list(file.header_dct[interval].values())

    def get_all_file_ids(self) -> List[str]:
        """ Return all file ids for a current state. """
        ids = []
        for file_id in self.database.keys():
            if file_id.startswith("t" if Settings.TOTALS else "s"):
                ids.append(file_id)
        return ids

    def get_all_set_ids(self) -> List[str]:
        """ Get a list of already used ids (without s,t identifier). """
        return [id_[1:] for id_ in self.get_all_file_ids()]

    def get_all_file_names(self) -> List[str]:
        """ Get all used file names. """
        return [f.file_name for f in self.database.values()]

    def delete_file(self, file_id: str) -> None:
        """ Delete file from the database. """
        try:
            del self.database[file_id]
        except KeyError:
            print(f"Cannot delete file: id '{file_id}',"
                  f"\nFile was not found in the database.")

    def delete_sets(self, *args: str) -> None:
        """ Delete specified sets from the database. """
        for set_id in args:
            self.delete_file(f"s{set_id}")
            self.delete_file(f"t{set_id}")

    def rename_file(self, file_id: str, name: str):
        """ Rename given file. """
        try:
            file = self.database[file_id]
            file.rename(name)
        except KeyError:
            print(f"Cannot rename file: '{file_id}',"
                  f"\nFile was not found in database.")

    def rename_set(self, set_id: str, name: str, totals_name: str):
        """ Rename a file set in the database. """
        self.rename_file(f"s{set_id}", name)
        self.rename_file(f"t{set_id}", totals_name)

    def add_file(self, file_id: str, file: ResultsFile) -> None:
        """ Add processed results file to the database. """
        try:
            self.database[file_id] = file
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")
