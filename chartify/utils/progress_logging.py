from contextlib import contextmanager
from multiprocessing import Queue
from pathlib import Path
from typing import Union
from uuid import uuid1

from PySide2.QtCore import QThread, Signal
from esofile_reader.processing.progress_logger import BaseLogger, INFO

ERROR = -1
NEW_FILE = 0
DONE = 1
INCREMENT = 2
SET_MAX = 3
UPDATE_TEXT = 4
SET_PENDING = 5


class UiLogger(BaseLogger):
    def __init__(self, name: str, path: Path, progress_queue: Queue):
        super().__init__(name, level=INFO)
        self.path = path
        self.logger_id = str(uuid1())
        self.progress_queue = progress_queue
        self._put_to_queue(NEW_FILE, name, path)

    def _put_to_queue(self, identifier: int, *args):
        self.progress_queue.put((self.logger_id, identifier, args))

    def log_message(self, message: str, level: int) -> None:
        self._put_to_queue(UPDATE_TEXT, message)

    def increment_progress(self, i: Union[int, float] = 1) -> None:
        self.progress += i
        self._put_to_queue(INCREMENT, self.progress)

    def set_maximum_progress(self, max_progress: int, progress: int = 0):
        self.max_progress = max_progress
        self.progress = progress
        self._put_to_queue(SET_MAX, self.progress, self.max_progress)

    def log_task_finished(self) -> None:
        self._put_to_queue(SET_PENDING)

    def log_task_failed(self, message: str) -> None:
        self._put_to_queue(ERROR, message)

    @contextmanager
    def log_task(self, task_name: str) -> None:
        self.current_task_name = task_name
        self.log_message(f"Task: '{task_name}' started!", level=INFO)
        try:
            yield
            self.log_task_finished()
        except Exception as e:
            self.log_task_failed(e.args[0])
            raise e

    def done(self):
        self._put_to_queue(DONE)


class ProgressThread(QThread):
    file_added = Signal(str, str, Path)
    status_changed = Signal(str, str)
    progress_updated = Signal(str, int)
    pending = Signal(str)
    range_changed = Signal(str, int, int)
    failed = Signal(str, str)
    done = Signal(str)

    def __init__(self, progress_queue: Queue):
        super().__init__()
        self.progress_queue = progress_queue

    def run(self):
        while True:
            logger_id, identifier, args = self.progress_queue.get()
            switch = {
                ERROR: self.failed,
                NEW_FILE: self.file_added,
                DONE: self.done,
                INCREMENT: self.progress_updated,
                SET_MAX: self.range_changed,
                UPDATE_TEXT: self.status_changed,
                SET_PENDING: self.pending,
            }
            switch[identifier].emit(logger_id, *args)
