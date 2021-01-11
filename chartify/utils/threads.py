from contextlib import contextmanager

from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader.pqt.parquet_file import ParquetFile


# noinspection PyUnresolvedReferences
class FileWatcher(QThread):
    file_loaded = Signal(ParquetFile)

    def __init__(self, file_queue):
        super().__init__()
        self.file_queue = file_queue

    def run(self):
        while True:
            file = self.file_queue.get()
            self.file_loaded.emit(file)


@contextmanager
def suspend_watcher(main_window, thread: FileWatcher) -> None:
    queue = thread.file_queue
    thread.quit()
    yield
    main_window.watcher = FileWatcher(queue)
    main_window.watcher.start()


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
