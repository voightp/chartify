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


def create_unique_name(name, check_list):
    """ Create a unique name to avoid duplicates. """

    def add_num():
        return f"{name} ({i})"

    new_name = name
    i = 0

    # add unique number if the file name is not unique
    while new_name in check_list:
        i += 1
        new_name = add_num()

    return new_name
