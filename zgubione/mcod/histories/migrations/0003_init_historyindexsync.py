from django.db import migrations
from django.utils.timezone import now


def init_histories_index_sync(apps, schema_editor):
    # TODO this should be fixed.
    HistoryIndexSync = apps.get_model("histories", "HistoryIndexSync")
    HistoryIndexSync.objects.create(last_indexed=now())


class Migration(migrations.Migration):

    dependencies = [
        ("histories", "0002_historyindexsync"),
    ]

    operations = [
        migrations.RunPython(init_histories_index_sync),
    ]
