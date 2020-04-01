from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader.storage.storage_files import ParquetFile


# noinspection PyUnresolvedReferences
class Monitor(QThread):
    bar_updated = Signal(str, int)
    info_updated = Signal(str, str)
    pending = Signal(str)
    range_changed = Signal(str, int, int)
    started = Signal(str, str)
    file_added = Signal(str, str)
    failed = Signal(str, str)
    locked = Signal(str)
    done = Signal(str)

    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue

    def run(self):
        while True:
            monitor, identifier, message = self.progress_queue.get()

            def send_new_file():
                self.file_added.emit(monitor.id, monitor.name)

            def send_set_range():
                self.range_changed.emit(monitor.id, monitor.progress, monitor.max_progress)

            def send_pending():
                self.pending.emit(monitor.id)

            def send_update_bar():
                self.bar_updated.emit(monitor.id, message)

            def do_not_report():
                pass

            def send_failed():
                self.failed.emit(monitor.id, message)

            def send_done():
                self.done.emit(monitor.id)

            def send_update_info():
                print(message)

            switch = {
                -1: send_failed,
                0: send_new_file,
                1: do_not_report,  # processing started
                2: send_set_range,  # preprocessing finished
                3: do_not_report,  # header finished
                4: do_not_report,  # body finished
                5: do_not_report,  # intervals finished
                6: do_not_report,  # output cls finished
                7: do_not_report,  # tree finished
                8: send_pending,  # file processing finished
                9: send_set_range,  # storing started
                10: do_not_report,  # storing finished
                50: do_not_report,  # totals started
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
