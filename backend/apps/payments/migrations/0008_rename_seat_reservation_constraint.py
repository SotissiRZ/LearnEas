from django.db import migrations


OLD_NAME = "uniq_order_formation_reservation"
NEW_NAME = "uniq_order_form_res"


def _rename_constraint(schema_editor, old_name: str, new_name: str) -> None:
    # PostgreSQL keeps an already-applied constraint name even when an older
    # migration file is corrected. Fresh installs already use NEW_NAME; this
    # conditional rename only repairs databases created by pre-v28 releases.
    if schema_editor.connection.vendor != "postgresql":
        return

    table = "payments_formationseatreservation"
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM pg_constraint AS con
            JOIN pg_class AS cls ON cls.oid = con.conrelid
            WHERE cls.relname = %s AND con.conname = %s
            LIMIT 1
            """,
            [table, old_name],
        )
        exists = cursor.fetchone() is not None

    if exists:
        quote = schema_editor.quote_name
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old_name)} TO {quote(new_name)}"
        )


def forwards(apps, schema_editor):
    _rename_constraint(schema_editor, OLD_NAME, NEW_NAME)


def backwards(apps, schema_editor):
    _rename_constraint(schema_editor, NEW_NAME, OLD_NAME)


class Migration(migrations.Migration):
    dependencies = [("payments", "0007_payment_config_constraints")]

    operations = [migrations.RunPython(forwards, backwards)]
