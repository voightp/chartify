from PySide2.QtCore import QThread, Signal

from eso_reader.monitor import DefaultMonitor
from eso_reader.eso_file import EsoFile


# noinspection PyUnresolvedReferences
class MonitorThread(QThread):
    progress_bar_updated = Signal(int, int)
    progress_text_updated = Signal(int, str)
    finished = Signal(int)
    preprocess_finished = Signal(int, int)
    started = Signal(int, str)
    initialized = Signal(int, str)
    failed = Signal(int, str)

    def __init__(self, progress_queue):
        super().__init__()
        self.progress_queue = progress_queue

    def run(self):
        while True:
            monitor, identifier, message = self.progress_queue.get()
            mon_id, mon_name = monitor.id, monitor.name

            def send_initialized():
                self.initialized.emit(mon_id, mon_name)
                self.progress_text_updated.emit(mon_id, message)

            def send_started():
                self.started.emit(mon_id, mon_name)
                self.progress_text_updated.emit(mon_id, message)

            def send_finished():
                self.finished.emit(mon_id)

            def send_update_text():
                self.progress_text_updated.emit(mon_id, message)

            def preprocessing_finished():
                steps = monitor.n_steps
                self.preprocess_finished.emit(mon_id, steps)

            def send_update_progress_bar():
                self.progress_bar_updated.emit(mon_id, message)

            def do_not_report():
                pass

            def failed():
                self.progress_text_updated.emit(mon_id, "FAILED")

            switch = {
                "init": send_initialized,
                -1: failed,
                0: send_started,
                1: preprocessing_finished,
                2: send_update_text,
                3: do_not_report,
                4: send_update_text,
                5: do_not_report,
                6: send_update_text,
                7: do_not_report,
                8: send_update_text,
                9: do_not_report,
                10: send_update_text,
                11: do_not_report,
                12: send_finished,
                100: send_update_progress_bar,
            }

            switch[identifier]()


# noinspection PyUnresolvedReferences
class EsoFileWatcher(QThread):
    loaded = Signal(int, EsoFile)

    def __init__(self, file_queue):
        super().__init__()
        self.file_queue = file_queue

    def run(self):
        while True:
            id, eso_file = self.file_queue.get()
            self.loaded.emit(id, eso_file)


class PipeEcho(QThread):
    output_requested = Signal()

    def __init__(self, pipe):
        super().__init__()
        self.pipe = pipe

    def run(self):
        while True:
            message = self.pipe.recv()
            if message:
                print("Message '{}' received.".format(message))
                self.output_requested.emit()


class GuiMonitor(DefaultMonitor):
    def __init__(self, path, id, queue):
        super().__init__(path)
        self.queue = queue
        self.id = id
        self.send_message("init", "Waiting")

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
