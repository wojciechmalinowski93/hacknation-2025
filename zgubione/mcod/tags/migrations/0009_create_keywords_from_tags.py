from collections import defaultdict
import itertools

from django.db import migrations


def forwards_func(apps, schema_editor):
    def name_en(tag):
        if isinstance(tag.i18n, dict) and "name_en" in tag.i18n:
            return tag.i18n["name_en"]

    Tag = apps.get_model("tags", "Tag")
    Dataset = apps.get_model("datasets", "Dataset")
    Application = apps.get_model("applications", "Application")

    tag_id_to_keywords = defaultdict(list)
    datasets = Dataset.objects.prefetch_related("tags").all()
    applications = Application.objects.prefetch_related("tags").all()

    for obj in itertools.chain(datasets, applications):
        for tag in obj.tags.all():
            if tag.id not in tag_id_to_keywords:
                keyword_pl, _ = Tag.objects.get_or_create(name=tag.name, language="pl")
                tag_id_to_keywords[tag.id].append(keyword_pl)

                tag_name_en = name_en(tag)
                if tag_name_en:
                    keyword_en, _ = Tag.objects.get_or_create(name=tag_name_en, language="en")
                    tag_id_to_keywords[tag.id].append(keyword_en)

            obj.tags.add(*tag_id_to_keywords[tag.id])


def reverse_func(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")
    Tag.objects.exclude(language="").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0008_auto_20210122_1658"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_code=reverse_func),
    ]
