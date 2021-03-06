import os
import shutil
from multiprocessing import Manager
from pathlib import Path
from typing import List, Optional

from PySide2.QtCore import QThreadPool
from esofile_reader.pqt.parquet_file import ParquetFile

from chartify.controller.file_processing import load_file
from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.settings import Settings
from chartify.ui.main_window import MainWindow
from chartify.ui.widgets.treeview_model import ViewModel, VV
from chartify.controller.process_utils import create_pool, kill_child_processes
from chartify.controller.progress_logging import ProgressThread, UiLogger
from chartify.controller.threads import FileWatcher, suspend_watcher
from chartify.utils.utils import get_str_identifier


class AppController:
    """
    Controller class to connect application
    view with application model.

    All background threads and processes are controlled
    in this class.

    Attributes & Parameters
    -----------------------
    v : MainWindow
        A main application view.
    m : AppModel
        An access to the application database.
    wvc : WebViewController
        A link to the application web controller.

    """

    def __init__(self, model: AppModel, view: MainWindow, wv_controller: WVController):
        self.v = view
        self.m = model
        self.wvc = wv_controller

        # ~~~~ Queues ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.manager = Manager()
        self.lock = self.manager.Lock()
        self.ids = self.manager.list([])
        self.progress_queue = self.manager.Queue()
        self.file_queue = self.manager.Queue()

        # ~~~~ Monitoring threads ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.watcher = FileWatcher(self.file_queue)
        self.watcher.file_loaded.connect(self.on_file_loaded)
        self.watcher.start()

        self.progress_thread = ProgressThread(self.progress_queue)
        self.progress_thread.start()

        # ~~~~ Thread executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.thread_pool = QThreadPool()

        # ~~~~ Process executor ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.pool = create_pool()

        # ~~~~ Connect signals ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.connect_view_signals()
        self.connect_progress_signals()

    def tear_down(self) -> None:
        """ Clean up application resources. """
        shutil.rmtree(Settings.APP_TEMP_DIR, ignore_errors=True)

        self.watcher.terminate()
        self.progress_thread.terminate()
        self.manager.shutdown()

        kill_child_processes(os.getpid())

        self.v._CLOSE_FLAG = True
        self.v.close()

    def connect_view_signals(self) -> None:
        """ Connect view signals. """
        self.v.paletteUpdated.connect(self.wvc.refresh_layout)
        self.v.selectionChanged.connect(self.on_selection_change)
        self.v.fileProcessingRequested.connect(self.on_file_processing_requested)
        self.v.syncFileProcessingRequested.connect(self.on_sync_file_processing_requested)
        self.v.fileRenameRequested.connect(self.on_file_rename_requested)
        self.v.variableRenameRequested.connect(self.on_variable_rename_requested)
        self.v.variableRemoveRequested.connect(self.on_variable_remove_requested)
        self.v.aggregationRequested.connect(self.on_aggregation_requested)
        self.v.fileRemoveRequested.connect(self.on_file_remove_requested)
        self.v.appCloseRequested.connect(self.tear_down)
        self.v.close_all_act.triggered.connect(lambda x: print("IMPLEMENT"))
        self.v.save_act.triggered.connect(self.on_save)
        self.v.save_as_act.triggered.connect(self.on_save_as)

    def connect_progress_signals(self) -> None:
        """ Create progress_thread signals. """
        self.progress_thread.file_added.connect(self.v.progress_container.add_file)
        self.progress_thread.progress_updated.connect(self.v.progress_container.update_progress)
        self.progress_thread.range_changed.connect(self.v.progress_container.set_range)
        self.progress_thread.pending.connect(self.v.progress_container.set_pending)
        self.progress_thread.failed.connect(self.v.progress_container.set_failed)
        self.progress_thread.status_changed.connect(self.v.progress_container.set_status)
        self.progress_thread.done.connect(self.v.progress_container.remove_file)

    def on_selection_change(self, view_variables: List[VV]) -> None:
        """ Handle selection update. """
        out_str = [" | ".join([v for v in var if v is not None]) for var in view_variables]
        if out_str:
            print("Selected Variables:\n\t{}".format("\n\t".join(out_str)))

    def save_project(self, path: Path) -> None:
        with suspend_watcher(self, self.watcher):
            logger = UiLogger(path.stem, path, self.progress_queue)
            with logger.log_task(f"save file {path.stem}"):
                self.m.save_to_zip(path, logger)

    def on_save(self) -> None:
        if not self.m.storage.path:
            self.on_save_as()
        else:
            self.save_project(self.m.path)

    def on_save_as(self) -> None:
        path = self.v.save_storage_to_fs()
        if path:
            self.m.path = path
            self.save_project(path)

    def on_file_processing_requested(self, paths: List[Path]) -> None:
        """ Load new files. """
        for path in paths:
            self.pool.submit(
                load_file,
                path,
                self.m.workdir,
                self.progress_queue,
                self.file_queue,
                self.ids,
                self.lock,
            )

    def on_sync_file_processing_requested(self, paths: List[Path]) -> None:
        """ Load new files. """
        for path in paths:
            load_file(
                path, self.m.workdir, self.progress_queue, self.file_queue, self.ids, self.lock,
            )

    def on_file_loaded(self, file: ParquetFile) -> None:
        """ Add results file into 'tab' widget. """
        names = self.m.get_all_file_names()
        name = get_str_identifier(file.file_name, names)
        file.rename(name)
        self.m.storage.files[file.id_] = file
        self.v.add_file_widget(file)

    def on_file_rename_requested(self, id_: int, name: str) -> None:
        """ Update file name. """
        self.m.rename_file(id_, name)

    def on_file_remove_requested(self, id_: int) -> None:
        """ Delete file from the database. """
        with self.lock:
            self.m.delete_file(id_)
            self.ids.remove(id_)

    def on_variable_rename_requested(
        self, models: List[ViewModel], old_view_variable: VV, new_view_variable: VV,
    ) -> None:
        for model in models:
            model.update_variable_if_exists(old_view_variable, new_view_variable)

    def on_variable_remove_requested(
        self, models: List[ViewModel], view_variables: List[VV],
    ):
        for model in models:
            model.delete_variables(view_variables)

    def on_aggregation_requested(
        self,
        models: List[ViewModel],
        func: str,
        view_variables: List[VV],
        new_key: str,
        new_type: Optional[str],
    ):
        for model in models:
            model.aggregate_variables(view_variables, func, new_key, new_type)
