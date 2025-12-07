from django.db import migrations


def set_categories_types(apps, schema_editor):
    ArticleCategory = apps.get_model("articles", "ArticleCategory")
    ArticleCategory.objects.filter(pk=1).update(type="article")
    ArticleCategory.objects.filter(pk__in=[2, 3, 4]).update(type="knowledge_base")


def reverse_categories_types(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0018_articlecategory_type"),
    ]

    operations = [
        migrations.RunPython(set_categories_types, reverse_categories_types),
    ]
