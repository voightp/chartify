from collections import defaultdict
import os
import sys

projects = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(projects, "eso_reader"))
sys.path.append(os.path.join(projects, "dash_app"))

from constants import TS, D, H, M, A, RP
from mini_classes import HeaderVariable


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

    def mask_header_dct(self, energy_power_dct, units_system, power_units, energy_units):
        """ Modify units on the header dictionary. """
        mask = {}

        default_energy_units = ["J"]
        default_power_units = ["W", "W/m2"]

        # energy_rate_dct : dct
        #     Defines if 'energy' or 'rate' will be reported for a specified interval
        # rate_units : {'W', 'kW', 'MW', 'Btu/h', 'kBtu/h'}
        #     Convert default 'Rate' outputs to requested units.
        # energy_units : {'J', 'kJ', 'MJ', 'GJ', 'Btu', 'kWh', 'MWh'}

        for interval, vars in self._header_dct.items():
            if interval in [TS, H]:
                mask[interval] = {}
                for id, var in vars.items():
                    units = var.units
                    if units == "J" or units == "W":
                        mask[interval][id] = HeaderVariable(var.key, var.variable, power_units)
                    else:
                        mask[interval][id] = var

            if interval in [D, M, A, RP]:
                mask[interval] = {}
                for id, var in vars.items():
                    units = var.units
                    if units == "J":
                        mask[interval][id] = HeaderVariable(var.key, var.variable, power_units)
                    else:
                        mask[interval][id] = var

    def header_view(self, group_by_key="raw", interval_request=None):
        """ Create tree with categorized values. """
        dct = self._filtered_header_no_ids(request=interval_request)

        if group_by_key == "raw":
            return dct

        else:
            idnt = ["key", "variable", "units"]
            idnt.remove(group_by_key)
            vis_dct = defaultdict(list)
            for data in dct:
                key = data.__getattribute__(group_by_key)
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
