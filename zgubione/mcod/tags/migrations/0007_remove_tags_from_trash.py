from django.db import migrations


def remove_tags_from_trash(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")
    Tag.objects.filter(is_removed=True).delete()  # doesn't use soft deletion, Tag here doesn't inherit from SoftDeletableModel


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0006_auto_20210115_2254"),
    ]

    operations = [
        migrations.RunPython(remove_tags_from_trash),
    ]
