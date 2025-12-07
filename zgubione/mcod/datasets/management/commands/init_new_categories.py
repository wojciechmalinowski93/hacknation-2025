import csv

from django_tqdm import BaseCommand

from mcod.categories.models import Category
from mcod.datasets.models import Dataset
from mcod.harvester.models import OLD_CATEGORY_TITLE_2_DCAT_CATEGORY_CODE


def load_csv(filename):
    with open(filename, newline="") as csv_file:
        reader = csv.reader(csv_file, delimiter=",", quotechar='"')
        rows = list(reader)
    header, *data = rows
    data = [dict(zip(header, row)) for row in data]
    return data


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str, help="Path to category conversion .csv file")
        parser.add_argument(
            "--empty-first",
            action="store_true",
            dest="empty_first",
            help=(
                "Remove all records from Dataset.categories.through table at the beginning. "
                "If not used, Dataset.categories will be cleared for each dataset, just before re-populating, "
                "which is slower but its progress can be measured."
            ),
        )

    def handle(self, *args, **options):
        empty_first = options["empty_first"]
        if empty_first:
            Dataset.categories.through.objects.all().delete()

        dataset_id_to_categories = {}
        data = load_csv(options["filepath"])
        for row in data:
            titles_raw = row["nowa_kategoria_zbioru_danych"]
            if not titles_raw:
                continue

            titles = [title.strip() for title in titles_raw.split("/")]
            categories = Category.objects.exclude(code="").filter(title__in=titles)

            assert len(categories) > 0
            dataset_id = int(row["id_zbioru_danych"])
            dataset_id_to_categories[dataset_id] = categories

        query = Dataset.raw.select_related("category").all()

        progress_bar = self.tqdm(desc="Populating dataset.categories", total=query.count())
        for dataset in query:
            progress_bar.update(1)
            if not empty_first:
                dataset.categories.clear()

            try:
                categories = dataset_id_to_categories[dataset.id]
            except KeyError:
                if not dataset.category:
                    continue
                dcat_category_code = OLD_CATEGORY_TITLE_2_DCAT_CATEGORY_CODE[dataset.category.title]
                dcat_category = Category.objects.get(code=dcat_category_code)
                categories = [dcat_category]

            dataset.categories.add(*categories)
