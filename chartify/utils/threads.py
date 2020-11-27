from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader.pqt.parquet_file import ParquetFile

from chartify.ui.treeview import ViewModel


# noinspection PyUnresolvedReferences
class EsoFileWatcher(QThread):
    file_loaded = Signal(ParquetFile, dict)
    all_loaded = Signal(str)

    def __init__(self, file_queue):
        super().__init__()
        self.file_queue = file_queue

    def run(self):
        while True:
            files = self.file_queue.get()
            if isinstance(files, str):
                # passed progress_thread id, send close request
                self.all_loaded.emit(files)
            else:
                # create ModelViews outside main application loop
                # totals file may be 'None' so it needs to be skipped
                for file in list(filter(None, files)):
                    models = ViewModel.models_from_file(file)
                    self.file_loaded.emit(file, models)


class IterWorker(QRunnable):
    def __init__(self, func, lst, *args, **kwargs):
        super().__init__()
        self.func = func
        self.lst = lst
        self.args = args
        self.kwargs = kwargs

    def run(self):
        # TODO catch fetch exceptions, emit signal to handle results
        for i in self.lst:
            self.func(i, *self.args, **self.kwargs)


class Worker(QRunnable):
    def __init__(self, func, *args, callback=None, **kwargs):
        super().__init__()
        self.func = func
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def run(self):
        # TODO catch fetch exceptions, emit signal to handle results
        res = self.func(*self.args, **self.kwargs)

        if self.callback:
            self.callback(res)
