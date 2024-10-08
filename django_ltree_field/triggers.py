from os import name
from django.db import router

from django.db.migrations.operations.base import Operation, OperationCategory


class LtreeTriggerOperation(Operation):
    category = OperationCategory.SQL

    def __init__(
        self,
        model_name: str,
        field_name: str,
    ):
        self.model_name = model_name
        self.field_name = field_name
        # Do we need 'hints' here?

    def _get_sql(
        self,
        *,
        table_name: str,
        column_name: str,
    ):
        raise NotImplementedError

    def _get_reverse_sql(
        self,
        *,
        table_name: str,
        column_name: str,
    ):
        return f"""
            DROP TRIGGER {table_name}_{column_name}_{self.name}_trg ON {table_name};
            DROP FUNCTION {table_name}_{column_name}_{self.name}();
        """

    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "field_name": self.field_name,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if router.allow_migrate(
            schema_editor.connection.alias,
            app_label,
            # **self.hints,
        ):
            # Should this be 'to model' or does it not matter?
            to_model = to_state.apps.get_model(app_label, self.model_name)
            field = to_model._meta.get_field(self.field_name)
            __, db_column = field.get_attname_column()
            self._run_sql(
                schema_editor,
                self._get_sql(
                    table_name=to_model._meta.db_table,
                    column_name=db_column,
                ),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if router.allow_migrate(
            schema_editor.connection.alias,
            app_label,
            #  **self.hints,
        ):
            from_model = from_state.apps.get_model(app_label, self.model_name)
            field = from_model._meta.get_field(self.field_name)
            __, db_column = field.get_attname_column()
            self._run_sql(
                schema_editor,
                self._get_reverse_sql(
                    table_name=from_model._meta.db_table,
                    column_name=db_column,
                ),
            )

    def _run_sql(self, schema_editor, sql):
        statements = schema_editor.connection.ops.prepare_sql_script(sql)
        for statement in statements:
            schema_editor.execute(statement, params=None)


class LtreeDeleteProtect(LtreeTriggerOperation):
    name = "delete_protect"

    def _get_sql(
        self,
        *,
        table_name: str,
        column_name: str,
    ):
        return f"""
            CREATE FUNCTION {table_name}_{column_name}_{self.name}() RETURNS TRIGGER AS
            $func$
            BEGIN
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
                RETURN OLD;
            END;
            $func$ LANGUAGE plpgsql;

            CREATE TRIGGER {table_name}_{column_name}_{self.name}_trg
                BEFORE DELETE
                ON {table_name}
                FOR EACH ROW
                EXECUTE PROCEDURE {table_name}_{column_name}_{self.name}();
        """

    def describe(self):
        return "Protects descendants of a node from deletion."


class LtreeDeleteCascade(LtreeTriggerOperation):
    name = "delete_cascade"

    def _get_sql(
        self,
        *,
        table_name: str,
        column_name: str,
    ):
        return f"""
            CREATE FUNCTION {table_name}_{column_name}_{self.name}() RETURNS TRIGGER AS
            $func$
            BEGIN
                DELETE
                FROM
                    {table_name}
                WHERE
                    {column_name} <@ OLD.{column_name} AND {column_name} != OLD.{column_name};
                RETURN OLD;
            END;
            $func$ LANGUAGE plpgsql;

            CREATE TRIGGER {table_name}_{column_name}_{self.name}_trg
                BEFORE DELETE
                ON {table_name}
                FOR EACH ROW
                EXECUTE PROCEDURE {table_name}_{column_name}_{self.name}();
        """

    def describe(self):
        return "Deletes descendants of a node when the node is deleted."
