from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader import TotalsFile
from esofile_reader.eso_file import EsoFile
from esofile_reader.processor.monitor import DefaultMonitor


# noinspection PyUnresolvedReferences
class Monitor(QThread):
    bar_updated = Signal(str, int)
    pending = Signal(str)
    range_changed = Signal(str, int, int)
    started = Signal(str, str)
    file_added = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue

    def run(self):
        while True:
            monitor, identifier, message = self.progress_queue.get()
            mon_id, mon_name = monitor.id, monitor.name

            def send_new_file():
                self.file_added.emit(mon_id, mon_name)

            def send_set_range():
                self.range_changed.emit(mon_id, monitor.progress, monitor.max_progress)

            def send_pending():
                self.pending.emit(mon_id)

            def send_update_bar():
                self.bar_updated.emit(mon_id, message)

            def do_not_report():
                pass

            def send_failed():
                self.failed.emit(mon_id, message)

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
                8: do_not_report,  # file processing finished
                9: send_set_range,  # storing started
                10: do_not_report,  # storing finished
                11: do_not_report,  # building totals generated
                100: send_update_bar,
            }

            switch[identifier]()


# noinspection PyUnresolvedReferences
class EsoFileWatcher(QThread):
    loaded = Signal(str, EsoFile, TotalsFile)

    def __init__(self, file_queue):
        super().__init__()
        self.file_queue = file_queue

    def run(self):
        while True:
            id_, f, tf = self.file_queue.get()
            self.loaded.emit(id_, f, tf)


class GuiMonitor(DefaultMonitor):
    CHUNK_SIZE = 10000

    def __init__(self, path, id_, queue):
        super().__init__(path)
        self.queue = queue
        self.id = id_
        self.send_message(0, "Waiting")

    def processing_finished(self):
        self.report_progress(8, "Processing finished!")

    def building_totals_finished(self):
        self.send_message(9, "Totals produced!")

    def set_chunk_size(self, n_lines):
        n_processing_steps = n_lines // self.CHUNK_SIZE

        if n_processing_steps < 10:
            self.max_progress = 10
        else:
            self.max_progress = n_processing_steps // self.PROGRESS_FRACTION

        super().set_chunk_size(n_lines)

    def update_progress(self, i=1):
        self.progress += i
        self.send_message(100, self.progress)

    def report_progress(self, identifier, text):
        self.send_message(identifier, text)

    def send_message(self, identifier, text):
        try:
            self.queue.put((self, identifier, text))
        except EOFError as e:
            print("Cannot send message!\n{}".format(e))
        except FileNotFoundError as e:
            print("Cannot find file!\n{}".format(e))
        except BrokenPipeError:
            print("App is being closed, cannot send message!")


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
