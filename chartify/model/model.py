from typing import List, Union

import pandas as pd
from PySide2.QtCore import Signal, QObject
from esofile_reader import get_results
from esofile_reader.utils.mini_classes import ResultsFile
from esofile_reader import TotalsFile

from chartify.charts.chart import Chart
from chartify.charts.trace import Trace1D, Trace2D, TraceData
from chartify.settings import Settings
from chartify.view.css_theme import parse_palette, Palette

from esofile_reader.storage.df_storage import DFStorage
from esofile_reader.storage.sql_storage import SQLStorage
from esofile_reader import DatabaseFile


class AppModel(QObject):
    """
    A class which holds and provides access to the
    application database.

    The database is being held in memory as it works
    as a standard python  dictionary at the moment.

    """

    def __init__(self):
        super().__init__()
        # ~~~~ File Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.storage = DFStorage()
        # self.storage.set_up_db("test.db")

        # ~~~~ Currently selected variables ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.selected_variables = []

        # ~~~~ Webview Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.wv_database = {
            "trace_data": [],
            "traces": [],
            "components": [],
            "items": {}
        }

    def get_file(self, id_: int) -> DatabaseFile:
        """ Get 'DatabaseFile for the given id. """
        return self.storage.files[id_]

    def get_other_files(self) -> List[DatabaseFile]:
        """ Get all the other files than currently selected. """
        other_files = []
        for id_, file in self.storage.files.items():
            if id_ != Settings.CURRENT_FILE_ID and file.totals == Settings.TOTALS:
                other_files.append(file)
        return other_files

    def store_file(self, file: ResultsFile) -> int:
        """ Store file in database. """
        try:
            return self.storage.store_file(file, totals=isinstance(file, TotalsFile))
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")

    def get_all_file_names(self) -> List[str]:
        """ Get all used file names. """
        return self.storage.get_all_file_names()

    def delete_file(self, id_: int) -> None:
        """ Delete file from the database. """
        try:
            self.storage.delete_file(id_)
        except KeyError:
            print(f"Cannot delete file: id '{id_}',"
                  f"\nFile was not found in the database.")

    def rename_file(self, id_: int, name: str):
        """ Rename given file. """
        try:
            self.storage.files[id_].rename(name)
        except KeyError:
            print(f"Cannot rename file: '{id_}',"
                  f"\nFile was not found in database.")

    def get_results(self, **kwargs) -> pd.DataFrame:
        """ Get output values for given variables. """
        if Settings.ALL_FILES:
            files = self.storage.files.values()
        else:
            files = self.storage.files[Settings.CURRENT_FILE_ID]

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

    def fetch_all_components(self):
        """ Get all components. """
        return self.wv_database["components"]

    def fetch_all_items(self):
        """ Get all items. """
        return self.wv_database["items"]

    def fetch_component(self, item_id: str) -> Union[Chart]:
        """ Get component of a given id. """
        for component in self.wv_database["components"]:
            if component.item_id == item_id:
                return component

    def remove_trace(self, trace_id: str) -> None:
        """ Remove trace from database. """
        trace = self.fetch_trace(trace_id)
        self.wv_database["traces"].remove(trace)

    def update_trace(self, trace: Union[Trace1D, Trace2D]) -> None:
        """ Replace trace with some other type trace. """
        self.remove_trace(trace.trace_id)
        self.wv_database["traces"].append(trace)

    def fetch_trace(self, trace_id: str) -> Union[Trace1D, Trace2D]:
        """ Get trace of a given id. """
        for trace in self.wv_database["traces"]:
            if trace.trace_id == trace_id:
                return trace

    def fetch_trace_data(self, trace_data_id: str) -> TraceData:
        """ Get trace of a given id. """
        for trace_data in self.wv_database["traces"]:
            if trace_data.trace_data_id == trace_data_id:
                return trace_data

    def fetch_traces(self, item_id: str) -> List[Union[Trace1D, Trace2D]]:
        """ Get traces assigned for a given item. """
        traces = []
        for trace in self.wv_database["traces"]:
            if trace.item_id == item_id:
                traces.append(trace)

        return traces

    def fetch_traces_data(self, item_id: str) -> List[TraceData]:
        """ Get traces assigned for a given item. """
        trace_data = []
        for trace_dt in self.wv_database["trace_data"]:
            if trace_dt.item_id == item_id:
                trace_data.append(trace_data)

        return trace_data

    def fetch_all_item_ids(self) -> List[str]:
        """ Get all used item ids. """
        return list(self.wv_database["items"].keys())
