import contextlib
import traceback
from multiprocessing import Lock
from pathlib import Path
from typing import List

from esofile_reader import GenericFile
from esofile_reader.exceptions import IncompleteFile, BlankLineError, InvalidLineSyntax
from esofile_reader.pqt.parquet_file import ParquetFile, ParquetFrame
from esofile_reader.typehints import ResultsFileType

from chartify.controller.progress_logging import UiLogger


def store_file(
    results_file: GenericFile, workdir: Path, logger: UiLogger, ids: List[int], lock: Lock,
) -> ParquetFile:
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
    return file


def load_file(
    path: Path, workdir: Path, progress_queue, file_queue, ids: List[int], lock: Lock
) -> None:
    """ Process and store given results file. """
    logger = UiLogger(path.name, path, progress_queue)
    try:
        with contextlib.suppress(IncompleteFile, BlankLineError, InvalidLineSyntax):
            # progress_thread.failed is called in processing function so suppressed
            # functions do not need to be dealt with explicitly
            suffix = path.suffix
            if suffix == ".eso" or suffix == ".sql":
                files = GenericFile.from_eplus_multienv_file(path, logger=logger)
            elif suffix == ".xlsx" or suffix == ".csv":
                files = GenericFile.from_excel(path, logger=logger)
            else:
                logger.log_task_failed(
                    f"Cannot process file '{path}'. Unexpected file type: {suffix}!"
                )

            for file in files if isinstance(files, list) else [files]:
                parquet_file = store_file(file, workdir, logger=logger, ids=ids, lock=lock)
                file_queue.put(parquet_file)
            logger.done()

    except Exception:
        # catch any unexpected generic exception
        logger.log_task_failed(traceback.format_exc())


def create_totals_file(
    file: ResultsFileType, workdir: Path, progress_queue, file_queue, ids: List[int], lock: Lock
):
    """ Generate and store totals file."""
    logger = UiLogger(file.name, file.file_path, progress_queue)
    totals_file = GenericFile.from_totals(file, logger=logger)
    parquet_file = store_file(totals_file, workdir, logger=logger, ids=ids, lock=lock)

    # assign new buddy attribute to link totals with original file
    file.buddy = parquet_file
    parquet_file.buddy = file
    file_queue.put(parquet_file)
    logger.done()
