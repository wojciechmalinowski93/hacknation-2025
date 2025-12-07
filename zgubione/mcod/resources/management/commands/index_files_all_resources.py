import traceback
from typing import List, Optional, Tuple

from django.core.management import BaseCommand
from django.db.models import Max, QuerySet
from tqdm import tqdm

from mcod.celeryapp import app
from mcod.resources.models import Resource
from mcod.resources.tasks import process_resource_file_data_task

MAX_ERRORS = 100  # stop after this number of errors


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--first-pk",
            type=int,
            default=0,
            help="Index resource with PK >= `first-pk`",
        )
        parser.add_argument(
            "--last-pk",
            type=int,
            default=None,
            help="Index resource with PK <= `last-pk`",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="async_",
            help="Schedule tasks to Celery",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't reindex - print out Resources that would have been touched",
        )
        parser.add_argument(
            "--rate-limit",
            type=str,
            help="Rate_limit (int, str) - the rate limit as tasks/sec or a rate limit string (`100/m`, etc.)",
        )

    def handle(self, *args, **options):
        first_pk: int = options["first_pk"]
        last_pk: Optional[int] = options["last_pk"]
        async_: bool = options["async_"]
        dry_run: bool = options["dry_run"]
        rate_limit: str = options["rate_limit"]
        self._prepare(async_, rate_limit)

        errors: List[Tuple[Resource, Exception]] = []

        last_pk: int = self._get_highest_pk(first_pk, last_pk)
        resources: QuerySet = self._get_queryset(first_pk, last_pk)
        total: int = resources.count()
        self.stdout.write(f"The action will validate and reindex resource data files for {total} resource(s)")
        for resource in tqdm(resources):
            resource: Resource
            self.stdout.write(f"index_files_all_resources processing {resource.pk}, {resource.slug}")
            if dry_run:
                self.stdout.write("DRY RUN - skipping")
                continue
            if not resource.is_data_processable:
                self.stdout.write(f"Resource with id={resource.id} not processable - skipping")
                continue

            if async_:
                process_resource_file_data_task.delay(resource.pk)
                continue
            try:
                process_resource_file_data_task.apply(
                    args=(resource.pk,),
                    throw=True,
                )
            except Exception as e:
                # For 'eager' runs we can get meaningful errors here
                errors.append((resource, e))
                if len(errors) > MAX_ERRORS:
                    break
        self._finalise(errors, async_)

    def _prepare(self, async_, rate_limit):
        if not async_:
            self.stderr.write("Warning - tasks will run synchronously. Use --async to schedule and forget")
        if async_ and rate_limit:
            self.stderr.write(f"Using {rate_limit=}")
            app.control.rate_limit("mcod.resources.tasks.process_resource_file_data_task", rate_limit)

    def _finalise(self, errors: List[Tuple[Resource, Exception]], async_: bool) -> None:
        if async_:
            self.stdout.write("Done scheduling tasks. Monitor progress and errors in Celery logs")
        if errors:
            self.stdout.write("Reindexing for the following Resources failed")
        for resource, exception in errors:
            resource: Resource
            self.stdout.write(f"Resource failed {resource.pk} {resource.title}")
            traceback.print_exc(file=self.stderr)

    def _get_queryset(self, first_pk: int, last_pk: int) -> QuerySet:
        """
        Returns Queryset on Resources of just primary keys
        """
        queryset = Resource.objects.with_tabular_data().order_by("pk").filter(pk__gte=first_pk, pk__lte=last_pk).only("pk")
        return queryset

    def _get_highest_pk(self, first_pk: int, last_pk: Optional[int]) -> int:
        max_pk: int = Resource.objects.with_tabular_data().aggregate(Max("pk")).get("pk__max") or 0
        if last_pk:
            if last_pk > max_pk:
                self.stdout.write(f"{last_pk=} is higher than anything in the database")
        else:
            last_pk = max_pk
        if first_pk > last_pk:
            self.stdout.write(f"No resources in range {first_pk}..{last_pk} found")
            raise ValueError
        return last_pk
