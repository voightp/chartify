from chartify.settings import Settings
from chartify.view.css_theme import parse_palette


class AppModel:
    """
    A class which holds and provides access to the
    application database.

    The database is being held in memory as it works
    as a standard python  dictionary at the moment.

    """

    def __init__(self):
        # ~~~~ File Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.database = {}

        # ~~~~ Webview Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.traces = {}
        self.components = {}
        self.items = {}

        # ~~~~ Palettes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.palettes = parse_palette(Settings.PALETTE_PATH)

    def store_grid_layout(self, layout):
        """ Store current grid layout. """
        self.items = layout

    def add_trace(self, trace_id, trace):
        """ Add trace into database. """
        self.traces[trace_id] = trace

    def fetch_all_trace_ids(self):
        """ Get all used trace ids. """
        return list(self.traces.keys())

    def fetch_all_item_ids(self):
        """ Get all used item ids. """
        return list(self.items.keys())

    def fetch_traces(self, item_id):
        """ Get traces assigned for a given chart. """
        traces = []
        for trace in self.traces.values():
            if trace.item_id == item_id:
                traces.append(trace)

        return traces

    def fetch_component(self, item_id):
        """ Get displayed object from the database."""
        try:
            return self.components[item_id]
        except KeyError:
            raise KeyError(f"Cannot find component '{item_id}'.")

    def fetch_palette(self, name):
        """ Get 'Palette' object with a specified name. """
        try:
            return self.palettes[name]
        except KeyError:
            raise KeyError(f"Cannot find palette '{name}'.")

    def fetch_file(self, id_):
        """ Fetch a single file from the database. """
        id_ = f"t{id_}" if Settings.TOTALS else f"s{id_}"
        try:
            return self.database[id_]
        except KeyError:
            raise KeyError(f"Cannot find file {id_} in database!")

    def fetch_files(self, *args):
        """ Fetch multiple files from the database. """
        files = []
        for id_ in args:
            f = self.fetch_file(id_)
            if f:
                files.append(f)
        return files

    def fetch_all_files(self):
        """ Fetch all files from the database. """
        files = []
        for id_ in self.get_all_set_ids():
            f = self.fetch_file(id_)
            if f:
                files.append(f)
        return files

    def fetch_file_header_variables(self, id_, interval):
        """ Fetch a file header variables for a given interval. """
        file = self.fetch_file(id_)
        if file:
            return list(file.header_dct[interval].values())

    def get_all_file_ids(self):
        """ Return all file ids for a current state. """
        ids = []
        for id_ in self.database.keys():
            if id_.startswith("t" if Settings.TOTALS else "s"):
                ids.append(id_)
        return ids

    def get_all_set_ids(self):
        """ Get a list of already used ids (without s,t identifier). """
        return [id_[1:] for id_ in self.get_all_file_ids()]

    def get_all_file_names(self):
        """ Get all used file names. """
        return [f.file_name for f in self.database.values()]

    def delete_file(self, id_):
        """ Delete file from the database. """
        try:
            print(f"Deleting file id: '{id_}' from the database.")
            del self.database[id_]
        except KeyError:
            print(f"Cannot delete set: id '{id_}',"
                  f"\nFile was not found in the database.")

    def delete_sets(self, *args):
        """ Delete specified sets from the database. """
        for id_ in args:
            self.delete_file(f"s{id_}")
            self.delete_file(f"t{id_}")

    def rename_file(self, id_, name):
        """ Rename file in the databases. """
        try:
            file = self.fetch_file(id_)
            file.rename(name)
        except KeyError:
            print(f"Cannot rename file: id '{id_}',"
                  f"\nFile was not found in database.")

    def rename_set(self, id_, name, totals_name):
        """ Rename a file set in the database. """
        self.rename_file(self.fetch_file(f"s{id_}"), name)
        self.rename_file(self.fetch_file(f"s{id_}"), totals_name)

    def add_file(self, id_, file):
        """ Add processed results file to the database. """
        try:
            self.database[id_] = file
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")
