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


def get_str_identifier(base_name, check_list, delimiter=" ", start_i=None):
    """ Create a unique name by adding index number to the base name. """

    def add_num():
        return f"{base_name}{delimiter}({i})"

    i = start_i if start_i else 0
    new_name = add_num() if start_i else base_name

    # add unique number if the file name is not unique
    while new_name in check_list:
        i += 1
        new_name = add_num()

    return new_name
