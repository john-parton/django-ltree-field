from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypedDict,
    runtime_checkable,
)

from django_ltree_field.fields import LTreeField, LTreeTrigger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models import Model
    from django.db.models.fields import Field


class _LTreeMetaDict(TypedDict):
    function_name: str
    table_name: str
    column_name: str
    trigger_name: str


@runtime_checkable
class DatabaseSchemaEditorProtocol(Protocol):
    """Ensure that the schema editor provides the required methods for managing
    ltree triggers when patched.

    This acts as a safeguard against potential future changes in Django's schema
    editor implementation that could disrupt the functionality of the ltree schema
    editor mixin.
    """

    def _alter_field(
        self,
        model: type[Model],
        old_field: Field[Any, Any],
        new_field: Field[Any, Any],
        old_type: str,
        new_type: str,
        old_db_params: dict[str, Any],
        new_db_params: dict[str, Any],
        strict: bool = False,
    ): ...

    def execute(
        self,
        sql: str,
        params: tuple[Any, ...] | None = (),
    ): ...

    def quote_name(
        self,
        name: str,
    ) -> str: ...

    def _create_index_name(
        self,
        table_name: str,
        column_names: Iterable[str],
        suffix: str,
    ) -> str: ...

    def create_model(
        self,
        model: type[Model],
    ): ...

    def delete_model(
        self,
        model: type[Model],
    ): ...

    def alter_db_table(
        self,
        model: type[Model],
        old_db_table: str,
        new_db_table: str,
    ): ...

    def add_field(
        self,
        model: type[Model],
        field: Field[Any, Any],
    ): ...

    def remove_field(
        self,
        model: type[Model],
        field: Field[Any, Any],
    ): ...


def _get_ltree_meta(
    *,
    schema_editor: DatabaseSchemaEditorProtocol,
    field: LTreeField,
    db_table: str,
) -> _LTreeMetaDict:
    return {
        "table_name": schema_editor.quote_name(db_table),
        "column_name": schema_editor.quote_name(field.column),
        # _create_index_name reuses Django private logic
        # Makes a name that is unique to the model and field
        # See https://github.com/django/django/blob/c499184f198df8deb8b5f7282b679babef8384ff/django/db/backends/base/schema.py#L1486-L1516
        "function_name": schema_editor._create_index_name(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            db_table,
            [field.column],
            suffix="_ltree",
        ),
        "trigger_name": schema_editor._create_index_name(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            db_table,
            [field.column],
            suffix="_ltree_trg",
        ),
    }


