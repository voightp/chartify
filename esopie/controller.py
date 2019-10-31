from functools import partial


class AppController:
    def __init__(self, model, view):
        self.v = view
        self.m = model

    def connect_view_signals(self):
        self.v.self.selection_updated.connect()
        self.v.all_tabs_closed.connect()

        self.v.load_file_act.triggered.connect(self.load_files_from_os)
        self.v.close_all_act.triggered.connect(self.close_all_tabs)
        self.v.remove_act.triggered.connect(self.remove_vars)
        self.v.hide_act.triggered.connect(self.hide_vars)
        self.v.remove_hidden_act.triggered.connect(self.remove_hidden_vars)
        self.v.show_hidden_act.triggered.connect(self.show_hidden_vars)
        self.v.sum_act.triggered.connect(partial(self.add_var, "sum"))
        self.v.mean_act.triggered.connect(partial(self.add_var, "mean"))
        self.v.tree_act.triggered.connect(self.view_tools_wgt.tree_view_btn.toggle)
        self.v.save_act.triggered.connect(lambda x: print("SAVE ACT!"))
        self.v.save_as_act.triggered.connect(lambda x: print("SAVE AS ACT!"))

    def connect_model_signals(self):
        """ Create monitor actions. """
        self.m.on_file_loaded.connect(self.m.add_new_file)

        self.m.monitor.initialized.connect(self.v.add_new_file)
        self.m.monitor.started.connect(self.v.update_progress_text)
        self.m.monitor.text_updated.connect(self.v.update_progress_text)
        self.m.monitor.bar_updated.connect(self.v.update_file_progress)
        self.m.monitor.preprocess_finished.connect(self.v.set_max_value)
        self.m.monitor.finished.connect(self.v.remove_file)
        self.m.monitor.failed.connect(self.v.set_failed)
