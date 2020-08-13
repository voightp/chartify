import contextlib
import math
import traceback
import uuid
from multiprocessing import Lock, cpu_count
from pathlib import Path
from typing import Tuple, List

import loky
import psutil
from esofile_reader import ResultsFile
from esofile_reader.base_file import IncompleteFile, BlankLineError, InvalidLineSyntax
from esofile_reader.storages.pqt_storage import ParquetFile
from esofile_reader.tables.pqt_tables import ParquetFrame

from chartify.utils.progress_monitor import ProgressMonitor


def create_pool():
    """ Create a new process pool. """
    n_cores = cpu_count()
    workers = (n_cores - 1) if n_cores > 1 else 1
    return loky.get_reusable_executor(max_workers=workers)


def kill_pool():
    """ Shutdown the process pool. """
    loky.get_reusable_executor().shutdown(wait=False, kill_workers=True)


def kill_child_processes(parent_pid):
    """ Terminate all running child processes. """
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for p in children:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            continue


def store_file(
    results_file: ResultsFile,
    workdir: str,
    monitor: ProgressMonitor,
    ids: List[int],
    lock: Lock,
) -> Tuple[int, ParquetFile]:
    """ Store results file as 'ParquetFile'. """
    n_steps = 0
    for tbl in results_file.tables.values():
        n = int(math.ceil(tbl.shape[1] / ParquetFrame.CHUNK_SIZE))
        n_steps += n

    monitor.reset_progress(new_max=n_steps)
    monitor.storing_started()

    with lock:
        id_ = 0
        while id_ in ids:
            id_ += 1
        ids.append(id_)

    file = ParquetFile.from_results_file(id_, results_file, pardir=workdir, monitor=monitor)
    monitor.storing_finished()

    return id_, file


def load_file(
    path: str, workdir: str, progress_queue, file_queue, ids: List[int], lock: Lock
) -> None:
    """ Process and store eso file. """
    monitor_id = str(uuid.uuid1())
    monitor = ProgressMonitor(path, monitor_id, progress_queue)
    try:
        with contextlib.suppress(IncompleteFile, BlankLineError, InvalidLineSyntax):
            # monitor.failed is called in processing function so suppressed
            # functions do not need to be dealt with explicitly
            suffix = Path(path).suffix
            if suffix == ".eso":
                files = ResultsFile.from_eso_file(path, monitor=monitor)
            elif suffix == ".xlsx":
                files = ResultsFile.from_excel(path)
            else:
                monitor.processing_failed(
                    f"Cannot process file '{path}'. Unexpected file type: {suffix}!"
                )

            for f in files if isinstance(files, list) else [files]:
                id1, file1 = store_file(
                    results_file=f, workdir=workdir, monitor=monitor, ids=ids, lock=lock
                )
                # generate and store totals file
                monitor.totals_started()
                totals_file = ResultsFile.from_totals(f)
                if totals_file:
                    id2, file2 = store_file(
                        results_file=totals_file,
                        workdir=workdir,
                        monitor=monitor,
                        ids=ids,
                        lock=lock,
                    )
                    # assign new buddy attribute to link totals with original file
                    file2.buddy = file1
                    file1.buddy = file2
                else:
                    file2 = None
                    file1.buddy = None

                file_queue.put((file1, file2))
            file_queue.put(monitor_id)
            monitor.done()

    except Exception:
        # catch any unexpected generic exception
        monitor.processing_failed(traceback.format_exc())