def _add_ltree_triggers(
    schema_editor: DatabaseSchemaEditorProtocol,
    *,
    field: LTreeField,
    db_table: str,
) -> None:
    """Add PostgreSQL ltree triggers to a database table for managing hierarchical data.

    This function creates and attaches PostgreSQL triggers to a table to enforce
    hierarchical constraints and manage cascading updates or deletions for ltree fields.
    The triggers can either protect the hierarchy from invalid operations or cascade
    changes to descendant nodes.

    Parameters
    ----------
    schema_editor : DatabaseSchemaEditorProtocol
        The database schema editor used to execute SQL commands.
    field : LTreeField
        The ltree field for which the triggers are being created.
    db_table : str
        The name of the database table to which the triggers will be added.

    Raises
    ------
    AssertionError
        If the `field.triggers` attribute is not set to a valid `LTreeTrigger` value.

    Notes
    -----
    If the `triggers` attribute of the `field` is `None`, the function exits early
    without performing any operations.
    """
    if field.triggers is None:
        return

    meta = _get_ltree_meta(
        schema_editor=schema_editor,
        field=field,
        db_table=db_table,
    )

    # Template strings for creating the ltree trigger functions
    # All of the parameters MUST be passed in as valid SQL identifiers to avoid SQL
    # injection.
    # Use of this function outside of _add_ltree_triggers should be prohibited, so
    # it is in not in the public API.
    cascade = """
    CREATE FUNCTION {function_name}() RETURNS TRIGGER AS
    $func$
    BEGIN
        -- I put both of the ops in one trigger so we don't have to pollute the namespace
        -- with two functions and two triggers
        IF (TG_OP = 'DELETE') THEN
            DELETE
            FROM
                {table_name}
            WHERE
                {column_name} <@ OLD.{column_name} AND {column_name} != OLD.{column_name};
            RETURN OLD;

        ELSIF (TG_OP = 'INSERT') THEN
            -- Raise an exception if there's not a proper parent of a non-root
            -- node
            IF (nlevel(NEW.{column_name}) > 1) AND NOT EXISTS (
                    SELECT
                        1
                    FROM
                        {table_name}
                    WHERE
                        {column_name} = subpath(NEW.{column_name}, 0, -1)
                ) THEN
                    RAISE EXCEPTION $err$Cannot insert '%%' into {table_name}.{column_name} because '%%' does not exist.$err$, NEW.{column_name}, subpath(NEW.{column_name}, 0, -1);
            END IF;
            RETURN NEW;
        ELSIF (TG_OP = 'UPDATE') THEN
            UPDATE
                {table_name}
            SET
                {column_name}  = NEW.{column_name}  || subpath({column_name}, nlevel(OLD.{column_name}))
            WHERE
                {column_name} <@ OLD.{column_name} AND {column_name} != OLD.{column_name};
        END IF;
        RETURN NEW; 
    END;
    $func$ LANGUAGE plpgsql;
    """

    protect = """
    CREATE FUNCTION {function_name}() RETURNS TRIGGER AS
    $func$
    BEGIN

        IF (TG_OP = 'DELETE') THEN
            IF EXISTS (
                SELECT
                    1
                FROM
                    {table_name}
                WHERE
                    {column_name} <@ OLD.{column_name} AND {column_name} != OLD.{column_name}
            ) THEN
                RAISE EXCEPTION $err$Cannot delete '%%' while {table_name}.{column_name} has descendants.$err$, OLD.{column_name};
            END IF;

        ELSIF (TG_OP = 'INSERT') THEN
            -- Raise an exception if there's not a proper parent of a non-root
            -- node
            IF (nlevel(NEW.{column_name}) > 1) AND NOT EXISTS (
                    SELECT
                        1
                    FROM
                        {table_name}
                    WHERE
                        {column_name} = subpath(NEW.{column_name}, 0, -1)
                ) THEN
                    RAISE EXCEPTION $err$Cannot insert '%%' into {table_name}.{column_name} because '%%' does not exist.$err$, NEW.{column_name}, subpath(NEW.{column_name}, 0, -1);
            END IF;
            RETURN NEW;
        ELSIF (TG_OP = 'UPDATE') THEN
            IF OLD.{column_name} IS DISTINCT FROM NEW.{column_name} AND EXISTS (
                SELECT
                    1
                FROM
                    {table_name}
                WHERE
                    {column_name} <@ OLD.{column_name} AND {column_name} != OLD.{column_name}
            ) THEN
                RAISE EXCEPTION $err$Cannot move '%%' while {table_name}.{column_name} has descendants.$err$, NEW.{column_name};
            END IF;
        END IF;
        RETURN OLD;
    END;
    $func$ LANGUAGE plpgsql;
    """

    if field.triggers == LTreeTrigger.PROTECT:
        tmpl = protect
    elif field.triggers == LTreeTrigger.CASCADE:
        tmpl = cascade
    else:
        raise AssertionError

    schema_editor.execute(tmpl.format(**meta))

    # We might prefer
    # WHEN (OLD.{meta['column_name']} IS DISTINCT FROM NEW.{meta['column_name']})
    # instead of UPDATE OF ?

    schema_editor.execute(
        f"""
        CREATE TRIGGER {meta["trigger_name"]}
            AFTER DELETE OR INSERT OR UPDATE OF {meta["column_name"]}
            ON {meta["table_name"]}
            FOR EACH ROW
            EXECUTE PROCEDURE {meta["function_name"]}();
        """
    )


