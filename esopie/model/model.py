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
        """ Fetch eso files from the database. """
        files = []
        for id_ in args:
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

    def get_all_names_from_db(self):
        """ Get all file names. """
        return [f.file_name for f in self.database.values()]

    def delete_sets_from_db(self, *args):
        """ Delete the eso file from the database. """
        for id_ in args:
            try:
                print(f"Deleting file id: '{id_}' from database.")
                del self.database[id_]
            except KeyError:
                print(f"Cannot delete eso file: id '{id_}',"
                      f"\nFile was not found in database.")

    def rename_file_in_db(self, id_, f_name, totals_f_name):
        """ Rename file in the databases. """
        try:
            f_set = self.database[id_]
            f_set[f"s{id_}"].rename(f_name)
            f_set[f"t{id_}"].rename(totals_f_name)
        except KeyError:
            print(f"Cannot rename eso file: id '{id_}',"
                  f"\nFile was not found in database.")

    def add_file_to_db(self, id_, file):
        """ Add processed eso file to the database. """
        try:
            self.database[id_] = file
        except BrokenPipeError:
            print("Application has been closed - catching broken pipe!")
