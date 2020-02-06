from PySide2.QtCore import QThread, Signal, QRunnable
from esofile_reader import TotalsFile
from esofile_reader.eso_file import EsoFile
from esofile_reader.processing.monitor import DefaultMonitor


# noinspection PyUnresolvedReferences
class Monitor(QThread):
    bar_updated = Signal(str, int)
    finished = Signal(str)
    preprocess_finished = Signal(str, int)
    started = Signal(str, str)
    initialized = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue

    def run(self):
        while True:
            monitor, identifier, message = self.progress_queue.get()
            mon_id, mon_name = monitor.id, monitor.name

            def send_initialized():
                self.initialized.emit(mon_id, mon_name)

            def send_started():
                self.started.emit(mon_id, mon_name)

            def send_preprocessing_finished():
                self.preprocess_finished.emit(mon_id, monitor.n_steps)

            def send_finished():
                self.finished.emit(mon_id)

            def send_update_progress_bar():
                self.bar_updated.emit(mon_id, message)

            def do_not_report():
                pass

            def send_failed():
                self.failed.emit(mon_id, message)

            switch = {
                -1: send_failed,
                0: send_initialized,
                1: send_started,
                2: send_preprocessing_finished,
                3: do_not_report,  # header finished
                4: do_not_report,  # body finished
                5: do_not_report,  # intervals finished
                6: do_not_report,  # output cls finished
                7: do_not_report,  # tree finished
                8: do_not_report,  # file processing finished
                9: send_finished,  # building totals generated
                100: send_update_progress_bar,
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
    def __init__(self, path, id_, queue):
        super().__init__(path)
        self.queue = queue
        self.id = id_
        self.send_message(0, "Waiting")

    def building_totals_finished(self):
        self.send_message(9, "Totals produced!")

    def calculate_steps(self):
        chunk_size = 10000
        n_lines = self.results_lines
        n_steps = n_lines // chunk_size

        if n_steps < 10:
            self.chunk_size = n_lines // 10
            self.n_steps = 10

        else:
            self.chunk_size = chunk_size
            self.n_steps = n_steps

    def update_body_progress(self):
        self.results_lines_counter += 1
        if self.results_lines_counter == self.chunk_size:
            self.progress += 1
            self.report_progress(100, self.progress)
            self.results_lines_counter = 0

    def report_progress(self, identifier, text):
        self.record_time(identifier)
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
