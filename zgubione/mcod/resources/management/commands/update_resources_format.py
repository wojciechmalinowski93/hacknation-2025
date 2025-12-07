from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q

from mcod.resources.models import ResourceFile
from mcod.resources.tasks import update_resource_with_archive_format


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--pks", type=str, dest="pks")

    def handle(self, *args, **options):
        pk_opt = options.get("pks")
        if pk_opt:
            q = Q(resource_id__in=(int(pk) for pk in options["pks"].split(",")))
        else:
            q = None
            for ext in settings.ARCHIVE_EXTENSIONS:
                if q is None:
                    q = Q(file__endswith=ext)
                else:
                    q |= Q(file__endswith=ext)
        q &= Q(is_main=True, resource__is_removed=False)
        res_files = list(
            ResourceFile.objects.filter(q)
            .exclude(format__in=settings.ARCHIVE_EXTENSIONS)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        self.stdout.write(f"Found {len(res_files)} resource files to update format.")
        for rf_id in res_files:
            update_resource_with_archive_format.s(rf_id).apply_async()
