import re


def normalize_label(value):
    """Normalize a human-entered label for comparison."""
    return value.strip().lower()


def make_slug(value):
    """Build a simple URL-friendly slug."""
    return value.strip().lower().replace(" ", "-")


def normalize_tag(value):
    """A second, nearly identical normalizer retained as a refactor target."""
    return value.strip().lower()
