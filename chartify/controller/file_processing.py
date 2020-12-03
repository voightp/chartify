import contextlib
import traceback
import uuid
from multiprocessing import Lock
from pathlib import Path
from typing import List, Tuple

from esofile_reader.exceptions import NoResults
from esofile_reader import GenericFile
from esofile_reader.exceptions import IncompleteFile, BlankLineError, InvalidLineSyntax
from esofile_reader.pqt.parquet_file import ParquetFile, ParquetFrame

from chartify.utils.progress_logging import UiLogger


def store_file(
    results_file: GenericFile, workdir: Path, logger: UiLogger, ids: List[int], lock: Lock,
) -> Tuple[int, ParquetFile]:
    """ Store results file as 'ParquetFile'. """
    ParquetFrame.MAX_N_COLUMNS = 2000
    with logger.log_task(f"Store file {results_file.file_name}"):
        logger.log_section("calculating number of parquets")
        n = ParquetFile.predict_number_of_parquets(results_file)
        logger.set_maximum_progress(n)
        with lock:
            id_ = 1
            while id_ in ids:
                id_ += 1
            ids.append(id_)
        logger.log_section("writing parquets")
        file = ParquetFile.from_results_file(id_, results_file, pardir=workdir, logger=logger)
    return id_, file


def load_file(
    path: Path, workdir: Path, progress_queue, file_queue, ids: List[int], lock: Lock
) -> None:
    """ Process and store eso file. """
    logger_id = str(uuid.uuid1())
    logger = UiLogger(path.name, path, logger_id, progress_queue)
    try:
        with contextlib.suppress(IncompleteFile, BlankLineError, InvalidLineSyntax):
            # progress_thread.failed is called in processing function so suppressed
            # functions do not need to be dealt with explicitly
            suffix = path.suffix
            if suffix == ".eso" or ".sql":
                files = GenericFile.from_eplus_multienv_file(path, logger=logger)
            elif suffix == ".xlsx" or ".csv":
                files = GenericFile.from_excel(path, logger=logger)
            else:
                logger.log_task_failed(
                    f"Cannot process file '{path}'. Unexpected file type: {suffix}!"
                )

            for f in files if isinstance(files, list) else [files]:
                id1, file1 = store_file(
                    results_file=f, workdir=workdir, logger=logger, ids=ids, lock=lock
                )
                try:
                    totals_file = GenericFile.from_totals(file1, logger=logger)
                    id2, file2 = store_file(
                        results_file=totals_file,
                        workdir=workdir,
                        logger=logger,
                        ids=ids,
                        lock=lock,
                    )
                    # assign new buddy attribute to link totals with original file
                    file2.buddy = file1
                    file1.buddy = file2
                except NoResults:
                    file2 = None
                    file1.buddy = None
                file_queue.put((file1, file2))
            file_queue.put(logger_id)
            logger.done()

    except Exception:
        # catch any unexpected generic exception
        logger.log_task_failed(traceback.format_exc())
