from src.catalog import active_items, display_label, find_group, find_item, item_count, normalize_code, normalize_group


ITEMS = [
    {"code": "red-fox", "group": "Animals", "title": "Red fox", "active": True},
    {"code": "snow-owl", "group": "Animals", "title": "Snow owl", "active": False},
    {"code": "field-notes", "group": "Books", "title": "Field notes"},
]


def test_normalizers_trim_and_replace_spaces() -> None:
    assert normalize_code("  Red Fox ") == "red-fox"
    assert normalize_group("  Animal Guide ") == "animal-guide"


def test_find_helpers_ignore_case_and_trim() -> None:
    assert find_item(ITEMS, " RED-FOX ") == ITEMS[0]
    assert find_group(ITEMS, " animals ") == ITEMS[:2]


def test_active_items_and_display_label() -> None:
    assert active_items(ITEMS) == [ITEMS[0], ITEMS[2]]
    assert display_label(ITEMS[0]) == "Red fox / Animals"
    assert display_label({"group": "Books"}) == "Books"


def test_item_count() -> None:
    assert item_count(ITEMS) == 3
