from collections import defaultdict, namedtuple
from eso_reader.mini_classes import HeaderVariable, Variable


class FileHeader:
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

    def __init__(self, id_, header_dct):
        self.header_dct = header_dct
        self.id_ = id_
        self.hidden = defaultdict(dict)

    @property
    def available_intervals(self):
        """ Get a list of available intervals. """
        return self.header_dct.keys()

    @classmethod
    def tree_header(cls, header_iterator, tree_key):
        """ Group variables into tree based on given key. """
        dct = defaultdict(list)

        for data, proxy in header_iterator:
            key = proxy.__getattribute__(tree_key)
            dct[key].append((data, proxy))

        return dct

    def show_hidden_variables(self):
        """ Restore hidden variables visibility. """
        for interval, ids in self.hidden.items():
            for id_ in ids:
                var = self.hidden[interval][id_]
                self.header_dct[interval][id_] = var

        self.hidden = defaultdict(dict)

    def remove_hidden_variables(self):
        """ Remove hidden variables. """
        variables = []
        for interval, ids in self.hidden.items():
            for id_ in ids:
                var = self.hidden[interval][id_]
                variables.append(Variable(interval, *var))

        self.hidden = defaultdict(dict)
        return variables

    def hide_variables(self, groups):
        """ Temporarily hide variables from the ui. """
        for interval, ids in groups.items():
            for id_ in ids:
                var = self.header_dct[interval].pop(id_)
                self.hidden[interval][id_] = var
                # TODO check what happens if all the variables are hidden

    def remove_variables(self, groups):
        """ Remove header variables from the header. """
        for interval, ids in groups.items():
            for id_ in ids:
                del self.header_dct[interval][id_]

            if not self.header_dct[interval]:
                del self.header_dct[interval]

    def add_variable(self, id_, variable):
        """ Add a new variable (from 'Variable' class). """
        interval, key, variable, units = variable
        self.header_dct[interval][id_] = HeaderVariable(key, variable, units)

    def get_header_iterator(self, units_settings, view_order, interval):
        """ Return data - proxy paired list of tuples. """
        variables = list(self.header_dct[interval].values())

        (rate_to_energy, units_system,
         energy_units, power_units) = units_settings

        order = list(view_order)
        ProxyVariable = namedtuple("ProxyVariable", order)
        proxy_header = []

        for var in variables:
            units = var.units

            if units in ["W", "W/m2"]:
                units = handle_rate_to_energy(units, rate_to_energy)

            proxy_units = convert_units(units, units_system,
                                        energy_units, power_units)
            proxy = ProxyVariable(key=var.key,
                                  variable=var.variable,
                                  units=proxy_units)

            proxy_header.append(proxy)

        return zip(variables, proxy_header)


def convert_energy(units, energy_units):
    """ Convert energy units. """
    e = energy_units
    if units == "J/m2":
        return e + "-ft2" if "btu" in e.lower() else e + "/m2"

    else:
        return e


def convert_power(units, power_units):
    """ Convert power units. """
    p = power_units
    if units == "W/m2":
        return p + "-ft2" if "btu/h" in p.lower() else p + "/m2"

    else:
        return p


def handle_rate_to_energy(units, is_energy):
    """ Return proxy units for given parameters. """
    if is_energy and (units == "W" or units == "W/m2"):
        return "J/m2" if units == "W/m2" else "J"

    else:
        return units


def convert_units(units, units_system, energy_units, power_units):
    """ Convert given units into requested format. """
    if units == "":
        return "-"

    elif (units == "W" or units == "W/m2") and power_units != "W":
        return convert_power(units, power_units)

    elif (units == "J" or units == "J/m2") and energy_units != "J":
        return convert_energy(units, energy_units)

    elif units_system == "IP":
        return to_ip(units)

    else:
        return units


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

    request = units
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
        print(f"Cannot convert to IP, original units [{units}] kept!")
        pass

    return units
