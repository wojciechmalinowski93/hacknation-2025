import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import QuerySet
from tqdm import tqdm

from mcod.resources.management.common import validate_dir_writable, validate_pks
from mcod.resources.models import Resource
from mcod.resources.score_computation import OpennessScoreValue

RecalculatedResourceRecord = Tuple[int, OpennessScoreValue, OpennessScoreValue]  # pk, score before, score after
ErrorRecord = Tuple[int, str]  # pk, error message


@dataclass
class OpennessScoreRecalculationResults:
    resources_up_to_date: List[RecalculatedResourceRecord]
    resources_to_update: List[RecalculatedResourceRecord]
    errors: List[ErrorRecord]

    def __bool__(self) -> bool:
        return bool(self.resources_up_to_date or self.resources_to_update or self.errors)


class Command(BaseCommand):
    """
    Django management command for recalculating the openness score of Resources.

    This command performs the following actions:
    - Recalculates the openness score for selected Resources.
      By default, it processes all Resources, but you can limit the scope
      by providing a list of specific Resource IDs (PKs).
    - Generates a CSV report containing:
        - Resource ID
        - Openness score BEFORE recalculation
        - Openness score AFTER recalculation
        - Whether the score has changed ("TAK" / "NIE")

    Additionally:
    - If any errors occur during processing, separate error report will be created.
    - The command supports two modes of operation:
        1. **Update mode**: Updates openness scores in the database for Resources whose score has changed.
        2. **Dry-run mode** (default): Only generates reports; no database changes are made.

    Use dry-run mode when you want to preview changes without modifying the data.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--pks",
            type=str,
            default="",
            help="primary keys of resource to recalculate openness score for. "
            "Without flag all resources will be recalculated.",
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
            help="set flag -u or --update to update resources with new openness score."
            " Without the flag command will only simulate the process and generate report(s).",
        )
        parser.add_argument(
            "--report-dir",
            type=str,
            default=".",
            help="default report folder name",
        )

    def handle(self, *args, **options):

        self._validate_command_arguments(**options)

        process_start_msg = "Start resources Openness Score recalculation."
        if not options["update"]:
            process_start_msg += " [DRY-RUN: only reports will be generated (no DB update)]"
        self.stdout.write(process_start_msg)

        # Step 1: Calculate openness score for all / given resources
        os_recalculation_results: OpennessScoreRecalculationResults = self._recalculate_openness_score(**options)
        if not os_recalculation_results:
            self.stdout.write("No resources to recalculate in given list / range.")
            return

        # Step 2: Create .csv report containing info about all processed resources
        self._create_success_csv_report(
            res_to_update=os_recalculation_results.resources_to_update,
            res_up_to_date=os_recalculation_results.resources_up_to_date,
            **options,
        )

        # Step 3: If any error occurred, create .csv report with details
        if os_recalculation_results.errors:
            self._create_error_csv_report(os_recalculation_results.errors, **options)

        # Step 4 (optional): Update DB with new openness score values
        update_operation: bool = options["update"]
        if update_operation:
            self._update_resources_openness_score(os_recalculation_results.resources_to_update)

    def _validate_command_arguments(self, **options) -> None:
        pks: str = options.get("pks")
        first_pk: Optional[int] = options.get("first_pk")
        last_pk: Optional[int] = options.get("last_pk")
        report_dir: Path = self._get_report_dir(**options)

        validate_pks(pks, first_pk, last_pk)
        validate_dir_writable(report_dir)

    @staticmethod
    def _get_pks(**options) -> Optional[List[str]]:
        pks_str: Optional[str] = options.get("pks")
        return [pk for pk in pks_str.split(",") if pk] if pks_str else None

    @staticmethod
    def _get_pks_range(**options) -> Tuple[Optional[int], Optional[int]]:
        first_pk: Optional[int] = options.get("first_pk")
        last_pk: Optional[int] = options.get("last_pk")
        return first_pk, last_pk

    def _get_resources_to_recalculate_qs(self, **options) -> QuerySet:
        # Get all not removed resources QuerySet
        all_resources_qs: QuerySet = Resource.objects.only("pk", "openness_score")
        # Filter qs if pks were passed
        pks = self._get_pks(**options)
        if pks:
            all_resources_qs = all_resources_qs.filter(pk__in=pks)
            return all_resources_qs

        # Filter qs by pks range
        first_pk: Optional[int]
        last_pk: Optional[int]
        first_pk, last_pk = self._get_pks_range(**options)
        if first_pk is not None:
            all_resources_qs = all_resources_qs.filter(pk__gte=first_pk)
        if last_pk is not None:
            all_resources_qs = all_resources_qs.filter(pk__lte=last_pk)

        return all_resources_qs

    @staticmethod
    def _get_report_dir(**options) -> Path:
        return Path(options["report_dir"]).absolute()

    def _recalculate_openness_score(self, **options) -> OpennessScoreRecalculationResults:
        resource_qs: QuerySet = self._get_resources_to_recalculate_qs(**options)

        data_with_no_changes: List[RecalculatedResourceRecord] = []
        data_to_update: List[RecalculatedResourceRecord] = []
        errors_data: List[ErrorRecord] = []

        pbar = tqdm(resource_qs.iterator(), total=resource_qs.count())
        for resource in pbar:
            try:
                score: OpennessScoreValue = resource.openness_score
                recalculated_score: OpennessScoreValue

                logging.disable(logging.CRITICAL)  # disable logs from .get_openness_score func
                recalculated_score, _ = resource.get_openness_score()
                logging.disable(logging.NOTSET)

                record = (resource.pk, score, recalculated_score)
                if score == recalculated_score:
                    data_with_no_changes.append(record)
                else:
                    data_to_update.append(record)

            except Exception as e:
                errors_data.append((resource.pk, str(e)))

            finally:
                pbar.set_description(
                    f"OK: {len(data_with_no_changes)}, " f"NEEDS UPDATE: {len(data_to_update)}, " f"ERRORS: {len(errors_data)} |"
                )

        return OpennessScoreRecalculationResults(
            resources_to_update=data_to_update,
            resources_up_to_date=data_with_no_changes,
            errors=errors_data,
        )

    def _create_success_csv_report(
        self,
        res_to_update: List[RecalculatedResourceRecord],
        res_up_to_date: List[RecalculatedResourceRecord],
        **options,
    ) -> None:
        column_names = (
            "Id zasobu",
            "Poziom otwartości danych PRZED",
            "Poziom otwartości danych PO",
        )
        # Create DF with up-to-date resources
        df_with_res_up_to_date = pd.DataFrame(data=res_up_to_date, columns=column_names)
        df_with_res_up_to_date["Czy nastąpiła zmiana?"] = "NIE"

        # Create DF with resources which need update
        df_with_res_to_update = pd.DataFrame(data=res_to_update, columns=column_names)
        df_with_res_to_update["Czy nastąpiła zmiana?"] = "TAK"

        # Join tables
        df = pd.concat([df_with_res_up_to_date, df_with_res_to_update])

        # Save DF to .csv file
        report_dir: Path = self._get_report_dir(**options)
        now = datetime.datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
        report_filename = f"aktualizacja poziomów otwartości zasobów - {now}.csv"
        df.to_csv(report_dir / report_filename, index=False)

        self.stdout.write(self.style.SUCCESS("Openness Score report successfully generated."))

    def _create_error_csv_report(self, data: List[ErrorRecord], **options) -> None:
        # Create DF with errors
        df = pd.DataFrame(data, columns=["Resource Id", "Error Reason"])

        # Save DF with errors to .csv file
        now = datetime.datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
        report_filename = f"błędy podczas aktualizacji poziomów otwartości zasobów - {now}.csv"
        report_dir: Path = self._get_report_dir(**options)
        df.to_csv(report_dir / report_filename, index=False)

        self.stdout.write(self.style.SUCCESS("Openness Score errors report successfully generated."))

    @staticmethod
    def _update_es_and_rdf_db_for_resources(resources: List[Resource]) -> None:
        for resource in resources:
            resource.update_es_and_rdf_db()

    def _update_resources_openness_score(self, res_to_update: List[RecalculatedResourceRecord]) -> None:
        if not res_to_update:
            self.stdout.write("No resources to update.")
            return

        res_to_update_count: int = len(res_to_update)
        self.stdout.write(f"Updating {res_to_update_count} resources.")

        chunk_size = 1000
        try:
            with transaction.atomic():
                for i in range(0, res_to_update_count, chunk_size):
                    chunk = res_to_update[i : i + chunk_size]
                    resources_to_update: List[Resource] = [
                        Resource(pk=pk, openness_score=new_score) for pk, _, new_score in chunk
                    ]
                    Resource.objects.bulk_update(resources_to_update, ["openness_score"])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to update openness score for resources: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Openness score updated for {res_to_update_count} resources."))
            self.stdout.write("Run update ElasticSearch and RDF db's tasks for all updated resource.")
            self._update_es_and_rdf_db_for_resources(resources_to_update)
