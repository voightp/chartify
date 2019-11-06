from esopie.settings import Settings


class AppModel:
    def __init__(self):
        # ~~~~ Database ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.database = {}

    def fetch_file(self, id_):
        """ Fetch file from database. """
        id_ = f"t{id_}" if Settings.TOTALS else f"s{id_}"
        try:
            return self.database[id_]
        except KeyError:
            raise KeyError(f"Cannot find file {id_} in database!")

    def fetch_files(self, *args):
        """ Fetch results files from the database. """
        files = []
        for id_ in args:
            f = self.fetch_file(id_)
            if f:
                files.append(f)
        return files

    def fetch_all_files(self):
        """ Fetch eso files from the database. """
        files = []
        for id_ in self.get_all_set_ids():
            f = self.fetch_file(id_)
            if f:
                files.append(f)
        return files

    def fetch_file_header_variables(self, id_, interval):
        """ Fetch file header variables for a given interval. """
        file = self.fetch_file(id_)
        if file:
            return list(file.header_dct[interval].values())

    def get_all_file_ids(self):
        """ Return all file ids for given state. """
        ids = []
        for id_ in self.database.keys():
            if id_.startswith("t" if Settings.TOTALS else "s"):
                ids.append(id_)
        return ids

    def get_all_set_ids(self):
        """ Get a list of already used ids (without s,t identifier). """
        return [id_[1:] for id_ in self.get_all_file_ids()]

    def get_all_file_names(self):
        """ Get all file names. """
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
        """ Delete specified sets from the database. """
        self.rename_file(self.fetch_file(f"s{id_}"), name)
        self.rename_file(self.fetch_file(f"s{id_}"), totals_name)

    def add_file(self, id_, file):
        """ Add processed eso file to the database. """
        try:
            self.database[id_] = file
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")
