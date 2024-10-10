from __future__ import annotations

from typing import TypedDict

from numpy import delete

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

    def _get_ltree_meta(
        self,
        *,
        field: LTreeField,
        db_table: str,
    ) -> _LTreeMetaDict:
        return {
            "table_name": self.quote_name(db_table),
            "column_name": self.quote_name(field.column),
            # _create_index_name reuses Django private logic
            # Makes a name that is unique to the model and field
            # See https://github.com/django/django/blob/c499184f198df8deb8b5f7282b679babef8384ff/django/db/backends/base/schema.py#L1486-L1516
            "function_name": self._create_index_name(
                db_table,
                [field.column],
                suffix="_ltree",
            ),
            "trigger_name": self._create_index_name(
                db_table,
                [field.column],
                suffix="_ltree_trg",
            ),
        }

    def create_model(self, model):
        retval = super().create_model(model)

        for field in model._meta.local_fields:
            if isinstance(field, LTreeField):
                self._add_ltree_triggers(
                    field=field,
                    db_table=model._meta.db_table,
                )

        return retval

    def delete_model(self, model):
        for field in model._meta.local_fields:
            if isinstance(field, LTreeField):
                self._delete_ltree_triggers(
                    field=field,
                    db_table=model._meta.db_table,
                )

        return super().delete_model(model)

    def alter_db_table(self, model, old_db_table, new_db_table):
        """Rename the table a model points to."""
        # Do not run any logic if not applicable
        if old_db_table == new_db_table or not any(
            isinstance(field, LTreeField) for field in model._meta.local_fields
        ):
            return super().alter_db_table(model, old_db_table, new_db_table)

        ltree_fields = [
            field for field in model._meta.local_fields if isinstance(field, LTreeField)
        ]

        for field in ltree_fields:
            self._delete_ltree_triggers(
                field=field,
                db_table=old_db_table,
            )

        retval = super().alter_db_table(model, old_db_table, new_db_table)

        for field in ltree_fields:
            self._add_ltree_triggers(
                field=field,
                db_table=new_db_table,
            )

        return retval

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
                        RAISE EXCEPTION $err$Cannot delete '%%s' while {table_name}.{column_name} has descendants.$err$, OLD.{column_name};
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
                            RAISE EXCEPTION 'errrr';
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
                        RAISE EXCEPTION $err$Cannot move '%%s' while {table_name}.{column_name} has descendants.$err$, NEW.{column_name};
                    END IF;
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
                            RAISE EXCEPTION 'errrr';
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
        )

    def _add_ltree_triggers(self, *, field: LTreeField, db_table: str):
        if field.triggers is None:
            return

        meta = self._get_ltree_meta(
            field=field,
            db_table=db_table,
        )

        if field.triggers == LTreeTrigger.PROTECT:
            self._create_ltree_protect_function(**meta)
        elif field.triggers == LTreeTrigger.CASCADE:
            self._create_ltree_cascade_function(**meta)
        else:
            raise AssertionError

        # We might prefer
        # WHEN (OLD.{meta['column_name']} IS DISTINCT FROM NEW.{meta['column_name']})
        # instead of UPDATE OF ?

        self.execute(
            f"""
            CREATE TRIGGER {meta['trigger_name']}
                BEFORE DELETE OR INSERT OR UPDATE OF {meta['column_name']}
                ON {meta['table_name']}
                FOR EACH ROW
                EXECUTE PROCEDURE {meta['function_name']}();
            """
        )

    def _delete_ltree_triggers(self, *, field: LTreeField, db_table: str):
        meta = self._get_ltree_meta(
            field=field,
            db_table=db_table,
        )

        self.execute(
            f"""
            DROP TRIGGER {meta['trigger_name']} ON {meta['table_name']};
            DROP FUNCTION {meta['function_name']}();
            """
        )

    def add_field(self, model, field):
        """Hooks into the add_field method to add triggers for ltree fields."""
        retval = super().add_field(model, field)
        # Don't create the triggers until after the field has been added
        # I don't believe this is strictly necessary, as triggers are attached
        # to tables and not fields, but it's logically consistent
        if isinstance(field, LTreeField):
            self._add_ltree_triggers(
                field=field,
                db_table=model._meta.db_table,
            )
        return retval

    def remove_field(self, model, field):
        """
        Remove a field from a model. Usually involves deleting a column,
        but for M2Ms may involve deleting a table.
        """
        if isinstance(field, LTreeField):
            # Not tested very well
            self._delete_ltree_triggers(
                field=field,
                db_table=model._meta.db_table,
            )

        return super().remove_field(model, field)
