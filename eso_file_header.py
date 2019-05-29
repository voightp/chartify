from collections import defaultdict, namedtuple


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

    def _header_no_ids(self, interval):
        """ Return a list of header variables for a given interval. """
        return list(self._header_dct[interval])

    @staticmethod
    def _get_field_names(group_by_key):
        """ Rearrange variable order. . """
        order = ["key", "variable", "units"]
        order.remove(group_by_key)
        order.insert(0, group_by_key)
        return order

    @staticmethod
    def create_proxy(header, interval, units_settings, field_names):
        """ Create a list of proxy variables. """
        energy_dct, units_system, energy_units, power_units = units_settings
        use_energy = energy_dct[interval]
        ProxyHeaderVariable = namedtuple("ProxyHeaderVariable", field_names)
        proxy_header = []

        for var in header:
            units = var.units

            if units in ["W", "W/m2", "J"]:
                units = handle_energy_power(units, use_energy)

            proxy_units = convert_units(units, units_system, energy_units, power_units)
            proxy = ProxyHeaderVariable(key=var.key, variable=var.variable, units=proxy_units)

            proxy_header.append(proxy)

        return proxy_header

    @classmethod
    def tree_header(cls, header_iterator, group_by_key):
        """ Group variables into tree based on given key. """
        dct = defaultdict(list)

        for data, proxy in header_iterator:
            key = proxy.__getattr__(group_by_key)
            proxy.__setattr__(group_by_key, None)
            dct[key].append((data, proxy))

        return dct

    def get_header_iterator(self, interval, units_settings, group_by_key):
        """ Return data - proxy paired list of tuples. """
        header = self._header_no_ids(interval)
        field_names = self._get_field_names(group_by_key)

        proxy = self.create_proxy(header,
                                  interval,
                                  units_settings,
                                  field_names)

        return zip(header, proxy)


def convert_power(units, power_units):
    """ Convert power units. """
    if units == "W/m2" and "btu" in power_units.lower():
        return power_units + ".ft2"
    else:
        return power_units + "/m2"


def handle_energy_power(units, is_energy):
    """ Return proxy units for given parameters. """
    if is_energy and (units == "W" or units == "W/m2"):
        return "J/m2" if units == "W/m2" else "J"

    elif not is_energy and units == "J":
        return "W"

    else:
        return units


def convert_units(units, units_system, energy_units, power_units):
    """ Convert given units into requested format. """
    if (units == "W" or "W/m2") and power_units != "W":
        return convert_power(units, power_units)

    elif units == "J" and energy_units != "J":
        return energy_units

    elif units_system == "IP":
        return to_ip(units)


def to_ip(units):
    """
    m           ->      ft
    m2          ->      ft2
    m3          ->      ft3
    deltaC      ->      deltaF
    m/s         ->      ft/min
    kg          ->      lb
    kg/s        ->      lb/min
    m3/s        ->      g/min
    Pa          ->      lbsf/ft2
    J/kg        ->      btu/lb
    kg/m3       ->      lb/f3
    W/m2-K      ->      btu/hr-ft2-F
    J/kg-K      ->      btu/lb-F
    W/m-K       ->      btu/hr-ft-F
    m2/s        ->      ft2/s
    m2-K/W      ->      F-ft-hr/btu
    lx          ->
    lm          ->
    cd          ->
    cd/m2       ->
    """

    request = units.lower()
    table = {
        "m": "ft",
        "m2": "ft2",
        "m3": "ft3",
        "deltaC": "deltaF",
        "C": "F",
        "K": "F",
        "m/s": "ft/min",
        "kg": "lb",
        "kg/s": "lb/min",
        "m3/s": "g/min",
        "Pa": "lbsf/ft2",
        "J/kg": "btu/lb",
        "kg/m3": "lb/f3",
        "W/m2-K": "btu/hr-ft2-F",
        "J/kg-K": "btu/lb-F",
        "W/m-K": "btu/hr-ft-F",
        "m2/s": "ft2/s",
        "m2-K/W": "F-ft-hr/btu",
    }

    try:
        units = table[request]

    except KeyError:
        print("Cannot convert to IP, original units [{}] kept!".format(units))
        pass

    return units
