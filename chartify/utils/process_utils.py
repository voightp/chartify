import math
import traceback
import uuid
from multiprocessing import Lock
from multiprocessing import cpu_count
from typing import Tuple, List

import loky
import psutil
from esofile_reader import EsoFile, TotalsFile
from esofile_reader.base_file import IncompleteFile
from esofile_reader.data.pqt_data import ParquetFrame
from esofile_reader.storage.storage_files import ParquetFile
from esofile_reader.utils.mini_classes import ResultsFile

from chartify.utils.monitor import GuiMonitor


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
    results_file: ResultsFile, workdir: str, monitor: GuiMonitor, ids: List[int], lock: Lock
) -> Tuple[int, ParquetFile]:
    """ Store results file as 'ParquetFile'. """
    n_steps = 0
    for tbl in results_file.data.tables.values():
        n = int(math.ceil(tbl.shape[1] / ParquetFrame.CHUNK_SIZE))
        n_steps += n

    monitor.reset_progress(new_max=n_steps)
    monitor.storing_started()

    with lock:
        i = 0
        while i in ids:
            i += 1
        ids.append(i)

    id_ = i

    file = ParquetFile(
        id_=id_,
        file_path=results_file.file_path,
        file_name=results_file.file_name,
        data=results_file.data,
        file_created=results_file.file_created,
        search_tree=results_file.search_tree,
        type_=results_file.__class__.__name__,
        pardir=workdir,
        monitor=monitor,
    )
    file.CLEAN_UP = False

    monitor.storing_finished()

    return id_, file


def load_file(
    path: str, workdir: str, progress_queue, file_queue, ids: List[int], lock: Lock
) -> None:
    """ Process and store eso file. """
    monitor_id = str(uuid.uuid1())
    monitor = GuiMonitor(path, monitor_id, progress_queue)

    try:
        files = EsoFile.process_multi_env_file(path, monitor=monitor)
        monitor.building_totals_finished()

        for f in files:
            id_, file = store_file(
                results_file=f, workdir=workdir, monitor=monitor, ids=ids, lock=lock
            )
            file_queue.put(file)

            id_, file = store_file(
                results_file=TotalsFile(f), workdir=workdir, monitor=monitor, ids=ids, lock=lock
            )

            file_queue.put(file)

        file_queue.put(monitor_id)
        monitor.done()

    except IncompleteFile:
        monitor.processing_failed(
            f"Processing failed - incomplete file!" f"\n{traceback.format_exc()}"
        )
