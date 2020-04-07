from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader.storage.storage_files import ParquetFile


# noinspection PyUnresolvedReferences
class Monitor(QThread):
    progress_updated = Signal(str, int)
    status_updated = Signal(str, str)
    pending = Signal(str)
    range_changed = Signal(str, int, int)
    started = Signal(str, str)
    file_added = Signal(str, str, str)
    failed = Signal(str, str)
    locked = Signal(str)
    done = Signal(str)

    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue



    def run(self):
        while True:
            monitor, identifier, message = self.progress_queue.get()

            def do_not_report():
                pass

            def initialized():
                self.file_added.emit(id_, label, file_path)

            def send_set_range(self, id_: str, progress: int, max_progress: int):
                self.range_changed.emit(id_, progress, max_progress)

            def send_pending(self, id_: str):
                self.pending.emit(id_)

            def send_update_bar(self, id_: str, message: str):
                self.progress_updated.emit(id_, message)

            def send_done(self, id_: str):
                self.done.emit(id_)

            def send_failed(self, id_: str, message: str):
                self.failed.emit(id_, message)

            def send_status_updated(self, id_: str, status: str):
                self.status_updated.emit(id_, status)

            switch = {
                -1: send_failed,
                0: initialized,  # initialized!
                1: do_not_report,  # pre-processing!
                2: send_set_range,  # processing data dictionary!
                3: do_not_report,  # processing data!
                4: do_not_report,  # processing intervals!
                5: do_not_report,  # generating search tree!
                6: do_not_report,  # skipping peak tables!
                7: do_not_report,  # generating tables!
                8: send_pending,  # processing finished!
                9: send_set_range,  # writing parquets!
                10: do_not_report,  # parquets written!
                50: do_not_report,  # generating totals!
                99: send_update_bar,
                100: send_done,
            }

            switch[identifier]()


# noinspection PyUnresolvedReferences
class EsoFileWatcher(QThread):
    file_loaded = Signal(ParquetFile)
    all_loaded = Signal(str)

    def __init__(self, file_queue):
        super().__init__()
        self.file_queue = file_queue

    def run(self):
        while True:
            file = self.file_queue.get()

            if isinstance(file, str):
                # passed monitor id, send close request
                self.all_loaded.emit(file)
            else:
                self.file_loaded.emit(file)


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
