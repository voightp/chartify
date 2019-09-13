from random import randint


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


def generate_id(used_ids, max_id=99999):
    """ Create a single unique id. """
    return generate_ids(used_ids, n=1, max_id=max_id)[0]


def get_str_identifier(base_name, check_list, delimiter=" ",
                       start_i=None, brackets=True):
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
                raise IndexError("Cannot skip an item as the base list"
                                 " length is lower than current index. ")
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
        raise TypeError(f"Cannot update object '{obj.__class__.__name__}' using"
                        f" object '{ref_obj.__class__.__name__}'")
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


data = {
    "data": [
        {"x": [1, 2, 3],
         "y": [4, 5, 6],
         "itemId": "kchoo"},
        {"x": [7, 8, 9],
         "y": [10, 11, 12],
         "itemId": "bar"}
    ],
    "layout": {
        "autosize": True,
        "modebar": {"activecolor": "rgba(175,28,255,0.5)",
                    "bgcolor": "rgba(0, 0, 0, 0)",
                    "color": "rgba(175,28,255,1)",
                    "orientation": "h"},
        "paper_bgcolor": "transparent",
        "plot_bgcolor": "transparent",
        "showlegend": True,
        "title": {"text": "A Fancy Plot"},
        "xaxis": {"autorange": True,
                  "range": [],
                  "type": "linear",
                  "gridcolor": "white"},
        "yaxis": {"autorange": True,
                  "range": [],
                  "type": "linear",
                  "gridcolor": "white"}
    }
}
