import urllib3
from django.apps import apps
from django.conf import settings
from django_tqdm import BaseCommand

urllib3.disable_warnings()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--where", type=str)
        parser.add_argument(
            "--async",
            action="store_const",
            dest="async",
            const=True,
            help="Validate using celery tasks",
        )

    def handle(self, *args, **options):
        asnc = options.get("async") or False
        if not asnc:
            settings.CELERY_TASK_ALWAYS_EAGER = True
        Resource = apps.get_model("resources", "Resource")

        query = Resource.objects.all()
        if options["where"]:
            query = query.extra(where=[options["where"]])

        progress_bar = self.tqdm(desc="Validating", total=query.count())
        for resource in query:
            progress_bar.update(1)
            resource.revalidate(update_verification_date=False)
        print("Done.")
