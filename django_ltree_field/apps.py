from __future__ import annotations

import django.db.backends.postgresql.schema as postgresql_schema
from django.apps import AppConfig
from django.conf import settings
from django.db.utils import load_backend

from .schema_editor import DatabaseSchemaEditorMixin
from .settings import should_patch_schema_editor


def patch_schema_editor() -> None:
    """Patch the schema editor to allow for triggers to be for fields."""
    for config in settings.DATABASES.values():
        backend = load_backend(config["ENGINE"])
        schema_editor_class = backend.DatabaseWrapper.SchemaEditorClass

        if (
            schema_editor_class
            and issubclass(
                schema_editor_class,
                postgresql_schema.DatabaseSchemaEditor,
            )
            and not issubclass(schema_editor_class, DatabaseSchemaEditorMixin)
        ):
            backend.DatabaseWrapper.SchemaEditorClass = type(
                "DatabaseSchemaEditor",
                (DatabaseSchemaEditorMixin, schema_editor_class),
                {},
            )


class DjangoLTreeFieldConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_ltree_field"

    def ready(self):
        """Do necessary patching when the app is ready."""
        if should_patch_schema_editor():
            patch_schema_editor()
