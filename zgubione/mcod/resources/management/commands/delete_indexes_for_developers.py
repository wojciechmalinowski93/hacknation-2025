from typing import Optional

from django.core.management import BaseCommand
from django.db.models import QuerySet

from mcod.organizations.models import Organization
from mcod.resources.tasks import delete_es_resource_tabular_data_indexes_for_organization


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't delete developers' resources indexes - print out Resources that would have been touched",
        )
        parser.add_argument(
            "--first-org-pk",
            type=int,
            default=0,
            help="Index resource with PK >= `first-org-pk`",
        )
        parser.add_argument(
            "--last-org-pk",
            type=int,
            default=None,
            help="Index resource with PK <= `last-org-pk`",
        )

    def _get_developers(self, first_org_pk: int, last_org_pk: Optional[int]) -> QuerySet:
        if last_org_pk:
            if first_org_pk > last_org_pk:
                self.stdout.write("last-org-pk must be greater or equal first-org-pk")
                raise ValueError("last-org-pk must be greater or equal first-org-pk")
            developers = Organization.raw.filter(
                institution_type=Organization.INSTITUTION_TYPE_DEVELOPER, id__gte=first_org_pk, id__lte=last_org_pk
            ).order_by("id")
        else:
            developers = Organization.raw.filter(
                institution_type=Organization.INSTITUTION_TYPE_DEVELOPER, id__gte=first_org_pk
            ).order_by("id")
        return developers

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        first_org_pk: int = options["first_org_pk"]
        last_org_pk: Optional[int] = options["last_org_pk"]

        developers: QuerySet[Organization] = self._get_developers(first_org_pk, last_org_pk)

        self.stdout.write(f"Indexes belonging to {len(developers)} organizations will be processed by celery tasks.")

        for developer in developers:
            if dry_run:
                self.stdout.write(f"Dry run delete tabular data index for organization id={developer.id}")
            else:
                self.stdout.write(
                    f"Start task -  delete_es_resource_tabular_data_indexes_for_organization for organization id={developer.id}"
                )
                delete_es_resource_tabular_data_indexes_for_organization.delay(developer.id)
