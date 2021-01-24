from PySide2.QtCore import QThread, Signal, QRunnable, QSemaphore
from esofile_reader.pqt.parquet_file import ParquetFile


class Semaphore(QSemaphore):
    def __init__(self, n: int = 1):
        super(Semaphore, self).__init__(n)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# noinspection PyUnresolvedReferences
class FileWatcher(QThread):
    file_loaded = Signal(ParquetFile)

    def __init__(self, file_queue, lock):
        super().__init__()
        self.file_queue = file_queue
        self.lock = lock

    def run(self):
        while True:
            file = self.file_queue.get()
            with self.lock:
                self.file_loaded.emit(file)


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
