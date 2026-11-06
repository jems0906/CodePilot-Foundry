from src.text_utils import make_slug, normalize_label, normalize_tag


def test_normalize_label_trims_and_folds_unicode() -> None:
    assert normalize_label("  STRASSE  ") == "strasse"
    assert normalize_label("  Straße  ") == "strasse"


def test_normalize_tag_trims_and_folds_unicode() -> None:
    assert normalize_tag("  Straße  ") == "strasse"


def test_make_slug_trims_and_replaces_spaces() -> None:
    assert make_slug("  Hello World ") == "hello-world"
