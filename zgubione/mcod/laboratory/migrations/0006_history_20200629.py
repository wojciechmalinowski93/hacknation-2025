import os

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("laboratory", "0005_auto_20200625_1042"),
    ]

    operations = [
        migrations.RunSQL(
            sql=open(os.path.join(settings.DATABASE_DIR, "ODSOFT-261-laboratory-history.sql")).read(),
            reverse_sql=open(os.path.join(settings.DATABASE_DIR, "ODSOFT-261-laboratory-history_backward.sql")).read(),
        )
    ]
