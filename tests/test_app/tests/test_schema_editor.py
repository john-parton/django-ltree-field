"""
Tests for django_ltree_field schema editor functionality.

This module tests the schema editor mixin that manages ltree triggers
for LTreeFields during model creation, alteration, and deletion.
"""
from django.db import connection
from django.test import TestCase

from django_ltree_field.fields import LTreeField, LTreeTrigger
from django_ltree_field.schema_editor import (
    _get_ltree_meta,
    _add_ltree_triggers,
    _delete_ltree_triggers,
)


class TestSchemaEditorMixin(TestCase):
    """Tests for the schema editor mixin."""

    def test_get_ltree_meta(self):
        """Test _get_ltree_meta function generates expected names."""
        field = LTreeField(triggers=LTreeTrigger.CASCADE)
        field.set_attributes_from_name("test_path")
        
        with connection.schema_editor() as schema_editor:
            meta = _get_ltree_meta(
                schema_editor=schema_editor,
                field=field,
                db_table="test_table"
            )
            
            # Check format of returned dictionary
            self.assertIn("table_name", meta)
            self.assertIn("column_name", meta)
            self.assertIn("function_name", meta)
            self.assertIn("trigger_name", meta)
            
            # Check that names contain the expected components
            self.assertIn("test_table", meta["table_name"])
            self.assertIn("test_path", meta["column_name"])
            self.assertIn("ltree", meta["function_name"])
            self.assertIn("ltree_trg", meta["trigger_name"])

    def test_add_and_delete_ltree_triggers(self):
        """Test adding and removing ltree triggers."""
        field = LTreeField(triggers=LTreeTrigger.CASCADE)
        field.set_attributes_from_name("test_path")
        
        # Create a temporary table for testing
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE test_ltree_table (id serial PRIMARY KEY, test_path ltree)"
            )

        try:
            with connection.schema_editor() as schema_editor:
                # Add triggers
                _add_ltree_triggers(
                    schema_editor=schema_editor,
                    field=field,
                    db_table="test_ltree_table"
                )
                
                # Check if the trigger exists
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT count(*) FROM pg_trigger 
                        WHERE tgrelid = 'test_ltree_table'::regclass 
                        AND tgname LIKE '%_ltree_trg'
                    """)
                    count = cursor.fetchone()[0]
                    self.assertEqual(count, 1)
                
                # Delete triggers
                _delete_ltree_triggers(
                    schema_editor=schema_editor,
                    field=field,
                    db_table="test_ltree_table"
                )
                
                # Check if the trigger was deleted
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT count(*) FROM pg_trigger 
                        WHERE tgrelid = 'test_ltree_table'::regclass 
                        AND tgname LIKE '%_ltree_trg'
                    """)
                    count = cursor.fetchone()[0]
                    self.assertEqual(count, 0)
        finally:
            # Clean up the test table
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS test_ltree_table")

    def test_null_triggers(self):
        """Test that no triggers are created when triggers is None."""
        field = LTreeField(triggers=None)
        field.set_attributes_from_name("test_path")
        
        # Create a temporary table for testing
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE test_ltree_null_table (id serial PRIMARY KEY, test_path ltree)"
            )

        try:
            with connection.schema_editor() as schema_editor:
                # Add triggers
                _add_ltree_triggers(
                    schema_editor=schema_editor,
                    field=field,
                    db_table="test_ltree_null_table"
                )
                
                # Check that no trigger was created
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT count(*) FROM pg_trigger 
                        WHERE tgrelid = 'test_ltree_null_table'::regclass 
                        AND tgname LIKE '%_ltree_trg'
                    """)
                    count = cursor.fetchone()[0]
                    self.assertEqual(count, 0)
        finally:
            # Clean up the test table
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS test_ltree_null_table")