from __future__ import annotations

from typing import TypedDict

from django.db.models import Model

from django_ltree_field.fields import LTreeField, LTreeTrigger


class _LTreeMetaDict(TypedDict):
    function_name: str
    table_name: str
    column_name: str
    trigger_name: str


class DatabaseSchemaEditorMixin:
    """A schema editor mixin that can be combined with DatabaseSchemaEditor to manage ltree triggers.

    We want to automatically create and manage triggers based on metadata
    defined on the field. This mixin provides the necessary hooks to
    install triggers on the database when the field definitions are
    created or altered.
    """

    def _alter_field(
        self,
        model,
        old_field,
        new_field,
        old_type,
        new_type,
        old_db_params,
        new_db_params,
        strict=False,
    ):
        if isinstance(old_field, LTreeField) or isinstance(new_field, LTreeField):
            raise NotImplementedError(
                "Subclasses must implement this method to alter a field"
            )

        return super()._alter_field(
            model,
            old_field,
            new_field,
            old_type,
            new_type,
            old_db_params,
            new_db_params,
            strict=strict,
        )

    def _get_ltree_meta(self, model: type[Model], field: LTreeField) -> _LTreeMetaDict:
        return {
            "table_name": self.quote_name(model._meta.db_table),
            "column_name": self.quote_name(field.column),
            # _create_index_name reuses Django private logic
            # Makes a name that is unique to the model and field
            # See https://github.com/django/django/blob/c499184f198df8deb8b5f7282b679babef8384ff/django/db/backends/base/schema.py#L1486-L1516
            "function_name": self._create_index_name(
                model._meta.db_table,
                [field.column],
                suffix="_ltree",
            ),
            "trigger_name": self._create_index_name(
                model._meta.db_table,
                [field.column],
                suffix="_ltree_trg",
            ),
        }

    def create_model(self, model):
        retval = super().create_model(model)

        for field in model._meta.local_fields:
            if isinstance(field, LTreeField):
                self._add_ltree_triggers(model, field)

        return retval

    def _delete_ltree_trigger(self, model, field: LTreeField):
        meta = self._get_ltree_meta(model, field)

        self.execute(
            f"""
            DROP TRIGGER {meta['trigger_name']} ON {meta['table_name']};
            DROP FUNCTION {meta['function_name']}();
            """
        )

    def _create_ltree_protect_function(
        self,
        *,
        function_name: str,
        table_name: str,
        column_name: str,
        trigger_name: str,
    ):
        self.execute(
            f"""
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
                        RAISE EXCEPTION $err$Cannot delete '%s' while "{table_name}"."{column_name}" has descendants.$err$, OLD.{column_name};
                    END IF;
                ELSIF (TG_OP = 'UPDATE') THEN
                    IF EXISTS (
                        SELECT
                            1
                        FROM
                            {table_name}
                        WHERE
                            {column_name} <@ NEW.{column_name} AND {column_name} != NEW.{column_name}
                    ) THEN
                        RAISE EXCEPTION $err$Cannot update '%s' while "{table_name}"."{column_name}" has descendants.$err$, NEW.{column_name};
                    END IF;
                RETURN OLD;
            END;
            $func$ LANGUAGE plpgsql;
            """
        )

    def _create_ltree_cascade_function(
        self,
        *,
        function_name: str,
        table_name: str,
        column_name: str,
        trigger_name: str,
    ):
        self.execute(
            f"""
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

                ELSIF (TG_OP = 'UPDATE') THEN
                    UPDATE
                        {table_name}
                    SET
                        {column_name}  = NEW.{column_name}  || subpath({column_name}, nlevel(OLD.{column_name}))
                    WHERE
                        {column_name} <@ OLD.{column_name} AND {column_name} != OLD.{column_name};
                    RETURN NEW;
                END IF;
            END;
            $func$ LANGUAGE plpgsql;
            """
        )

    def _add_ltree_triggers(self, model, field: LTreeField):
        if field.triggers is None:
            return

        meta = self._get_ltree_meta(model, field)

        if field.triggers == LTreeTrigger.PROTECT:
            self._create_ltree_protect_function(**meta)
        elif field.triggers == LTreeTrigger.CASCADE:
            self._create_ltree_cascade_function(**meta)
        else:
            raise AssertionError

        self.execute(
            f"""
            CREATE TRIGGER {meta['trigger_name']}
                BEFORE DELETE OR UPDATE
                ON {meta['table_name']}
                FOR EACH ROW
                EXECUTE PROCEDURE {meta['function_name']}();
            """
        )

    def add_field(self, model, field):
        """Hooks into the add_field method to add triggers for ltree fields."""
        retval = super().add_field(model, field)
        # Don't create the triggers until after the field has been added
        # I don't believe this is strictly necessary, as triggers are attached
        # to tables and not fields, but it's logically consistent
        if isinstance(field, LTreeField):
            self._add_ltree_triggers(model, field)
        return retval

    def remove_field(self, model, field):
        """
        Remove a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        if isinstance(field, LTreeField):
            # Not tested very well
            self._delete_ltree_triggers(model, field)

        return super().remove_field(model, field)
