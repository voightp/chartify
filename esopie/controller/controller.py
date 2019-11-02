from functools import partial
from esopie.settings import Settings
from esopie.view.view_functions import create_proxy


class AppController:
    def __init__(self, model, view):
        self.v = view
        self.m = model

    def connect_view_signals(self):
        # self.v.selectionUpdated
        self.v.settingsChanged.connect()
        self.v.paletteChanged.connect()
        self.v.fileProcessingRequested.connect()
        self.v.fileRenamed.connect()
        self.v.variableRenamed.connect()
        self.v.tabChanged.connect(self.handle_tab_change)
        self.v.tabClosed.connect()

        self.v.close_all_act.triggered.connect(self.close_all_tabs)
        self.v.hide_act.triggered.connect(self.hide_vars)
        self.v.remove_hidden_act.triggered.connect(self.remove_hidden_vars)
        self.v.show_hidden_act.triggered.connect(self.show_hidden_vars)

        self.v.sum_act.triggered.connect(partial(self.add_var, "sum"))
        self.v.mean_act.triggered.connect(partial(self.add_var, "mean"))
        self.v.save_act.triggered.connect(lambda x: print("SAVE ACT!"))
        self.v.save_as_act.triggered.connect(lambda x: print("SAVE AS ACT!"))
        self.v.remove_act.triggered.connect(lambda x: x)

        self.v.tabChanged.connect()
        self.v.fileProcessingRequested()
        self.v.settingsChanged.connect(lambda x: x)

    def connect_model_signals(self):
        """ Create monitor actions. """
        self.m.fileLoaded.connect(self.m.add_new_tab)

        self.m.monitor.initialized.connect(self.v.add_new_tab)
        self.m.monitor.started.connect(self.v.update_progress_text)
        self.m.monitor.text_updated.connect(self.v.update_progress_text)
        self.m.monitor.bar_updated.connect(self.v.update_file_progress)
        self.m.monitor.preprocess_finished.connect(self.v.set_max_value)
        self.m.monitor.finished.connect(self.v.remove_file)
        self.m.monitor.failed.connect(self.v.set_failed)

    def handle_tab_change(self, id_, view_order):
        """ Update content of a newly selected tab. """
        file = self.m.fetch_file(id_)

        # update interface to enable only available interval buttons
        # and rate to energy button when applicable
        self.v.toolbar.update_intervals_state(file.available_intervals)
        self.v.toolbar.update_rate_to_energy_state()

        interval = Settings.INTERVAL
        units = (Settings.RATE_TO_ENERGY, Settings.UNITS_SYSTEM,
                 Settings.ENERGY_UNITS, Settings.POWER_UNITS)
        variables = list(file.header_dct[interval].values())
        proxy = create_proxy(variables, view_order, *units)

        self.v.build_view(variables, proxy, interval, units)

        def handle_view_update(self):
            pass

        def handle_settings_change(self):
            pass

        def handle_variable_rename(self):
            if res:
                var = self.apply_async(self.rename_var, var_nm,
                                       key_nm, variable)
                self.selected = [var]
                self.current_view.scroll_to(var)

        def handle_file_rename(self):
            pass
