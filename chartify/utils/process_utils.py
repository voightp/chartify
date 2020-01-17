import loky
import psutil

from esofile_reader import EsoFile, TotalsFile
from esofile_reader.base_file import IncompleteFile
from multiprocessing import cpu_count


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


def load_file(path, monitor=None, suppress_errors=False):
    """ Process eso file. """
    try:
        std_file = EsoFile(path, monitor=monitor, suppress_errors=suppress_errors)
        tot_file = BuildingEsoFile(std_file)
        monitor.building_totals_finished()
        return std_file, tot_file
    except IncompleteFile:
        monitor.processing_failed("Processing failed - incomplete file!")
    except Exception:
        monitor.processing_failed("Processing failed!")


def wait_for_results(id_, queue, future):
    """ Put loaded file into the queue and clean up the pool. """
    try:
        res = future.result()
        if res:
            std_file, tot_file = res
            queue.put((id_, std_file, tot_file))

    except BrokenPipeError:
        print("The application is being closed - "
              "catching broken pipe.")

    except loky.process_executor.BrokenProcessPool:
        print("The application is being closed - "
              "catching broken process pool executor.")
