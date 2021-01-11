from pathlib import Path
from typing import List, Union
from zipfile import ZipFile

from PySide2.QtCore import QObject
from esofile_reader.pqt.parquet_file import ParquetFile
from esofile_reader.pqt.parquet_storage import ParquetStorage

from chartify.charts.chart import Chart
from chartify.charts.trace import Trace1D, Trace2D, TraceData
from chartify.controller.file_processing import UiLogger
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
        self.storage = ParquetStorage(workdir=Path(Settings.APP_TEMP_DIR, "storage"))

        # ~~~~ WebView Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.wv_database = {"trace_data": [], "traces": [], "components": [], "items": {}}

        # ~~~~ Save Path ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.path = None

    @property
    def workdir(self):
        return self.storage.workdir

    def save_to_zip(self, path: Path, logger: UiLogger) -> None:
        with ZipFile(path, mode="w") as zf:
            self.m.save_to_zip()
            for pqf in self.m.files.values():
                pqf.save_file_to_zip(zf, self.workdir, logger)

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
        files = []
        for id_, file in self.storage.files.items():
            files.append(file)
        return files

    def store_file(self, file: ParquetFile) -> int:
        """ Store file in database. """
        try:
            return self.storage.store_file(file)
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")

    def get_file_name(self, id_: int) -> str:
        """ Get file name of given file. """
        return self.get_file(id_).file_name

    def get_all_file_names(self) -> List[str]:
        """ Get all used file names. """
        return [file.file_name for file in self.get_all_files()]

    def delete_file(self, id_: int) -> None:
        """ Delete file from the database. """
        self.storage.delete_file(id_)

    def rename_file(self, id_: int, name: str):
        """ Rename given file. """
        self.storage.files[id_].rename(name)

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
