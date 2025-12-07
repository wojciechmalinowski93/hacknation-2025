from django.apps import apps
from django.core.management import BaseCommand
from django.core.management.base import CommandError
from tqdm import tqdm

from mcod.resources.tasks import process_resource_file_data_task


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--pks", type=str)
        parser.add_argument(
            "--async",
            action="store_const",
            dest="async",
            const=True,
            help="Use celery task",
        )

    def handle(self, *args, **options):
        if not options["pks"]:
            raise CommandError("No resource id specified. You must provide at least one.")
        Resource = apps.get_model("resources", "Resource")
        async_ = options.get("async") or False
        queryset = Resource.objects.with_tabular_data(pks=(int(pk) for pk in options["pks"].split(",")))
        self.stdout.write("The action will reindex files for {} resource(s)".format(queryset.count()))
        for obj in tqdm(queryset, desc="Indexing"):
            if async_:
                process_resource_file_data_task.delay(obj.pk)
            else:
                process_resource_file_data_task.apply(
                    args=(obj.pk,),
                    throw=True,
                )

        self.stdout.write("Done.")
