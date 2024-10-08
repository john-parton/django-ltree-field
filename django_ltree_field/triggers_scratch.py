import re
from typing import Literal, TypeGuard

from django.db.migrations.operations import RunSQL


# TODO Prefer TypeIs on Python 3.13
def _sanity_check_identifier(identifier: object) -> TypeGuard[str]:
    return isinstance(identifier, str) and bool(
        re.search(r"^[a-z0-9]+(?:_[a-z0-9]+)*$", identifier)
    )


type TRIGGER_TYPE = Literal[
    "MOVE",
    "DELETE_CASCADE",
    "CONSTRAINT_CHECK",
]

MOVE_FUNCTION_SQL = """
CREATE FUNCTION ltree_update_descendants(_column text) RETURNS TRIGGER
$func$
BEGIN
    EXECUTE format(
        $inner$
            UPDATE %1s
                SET %2I = $1 || subpath(%2I, nlevel($2))
            WHERE
                %2I <@ $2 AND %2I != $1;
        $inner$,
        TG_RELID::regclass,
        _column
    )
    USING NEW._path, OLD._path;
END
$func$
LANGUAGE plpgsql;
"""

MOVE_FUNCTION_REVERSE_SQL = """
DROP FUNCTION ltree_update_descendants(_column text);
"""


class LtreeFunctions(RunSQL):
    def __init__(self):
        super().__init__(
            sql=MOVE_FUNCTION_SQL,
            reverse_sql=MOVE_FUNCTION_REVERSE_SQL,
            hints=None,
            state_operations=None,
            elidable=False,
        )


def _format_move_trigger(*, table_name: str, path_name: str, trigger_name: str) -> str:
    return f"""
        CREATE TRIGGER {trigger_name}
        AFTER UPDATE ON {table_name}
            FOR EACH ROW
            WHEN (NEW.{path_name} IS DISTINCT FROM OLD.{path_name})
            EXECUTE PROCEDURE ltree_update_descendants('{path_name}');
    """


def _format_drop_trigger(*, trigger_name: str, table_name: str) -> str:
    return f"""
        DROP TRIGGER {trigger_name} ON {table_name};
    """


CHECK_FUNCTION_SQL = """
CREATE FUNCTION ltree_constraint_check(_column) RETURNS TRIGGER AS
$func$
BEGIN
    EXECUTE format(
        $inner$
            SELECT 1
            FROM
                %1s
            WHERE
                nlevel(%2I) > 1 AND NOT EXISTS (
                    SELECT
                        1
                    FROM
                        %1s AS parent
                    WHERE
                        %2I = subpath(parent.%2I, 0, -1)
                );
        $inner$,
        TG_RELID::regclass,
        _column
    );

    IF FOUND THEN
        RAISE EXCEPTION 'Invalid path';
    END IF;

    RETURN NULL;
END;
$func$

    """


CONSTRAINT_CHECK_SQL_TEMPLATE = """
CREATE OR REPLACE FUNCTION check_{table_name}_{path_name}() RETURNS TRIGGER AS
$func$
BEGIN
    IF EXISTS (
        SELECT
            1
        FROM
            {table_name} JOIN
            {table_name} AS parent ON {table_name}.{path_name} = subpath(parent.{path_name}, 0, -1)
    ) THEN
        RAISE EXCEPTION 'Invalid path';
    END IF;
    RETURN NULL;
END;

CREATE CONSTRAINT TRIGGER {table_name}_{path_name}_check_trg
    AFTER INSERT OR UPDATE
    ON {table_name}
    DEFERRABLE
    FOR EACH ROW
    EXECUTE PROCEDURE check_{table_name}_{path_name}();
"""

CONSTRAINT_CHECK_REVERSE_SQL_TEMPLATE = """
DROP TRIGGER {table_name}_{path_name}_check_trg ON {table_name};
DROP FUNCTION check_{table_name}_{path_name}();
"""


class LtreeTrigger(RunSQL):
    def __init__(
        self,
        *,
        table_name: str,
        path_name: str,
        trigger_type: TRIGGER_TYPE,
        hints=None,
    ):
        if not _sanity_check_identifier(table_name):
            msg = f"Invalid table name: {table_name}"
            raise ValueError(msg)
        if not _sanity_check_identifier(path_name):
            msg = f"Invalid path name: {path_name}"
            raise ValueError(msg)

        if trigger_type == "MOVE":
            trigger_name = "{table_name}_{path_name}_update_trg"
        else:
            raise ValueError

        match trigger_type:
            case "MOVE":
                sql = _format_move_trigger(
                    table_name=table_name,
                    path_name=path_name,
                    trigger_name=trigger_name,
                )
            case _:
                raise ValueError

        super().__init__(
            sql=sql,
            reverse_sql=_format_drop_trigger(
                trigger_name=trigger_name,
                table_name=table_name,
            ),
            # Not sure it actually makes sense to pass these
            hints=hints,  # Not sure how this works
            state_operations=None,
            elidable=False,
        )
