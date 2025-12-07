from django.apps import apps
from django_tqdm import BaseCommand

from mcod.datasets.tasks import archive_resources_files


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--dataset_ids", type=str, default="")

    def handle(self, *args, **options):
        Dataset = apps.get_model("datasets", "Dataset")
        pks_str = options.get("dataset_ids")
        pks = pks_str.split(",") if pks_str else None
        if pks is None:
            pks = Dataset.objects.filter(status="published").values_list("pk", flat=True)
        self.stdout.write(f"Starting archives creation for {len(pks)} datasets.")
        for pk in pks:
            archive_resources_files.s(dataset_id=pk).apply_async()
        self.stdout.write("Queued celery tasks for all specified datasets.")
