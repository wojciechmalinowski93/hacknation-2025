from django_tqdm import BaseCommand

from mcod.categories.models import Category
from mcod.harvester.models import OLD_CATEGORY_TITLE_2_DCAT_CATEGORY_CODE, DataSource


class Command(BaseCommand):
    def handle(self, *args, **options):
        query = DataSource.raw.select_related("category").all()

        for data_source in query:
            data_source.categories.clear()

            if not data_source.category:
                continue

            dcat_category_code = OLD_CATEGORY_TITLE_2_DCAT_CATEGORY_CODE[data_source.category.title]
            dcat_category = Category.objects.get(code=dcat_category_code)
            categories = [dcat_category]
            data_source.categories.add(*categories)
