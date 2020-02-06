import traceback
from multiprocessing import cpu_count

import loky
import psutil
from esofile_reader import EsoFile, TotalsFile
from esofile_reader.base_file import IncompleteFile


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


def load_file(path, monitor=None):
    """ Process eso file. """
    try:
        files = EsoFile.process_multi_env_file(path, monitor=monitor)
        t_files = [TotalsFile(f) for f in files]
        monitor.building_totals_finished()
        return files, t_files
    except IncompleteFile:
        monitor.processing_failed(f"Processing failed - incomplete file!"
                                  f"\n{traceback.format_exc()}")
    except Exception:
        monitor.processing_failed(traceback.format_exc())


def wait_for_results(id_, queue, future):
    """ Put loaded file into the queue and clean up the pool. """
    try:
        res = future.result()
        if res:
            files, totals_files = res
            queue.put((id_, files, totals_files))

    except BrokenPipeError:
        print("The application is being closed - "
              "catching broken pipe.")

    except loky.process_executor.BrokenProcessPool:
        print("The application is being closed - "
              "catching broken process pool executor.")
