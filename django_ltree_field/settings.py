from django.conf import settings


def should_patch_schema_editor() -> bool:
    """Whether to patch the schema editor.

    Settings this to False will mean that the triggers required
    for ltree fields will not be created automatically.
    """
    return getattr(settings, "LTREE_PATCH_SCHEMA_EDITOR", True)
