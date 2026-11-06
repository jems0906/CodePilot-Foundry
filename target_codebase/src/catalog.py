def normalize_code(value):
    return value.strip().lower().replace(" ", "-")


def normalize_group(value):
    return value.strip().lower().replace(" ", "-")


def find_item(items, code):
    wanted = code.strip().lower()
    for item in items:
        if item["code"].strip().lower() == wanted:
            return item
    return None


def find_group(items, group):
    wanted = group.strip().lower()
    matches = []
    for item in items:
        if item["group"].strip().lower() == wanted:
            matches.append(item)
    return matches


def active_items(items):
    result = []
    for item in items:
        if item.get("active", True) == True:
            result.append(item)
    return result


def display_label(item):
    title = item.get("title", "").strip()
    group = item.get("group", "").strip()
    if title and group:
        return title + " / " + group
    if title:
        return title
    return group


def item_count(items):
    count = 0
    for _item in items:
        count += 1
    return count
