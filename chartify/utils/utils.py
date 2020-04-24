import os
from collections import namedtuple
from pathlib import Path
from random import randint
from typing import Sequence, List

import numpy as np
import pandas as pd
from PySide2.QtCore import QObject
from esofile_reader.constants import AVERAGED_UNITS
from esofile_reader.conversion_tables import rate_table, energy_table, si_to_ip

VariableData = namedtuple("VariableData", "key variable units proxyunits")
FilterTuple = namedtuple("FilterTuple", "key variable units")


def install_fonts(pth, database):
    files = os.listdir(pth)
    for file in files:
        p = os.path.join(pth, file)
        database.addApplicationFont(p)


def int_generator():
    """ Generate a stream of integers. """
    i = 0
    while True:
        yield i
        i += 1


def generate_ids(used_ids, n=1, max_id=99999):
    """ Create a list with unique ids. """
    ids = []
    while True:
        id_ = randint(1, max_id)
        if id_ not in used_ids and id_ not in ids:
            ids.append(id_)
            if len(ids) == n:
                break
    return ids


def calculate_totals(df):
    """ Calculate df sum or average (based on units). """
    units = df.columns.get_level_values("units")
    cnd = units.isin(AVERAGED_UNITS)

    avg_df = df.loc[:, cnd].mean()
    sum_df = df.loc[:, [not b for b in cnd]].sum()

    sr = pd.concat([avg_df, sum_df])

    return sr


def generate_id(used_ids, max_id=99999):
    """ Create a single unique id. """
    return generate_ids(used_ids, n=1, max_id=max_id)[0]


def get_str_identifier(base_name, check_list, delimiter=" ", start_i=None, brackets=True):
    """ Create a unique name by adding index number to the base name. """

    def add_num():
        si = f"({i})" if brackets else f"{i}"
        return f"{base_name}{delimiter}{si}"

    i = start_i if start_i else 0
    new_name = add_num() if start_i else base_name

    # add unique number if the file name is not unique
    while new_name in check_list:
        i += 1
        new_name = add_num()

    return new_name


def merge_dcts(dct1, *args):
    """ Merge given dicts with a reference one."""
    for arg in args:
        dct1 = update_dct_recursively(dct1, arg)
    return dct1


def update_dct_recursively(dct, ref_dct):
    """ Update nested dict using reference dict. """
    for k, v in ref_dct.items():
        dv = dct.get(k, [] if isinstance(v, list) else {})

        if isinstance(v, list) and isinstance(dv, list):
            dct[k] = update_list_recursively(dv, v)
        elif not isinstance(dv, dict):
            dct[k] = v
        elif isinstance(v, dict):
            dct[k] = update_dct_recursively(dv, v)
        else:
            dct[k] = v

    return dct


def update_list_recursively(lst, ref_lst):
    """ Update nested list using reference list. """
    for i in range(len(ref_lst)):
        upd_item = ref_lst[i]
        if upd_item is None:
            # leave the item as it is
            try:
                lst[i]
            except IndexError:
                raise IndexError(
                    "Cannot skip an item as the base list"
                    " length is lower than current index. "
                )
            continue
        try:
            lst[i]
        except IndexError:
            lst.append(upd_item)

        if isinstance(upd_item, dict) and isinstance(lst[i], dict):
            lst[i] = update_dct_recursively(lst[i], upd_item)
        elif not isinstance(lst[i], list):
            lst[i] = upd_item
        elif isinstance(upd_item, list):
            lst[i] = update_list_recursively(lst[i], upd_item)
        else:
            lst[i] = upd_item

    return lst


def update_recursively(obj, ref_obj):
    """ Update nested object (list or dict) using reference object. """
    if isinstance(obj, list) and isinstance(ref_obj, list):
        obj = update_list_recursively(obj, ref_obj)
    elif isinstance(obj, dict) and isinstance(ref_obj, dict):
        obj = update_dct_recursively(obj, ref_obj)
    else:
        raise TypeError(
            f"Cannot update object '{obj.__class__.__name__}' using"
            f" object '{ref_obj.__class__.__name__}'"
        )
    return obj


def remove_recursively(dct, ref_dct):
    """ Remove nested dict attributes using reference dict. """
    for k, v in ref_dct.items():
        try:
            dct[k]
        except KeyError:
            continue

        if not isinstance(v, dict):
            del dct[k]
        else:
            remove_recursively(dct[k], v)


def create_proxy_units_column(
        source_units: pd.Series,
        rate_to_energy: bool,
        units_system: str,
        energy_units: str,
        power_units: str,
) -> pd.Series:
    # always replace whitespace with dash
    proxy_units = pd.Series(np.empty(source_units.size))
    proxy_units[:] = np.NaN
    pairs = [("", "-")]
    all_units = source_units.unique()

    if energy_units != "J":
        pairs.extend(
            [
                ("J", energy_table(energy_units)[1]),
                ("J/m2", energy_table(energy_units, per_area=True)[1]),
            ]
        )

    if power_units != "W":
        pairs.extend(
            [
                ("W", rate_table(power_units)[1]),
                ("W/m2", rate_table(power_units, per_area=True)[1]),
            ]
        )

    if rate_to_energy:
        if energy_units != "J":
            pairs.extend(
                [
                    ("W", energy_table(energy_units)[1]),
                    ("W/m2", energy_table(energy_units, per_area=True)[1]),
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
        proxy_units.loc[source_units == o] = n

    # replace all missing fields with original units
    proxy_units.loc[proxy_units.isna()] = source_units

    return proxy_units


class SignalBlocker:
    def __init__(self, *args: QObject):
        self.args = args

    def __enter__(self):
        for a in self.args:
            a.blockSignals(True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for a in self.args:
            a.blockSignals(False)


def refresh_css(*args):
    """ Refresh CSS of the widget. """
    for a in args:
        a.style().unpolish(a)
        a.style().polish(a)


def printdict(dct, limit=10):
    """ Print dictionary ignoring massive lists. """
    print_dict = {}
    for k, v in dct.items():
        if isinstance(v, dict):
            print_dict[k] = printdict(v, limit=limit)
        elif isinstance(v, list):
            lst = []
            if len(v) > limit:
                print_dict[k] = "[... list too long ...]"
                continue
            else:
                for item in v:
                    if isinstance(item, dict):
                        lst.append(printdict(item))
                    else:
                        lst.append(item)
            print_dict[k] = lst
        else:
            print_dict[k] = v
    return print_dict


def get_top_level_widget(wgt):
    top_level = None

    def traverse(wgt):
        parent = (wgt.parent())
        if parent:
            traverse(parent)
        else:
            nonlocal top_level
            top_level = wgt

    traverse(wgt)

    return top_level


def filter_files(paths: List[str], extensions: Sequence[str] = (".eso",)):
    """ Return a list of file paths with given extensions. """
    filtered = []
    for path in paths:
        p = Path(path)
        if p.suffix in extensions:
            filtered.append(path)
    return filtered
