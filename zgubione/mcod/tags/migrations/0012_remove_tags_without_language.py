from django.db import migrations


def forwards_func(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")
    Tag.objects.filter(language="").delete()


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0011_auto_20210225_1246"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_code=reverse_func),
    ]
