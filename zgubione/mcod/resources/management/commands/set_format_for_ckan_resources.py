import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

import pandas as pd
from celery import group
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q, QuerySet
from tqdm import tqdm

from mcod.resources.management.common import validate_dir_writable, validate_pks
from mcod.resources.models import Resource
from mcod.resources.tasks import get_ckan_resource_format_from_url_task


@dataclass
class ResourceToUpdateData:
    pk: int
    format: str


class Command(BaseCommand):
    """
    Django management command to set format of CKAN Resources.

    This command performs the following actions:
    - Gets format for selected CKAN Resources.
      By default, it processes all Resources, but you can limit the scope
      by providing a list of specific Resource IDs (PKs).
    - Generates a CSV report containing:
        - Resource ID
        - Url
        - Format

    Additionally:
    - If any errors occur during processing, separate error report will be created.
    - The command supports two modes of operation:
        1. **Update mode**: Updates resources in the database for Resources whose format has changed.
        2. **Dry-run mode** (default): Only generates reports; no database changes are made.

    Use dry-run mode when you want to preview changes without modifying the data.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--pks",
            type=str,
            default="",
            help="primary keys (comma separated) of CKAN resources to get format for.",
        )
        parser.add_argument(
            "--first-pk",
            type=int,
            default=None,
            help="Index resource with PK >= `first-pk`",
        )
        parser.add_argument(
            "--last-pk",
            type=int,
            default=None,
            help="Index resource with PK <= `last-pk`",
        )
        parser.add_argument(
            "-u",
            "--update",
            action="store_true",
            help="set flag -u or --update to update CKAN resources with new format."
            " Without the flag command will only simulate the process and generate report(s).",
        )
        parser.add_argument(
            "--report-dir",
            type=str,
            default=".",
            help="default report folder name",
        )

    def handle(self, *args, **options) -> None:  # noqa: C901

        # Get report directory and validate it's writable
        report_dir: str = options.get("report_dir")
        report_dir: Path = Path(report_dir).absolute()
        validate_dir_writable(report_dir)

        # Get primary keys options and validate them
        pks: str = options.get("pks")
        first_pk: Optional[int] = options.get("first_pk")
        last_pk: Optional[int] = options.get("last_pk")
        validate_pks(pks_str=pks, first_pk=first_pk, last_pk=last_pk)

        # Get CKAN resources from given range lacking format
        resources_qs: QuerySet = self._get_ckan_resources_qs(
            first_pk=first_pk,
            last_pk=last_pk,
            pks=[pk for pk in pks.split(",")] if pks else None,
        )
        resources_qs = resources_qs.only("pk")

        total: int = resources_qs.count()
        if total == 0:
            self.stdout.write("No CKAN resources to update.")
            return
        self.stdout.write(f"{total} CKAN resources need format update.")

        # Create and run celery tasks group to get CKAN resources formats
        tasks_group = group(get_ckan_resource_format_from_url_task.s(res.pk) for res in resources_qs)
        self.stdout.write("Starting CKAN resources format processing.")
        group_result = tasks_group.apply_async()

        try:
            # Display tasks processing progress bar
            with tqdm(total=total) as pbar:
                last_done: int = 0

                group_ready: bool = False
                while not group_ready:
                    group_ready = group_result.ready()
                    ready_results = [result for result in group_result.results if result.ready()]
                    done: int = len(ready_results)
                    success: int = sum(result.get()[0] for result in ready_results)
                    errors: int = done - success

                    pbar.update(done - last_done)
                    last_done = done
                    pbar.set_postfix(SUCCESS=success, FAILED=errors)
                    time.sleep(1)

        except KeyboardInterrupt:
            self.stdout.write("Interrupted. Terminating tasks.")
            group_result.revoke(teminate=True)

        # Aggregate tasks results into two list (success and errors)
        data = []
        err_data = []
        for r in group_result.results:
            result: List = r.get()
            success, pk, url, resource_format, error_msg = tuple(result)
            if success:
                data.append((pk, url, resource_format))
            else:
                err_data.append((pk, url, error_msg))

        self.stdout.write("Finished processing CKAN resources format update.")

        # Create success .csv report if any success occurred
        update: bool = options.get("update")
        now: str = datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
        if data:
            self.stdout.write("Generating success report.")

            success_report_filename = (
                f"raport aktualizacji formatu zasobów CKAN - {now}.csv"
                if update
                else f"raport kwalifikacji zasobów CKAN do aktualizacji formatu - {now}.csv"
            )
            self._save_data_to_csv(
                data=data,
                columns=["Id zasobu", "Url", "Format"],
                directory=report_dir,
                filename=success_report_filename,
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully generated report: {success_report_filename}"))

        # Create errors .csv if any exception occurred
        if err_data:
            self.stdout.write("Generating errors report.")
            errors_report_filename = f"raport błędów podczas aktualizacji formatu zasobów CKAN - {now}.csv"
            self._save_data_to_csv(
                data=err_data,
                columns=["Id zasobu", "Url", "Opis błędu"],
                directory=report_dir,
                filename=errors_report_filename,
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully generated report: {errors_report_filename}"))

        # Update CKAN resources format in DB (optional)
        if update:
            self.stdout.write("Updating CKAN resources with new format.")
            res_to_update_data: List[ResourceToUpdateData] = [
                ResourceToUpdateData(pk=pk, format=format_) for pk, _, format_ in data
            ]

            if not res_to_update_data:
                self.stdout.write("No resources to update.")
                return

            try:
                self._update_resources(res_to_update_data, chunk_size=100)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Błąd podczas próby aktualizacji zasobów CKAN: {str(exc)}"))

    @staticmethod
    def _get_ckan_resources_qs(
        first_pk: Optional[int] = None,
        last_pk: Optional[int] = None,
        pks: Optional[List[Union[int, str]]] = None,
    ) -> QuerySet:
        qs: QuerySet = Resource.objects.filter(
            dataset__source__source_type="ckan",
        ).filter(
            Q(format__isnull=True) | Q(format="")
        )  # only CKAN resources without format should be returned

        if pks:
            qs = qs.filter(pk__in=pks)
        if first_pk:
            qs = qs.filter(pk__gte=first_pk)
        if last_pk:
            qs = qs.filter(pk__lte=last_pk)

        return qs

    @staticmethod
    def _save_data_to_csv(
        data: List[Any],
        columns: List[str],
        directory: Path,
        filename: str,
    ) -> None:
        df = pd.DataFrame(data, columns=columns)
        df.to_csv(directory / filename, index=False)

    @staticmethod
    def _update_resources(
        resources_data: List[ResourceToUpdateData],
        chunk_size: Optional[int] = None,
    ) -> None:
        with transaction.atomic():
            res_to_update: List[Resource] = [Resource(pk=res.pk, format=res.format) for res in resources_data]
            Resource.objects.bulk_update(
                res_to_update,
                fields=("format",),
                batch_size=chunk_size,
            )
