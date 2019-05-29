from collections import defaultdict, namedtuple

ProxyHeaderVariable = namedtuple("ProxyHeaderVariable", "key variable units proxy_units")


class EsoFileHeader:
    """
    A class to handle the header data so it can be supplied
    into the 'ViewModel' class.

    The 'header_view' method is used to manipulate the data
    based on specified 'sorting key'.

    A 'sorting key' can be either 'raw', 'key', 'variable'
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

    def _header_no_ids(self):
        """ Return a header dictionary with header info as keys and intervals as values. """
        new_dct = defaultdict(list)

        for interval, value in self._header_dct.items():
            # loop only through values as id (key) is omitted
            for v in value.values():
                new_dct[v].append(interval)

        return new_dct

    def _filtered_header_no_ids(self, intervals=None):
        """ Filter header dictionary and return dict with applicable items. """
        if not intervals:
            return self._header_no_ids()

        if not isinstance(intervals, list):
            intervals = [intervals]
            intervals = set(self.available_intervals).intersection(set(intervals))

        filtered_header_dct = {}

        for key, value in self._header_no_ids().items():
            if all(map(lambda x: x in value, intervals)):
                filtered_header_dct[key] = value

        return filtered_header_dct

    def _assign_proxy_units(self, dct, units_settings):
        """ Add selected settings to the header dictionary. """
        energy_dct, units_system, energy_units, power_units = units_settings
        pass

    def proxy_header(self, units_settings, group_by_key, interval_request):
        """ Create tree with categorized values. """
        dct = self._filtered_header_no_ids(intervals=interval_request)

        if group_by_key == "raw":
            return dct

        else:
            idnt = ["key", "variable", "units"]
            idnt.remove(group_by_key)
            vis_dct = defaultdict(list)

            for pieces in dct:
                key = pieces.__getattribute__(group_by_key)
                vis_dct[key].append(pieces)

            return vis_dct

        is_energy = energy_rate_dct[interval]
        if is_energy:
            # 'energy' is requested for current output
            data = rate_to_energy(data, data_set, start_date, end_date)
        else:
            data = energy_to_rate(data, data_set, start_date, end_date)