def _delete_ltree_triggers(
    schema_editor: DatabaseSchemaEditorProtocol,
    *,
    field: LTreeField,
    db_table: str,
):
    """Delete the triggers and associated functions for an LTreeField in the database.

    This function removes the database triggers and functions associated with the
    specified LTreeField if they exist. It uses the schema editor to execute the
    necessary SQL commands.

    Parameters
    ----------
    schema_editor : DatabaseSchemaEditorProtocol
        The schema editor instance used to execute SQL commands.
    field : LTreeField
        The LTreeField instance for which the triggers and functions are to be deleted.
    db_table : str
        The name of the database table associated with the LTreeField.
    """
    meta = _get_ltree_meta(
        field=field,
        db_table=db_table,
        schema_editor=schema_editor,
    )

    schema_editor.execute(
        f"""
        DROP TRIGGER IF EXISTS {meta["trigger_name"]} ON {meta["table_name"]};
        DROP FUNCTION IF EXISTS {meta["function_name"]}();
        """
    )


class DatabaseSchemaEditorMixin:
    """A schema editor mixin that can be combined with DatabaseSchemaEditor to manage ltree triggers.

    We want to automatically create and manage triggers based on metadata
    defined on the field. This mixin provides the necessary hooks to
    install triggers on the database when the field definitions are
    created or altered.
    """

    def _alter_field(
        self: DatabaseSchemaEditorProtocol,
        model: type[Model],
        old_field: Field[Any, Any],
        new_field: Field[Any, Any],
        *args,
        **kwargs,
    ):
        if isinstance(old_field, LTreeField):
            _delete_ltree_triggers(
                self,
                field=old_field,
                db_table=model._meta.db_table,
            )

        if isinstance(new_field, LTreeField):
            _add_ltree_triggers(
                self,
                field=new_field,
                db_table=model._meta.db_table,
            )

        return super()._alter_field(
            model,
            old_field,
            new_field,
            *args,
            **kwargs,
        )

    def create_model(
        self: DatabaseSchemaEditorProtocol,
        model: type[Model],
    ):
        retval = super().create_model(model)

        for field in model._meta.local_fields:
            if isinstance(field, LTreeField):
                _add_ltree_triggers(
                    self,
                    field=field,
                    db_table=model._meta.db_table,
                )

        return retval

    def delete_model(
        self: DatabaseSchemaEditorProtocol,
        model: type[Model],
    ):
        for field in model._meta.local_fields:
            if isinstance(field, LTreeField):
                _delete_ltree_triggers(
                    self,
                    field=field,
                    db_table=model._meta.db_table,
                )

        return super().delete_model(model)

    def alter_db_table(
        self: DatabaseSchemaEditorProtocol,
        model: type[Model],
        old_db_table: str,
        new_db_table: str,
    ):
        # When altering a table, drop and recreate triggers
        # The triggers would stay attached to the table even after a rename,
        # but the triggers themselves refer to the tables by name.
        # This also keeps our delete_model logic in check)

        ltree_fields = [
            field for field in model._meta.local_fields if isinstance(field, LTreeField)
        ]

        if old_db_table != new_db_table:
            for field in ltree_fields:
                _delete_ltree_triggers(
                    self,
                    field=field,
                    db_table=old_db_table,
                )

        retval = super().alter_db_table(model, old_db_table, new_db_table)

        if old_db_table != new_db_table:
            for field in ltree_fields:
                _add_ltree_triggers(
                    self,
                    field=field,
                    db_table=new_db_table,
                )

        return retval

    def add_field(
        self: DatabaseSchemaEditorProtocol,
        model: type[Model],
        field: Field[Any, Any],
    ):
        # If an LTreeField is added, we need to add the triggers
        retval = super().add_field(model, field)

        if isinstance(field, LTreeField):
            _add_ltree_triggers(
                self,
                field=field,
                db_table=model._meta.db_table,
            )
        return retval

    def remove_field(
        self: DatabaseSchemaEditorProtocol,
        model: type[Model],
        field: Field[Any, Any],
    ):
        # If an LTreeField is removed, we need to remove the triggers
        if isinstance(field, LTreeField):
            _delete_ltree_triggers(
                self,
                field=field,
                db_table=model._meta.db_table,
            )

        return super().remove_field(model, field)
