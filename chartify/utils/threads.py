from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader.storage.storage_files import ParquetFile


# noinspection PyUnresolvedReferences
class Monitor(QThread):
    file_added = Signal(str, str, str)
    status_changed = Signal(str, str)
    progress_updated = Signal(str, int)
    pending = Signal(str, str)
    range_changed = Signal(str, int, int, str)
    failed = Signal(str, str)
    done = Signal(str)

    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue

    def run(self):
        while True:
            monitor, identifier, message = self.progress_queue.get()

            def do_not_report():
                pass

            def send_new_file():
                self.file_added.emit(monitor.id, monitor.name, monitor.path)

            def send_range():
                self.range_changed.emit(
                    monitor.id, monitor.progress, monitor.max_progress, message
                )

            def send_pending():
                self.pending.emit(monitor.id, message)

            def send_update_bar():
                self.progress_updated.emit(monitor.id, message)

            def send_failed():
                self.failed.emit(monitor.id, message)

            def send_status():
                self.status_changed.emit(monitor.id, message)

            def send_done():
                self.done.emit(monitor.id)

            switch = {
                -1: send_failed,
                0: send_new_file,  # initialized!
                1: send_status,  # pre-processing!
                2: send_range,  # processing data dictionary!
                3: send_status,  # processing data!
                4: send_status,  # processing intervals!
                5: send_status,  # generating search tree!
                6: do_not_report,  # skipping peak tables!
                7: send_status,  # generating tables!
                8: send_pending,  # processing finished!
                9: send_range,  # writing parquets!
                10: send_status,  # parquets written!
                50: send_status,  # generating totals!
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
