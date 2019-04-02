from collections import defaultdict


class EsoFileHeader:
    """
    A class to handle the header data so it can be supplied
    into the 'MyModel' class.

    The 'header_view' method is used to manipulate the data
    based on specified 'sorting key'.

    A 'sorting key' can be either 'None', 'key', 'variable'
    or 'units'

    Parameters
    ----------
    header_dct : dct
        A dictionary header of the processed 'Eso file'.

    """

    def __init__(self, header_dct):
        self._header_dct = header_dct

    @property
    def available_intervals(self):
        """ Return a list of available intervals. """
        return self._header_dct.keys()

    def header_view(self, tree_arrange_key=None, interval_request=None):
        """ Create tree with categorized values. """
        dct = self._filtered_header_no_ids(request=interval_request)
        if not tree_arrange_key:
            return dct

        else:
            idnt = ["key", "var", "units"]
            idnt.remove(tree_arrange_key)
            vis_dct = defaultdict(list)
            for data in dct:
                key = data.__getattribute__(tree_arrange_key)
                vis_dct[key].append(data)
            return vis_dct

    def _header_no_ids(self):
        """ Return a header dictionary with header info as keys and intervals as values. """
        new_dct = defaultdict(list)
        for interval, value in self._header_dct.items():
            for id, v in value.items():
                new_dct[v].append(interval)
        return new_dct

    def _filtered_header_no_ids(self, request=None):
        """ Filter header dictionary and return dict with only applicable items. """
        if not request:
            return self._header_no_ids()
        else:
            if not isinstance(request, list):
                request = [request]
            request = set(self.available_intervals).intersection(set(request))

        filtered_header_dct = {}

        for key, value in self._header_no_ids().items():
            if all(map(lambda x: x in value, request)):
                filtered_header_dct[key] = value

        return filtered_header_dct
