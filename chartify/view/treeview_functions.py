from collections import namedtuple

import pandas as pd
from esofile_reader.conversion_tables import rate_table, energy_table, si_to_ip


def add_proxy_units_column(
        variables_df: pd.DataFrame,
        rate_to_energy: bool,
        units_system: str,
        energy_units: str,
        power_units: str
) -> None:
    # always replace whitespace with dash
    pairs = [("", "-")]
    all_units = variables_df["source units"].unique()

    if energy_units != "J":
        pairs.extend(
            [
                ("J", energy_table(energy_units)[1]),
                ("J/m2", energy_table(energy_units, per_area=True)[1])
            ]
        )

    if power_units != "W":
        pairs.extend(
            [
                ("W", rate_table(power_units)[1]),
                ("W/m2", rate_table(power_units, per_area=True)[1])
            ]
        )

    if rate_to_energy:
        if energy_units != "J":
            pairs.extend(
                [
                    ("W", energy_table(energy_units)[1]),
                    ("W/m2", energy_table(energy_units, per_area=True)[1])
                ]
            )
        else:
            pairs.extend([("W", "J"), ("W/m2", "J/m2")])

    if units_system != "SI":
        for u in all_units:
            ip = si_to_ip(u)
            if ip:
                pairs.append((ip[0], ip[1]))

    # populate proxy column with new units
    for o, n in pairs:
        variables_df.loc[variables_df["source units"] == o, "units"] = n

    print(variables_df["source units"].isnull())
    variables_df.loc[variables_df["units"].isna(), "units"] = variables_df[
        "source units"]


def create_proxy(variables, view_order, rate_to_energy,
                 units_system, energy_units, power_units):
    """ Return data - proxy paired list of tuples. """
    order = list(view_order)
    ProxyVariable = namedtuple("ProxyVariable", order)
    proxy_variables = []

    for var in variables:
        units = var.units

        if units in ["W", "W/m2"]:
            units = handle_rate_to_energy(units, rate_to_energy)

        proxy_units = convert_units(units, units_system,
                                    energy_units, power_units)
        proxy = ProxyVariable(key=var.key,
                              variable=var.variable,
                              units=proxy_units)

        proxy_variables.append(proxy)

    return proxy_variables


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
