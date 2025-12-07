import os
from django.db import connection, migrations, models
from django.conf import settings
from functools import partial

PATCHES_DIR = os.path.join(settings.DATABASE_DIR, "patches")
patches = [filename for filename in os.listdir(PATCHES_DIR) if os.path.isfile(os.path.join(PATCHES_DIR, filename))]

patches.sort()


def load_patch(filename):
    def run_sql_from_file(apps, schema_editor):
        file_path = os.path.join(PATCHES_DIR, filename)
        sql_statement = open(file_path).read()
        with connection.cursor() as c:
            if sql_statement.strip():  # Twoja poprawka
                c.execute(sql_statement)

    return run_sql_from_file


class Migration(migrations.Migration):
    dependencies = [
        ("histories", "0003_init_historyindexsync"),
        ("resources", "0007_rename_fields"),
        ("tags", "0002_initial"),
        ("users", "0003_internals"),
        ("organizations", "0002_initial"),
    ]

    operations = [migrations.RunPython(load_patch(filename)) for filename in patches]
