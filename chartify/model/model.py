from typing import List, Union

import pandas as pd
from PySide2.QtCore import QObject
from esofile_reader import Variable
from esofile_reader import get_results
from esofile_reader.mini_classes import ResultsFile
from esofile_reader.storage.pqt_storage import ParquetStorage
from esofile_reader.storage.storage_files import ParquetFile

from chartify.charts.chart import Chart
from chartify.charts.trace import Trace1D, Trace2D, TraceData
from chartify.settings import Settings


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
        self.storage = ParquetStorage()

        # ~~~~ Currently selected variables ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.selected_variable_data = []

        # ~~~~ Webview Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.wv_database = {"trace_data": [], "traces": [], "components": [], "items": {}}

    @property
    def selected_variables(self) -> List[Variable]:
        variables = []
        for variable_data in self.selected_variable_data:
            variables.append(
                Variable(
                    interval=Settings.INTERVAL,
                    key=variable_data.key,
                    type=variable_data.type,
                    units=variable_data.units
                )
            )
        return variables

    def get_file(self, id_: int) -> ParquetFile:
        """ Get 'DatabaseFile for the given id. """
        return self.storage.files[id_]

    def get_other_files(self) -> List[ParquetFile]:
        """ Get all the other files than currently selected. """
        other_files = []
        for file in self.get_all_files():
            if file.id_ != Settings.CURRENT_FILE_ID:
                other_files.append(file)
        return other_files

    def get_all_files(self) -> List[ParquetFile]:
        """ Get all files of currently used type. """
        # TODO apply some filtering based on file type
        files = []
        for id_, file in self.storage.files.items():
            files.append(file)
        return files

    def store_file(self, file: ResultsFile) -> int:
        """ Store file in database. """
        try:
            return self.storage.store_file(file)
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")

    def get_file_name(self, id_: int) -> str:
        """ Get file name of given file. """
        file = self.get_file(id_)
        return file.file_name

    def get_other_file_names(self) -> List[str]:
        """ Get all used file names. """
        return [file.file_name for file in self.get_other_files()]

    def get_all_file_names(self) -> List[str]:
        """ Get all used file names. """
        return [file.file_name for file in self.get_all_files()]

    def delete_file(self, id_: int) -> None:
        """ Delete file from the database. """
        try:
            self.storage.delete_file(id_)
        except KeyError:
            print(f"Cannot delete file: id '{id_}'," f"\nFile was not found in the database.")

    def rename_file(self, id_: int, name: str):
        """ Rename given file. """
        self.storage.files[id_].rename(name)

    def get_results(self, **kwargs) -> pd.DataFrame:
        """ Get output values for given variables. """
        if Settings.ALL_FILES:
            files = self.storage.files.values()
        else:
            files = self.storage.files[Settings.CURRENT_FILE_ID]

        # transform variable data to variable (variable data holds extra proxy units)
        variables = [
            Variable(Settings.INTERVAL, v.key, v.type, v.units)
            for v in self.selected_variable_data
        ]

        args = (files, variables)
        kwargs = {
            "rate_units": Settings.POWER_UNITS,
            "energy_units": Settings.ENERGY_UNITS,
            "add_file_name": "column",
            "rate_to_energy_dct": {Settings.INTERVAL: Settings.RATE_TO_ENERGY},
            **kwargs,
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
