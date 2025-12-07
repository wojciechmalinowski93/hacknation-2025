import csv
import json
import logging
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from dateutil import relativedelta, rrule
from django.conf import settings
from django_tqdm import BaseCommand

from mcod.counters.models import ResourceDownloadCounter, ResourceViewCounter
from mcod.reports.models import SummaryDailyReport
from mcod.resources.models import Resource

logger = logging.getLogger("mcod")


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--log_paths", nargs="+", help="Path to api logs containing request data.")

        parser.add_argument(
            "--published_history_file_path",
            nargs="+",
            help="Path to file with publish history of all resources.",
        )

    def handle(self, *args, **options):
        res_data = {}
        for log_path in options["log_paths"]:
            self.read_from_log_history(log_path, res_data)
        self.read_from_report_files(res_data)
        self.remove_invalid_ids(res_data)
        res_q = Resource.orig.values("pk", "published_at")
        res_published_dates = {str(r["pk"]): r["published_at"].date() for r in res_q}

        rvc_count_views = 0
        rdc_count_downloads = 0
        with open(options["published_history_file_path"][0], "r") as json_file:
            history_published_dates = json.load(json_file)
        for res_id, res_details in res_data.items():
            if Resource.orig.filter(pk=res_id).exists():
                logger.debug("Started computing counters for resource with id: ", res_id)
                rvc_list = []
                rdc_list = []
                try:
                    start_date = self.get_start_date(res_published_dates, history_published_dates, res_id)
                except IndexError:
                    continue
                dates_list = list(res_details.keys())
                dates_list.sort()
                end_date = dates_list[-1]
                sorted_entries = []
                for timestamp in rrule.rrule(freq=rrule.DAILY, dtstart=start_date, until=end_date):
                    dt = timestamp.date()
                    init_val = self.get_init_val(dt, start_date, res_details)
                    self.initialize_start_date_values(dt, start_date, res_details)
                    sorted_entries.append(
                        dict(
                            date=dt,
                            **res_details.get(
                                dt,
                                {
                                    "summary_views": init_val,
                                    "summary_downloads": init_val,
                                    "views": init_val,
                                    "downloads": init_val,
                                },
                            ),
                        )
                    )
                data_gaps = self.find_summary_data_gaps(sorted_entries)
                self.fill_summary_data_gaps(sorted_entries, data_gaps)
                for i in range(len(sorted_entries) - 1, -1, -1):
                    views_count = self.get_count_value(sorted_entries, i, "summary_views")
                    downloads_count = self.get_count_value(sorted_entries, i, "summary_downloads")
                    if views_count > 0:
                        rvc_list.append(
                            ResourceViewCounter(
                                timestamp=sorted_entries[i]["date"],
                                resource_id=res_id,
                                count=views_count,
                            )
                        )
                        rvc_count_views += views_count
                    if downloads_count > 0:
                        rdc_list.append(
                            ResourceDownloadCounter(
                                timestamp=sorted_entries[i]["date"],
                                resource_id=res_id,
                                count=downloads_count,
                            )
                        )
                        rdc_count_downloads += downloads_count
                logger.debug("Creating counters in db for resource with id: ", res_id)
                ResourceViewCounter.objects.bulk_create(rvc_list)
                ResourceDownloadCounter.objects.bulk_create(rdc_list)
        logger.debug("Total created views count:", rvc_count_views)
        logger.debug("Total created downloads count:", rdc_count_downloads)

    def get_start_date(
        self,
        res_published_dates,
        history_published_dates,
        res_id,
    ):
        fallback_published_date = res_published_dates.get(res_id, datetime(2019, 5, 31).date())
        resource_published_dates = history_published_dates.get(res_id, {fallback_published_date.strftime("%Y-%m-%d"): 1})
        all_history_dates = [
            (datetime.strptime(publish_date, "%Y-%m-%d").date(), publish_value)
            for publish_date, publish_value in resource_published_dates.items()
        ]
        all_history_dates.sort(key=lambda x: x[0])
        publish_dates_lst = [history_entry[0] for history_entry in all_history_dates if history_entry[1] == 1]
        return publish_dates_lst[0]

    def get_init_val(self, dt, start_date, res_details):
        return 0 if dt == start_date and dt not in res_details else None

    def initialize_start_date_values(self, dt, start_date, res_details):
        if dt == start_date and dt in res_details and res_details[dt]["summary_views"] is None:
            res_details[dt]["summary_views"] = res_details[dt]["views"] if res_details[dt]["views"] is not None else 0
            res_details[dt]["summary_downloads"] = res_details[dt]["downloads"] if res_details[dt]["downloads"] is not None else 0

    def remove_invalid_ids(self, res_data):
        invalid_ids = []
        for res_id in res_data.keys():
            try:
                int(res_id)
            except ValueError:
                invalid_ids.append(res_id)
        for inv_id in invalid_ids:
            res_data.pop(inv_id)

    def read_from_report_files(self, res_data):
        directory_path = settings.ROOT_DIR
        files = list(SummaryDailyReport.objects.all().values_list("file", flat=True).order_by("file"))
        for file_path in files:
            logger.debug("Reading data from daily report:", file_path)
            file_name = file_path.split("/")[-1]
            name_parts = file_name.split("_")
            file_date = datetime(int(name_parts[3]), int(name_parts[4]), int(name_parts[5])).date()
            counters_date = file_date - relativedelta.relativedelta(days=1)
            full_path = f"{directory_path}{file_path}" if file_path.startswith("/") else f"{directory_path}/{file_path}"
            with open(full_path) as csvfile:
                report_reader = csv.reader(csvfile, delimiter=",")
                headers = next(report_reader, None)
                if "formaty_po_konwersji" in headers:
                    views_index = 10
                    downloads_index = 11
                    check_data_range = range(9, 13)
                else:
                    views_index = 9
                    downloads_index = 10
                    check_data_range = range(8, 12)
                for row in report_reader:
                    if self.has_valid_row_data(row, check_data_range):
                        res_id = row[0]
                        views_count = int(row[views_index])
                        downloads_count = int(row[downloads_index])
                        try:
                            res_details = res_data[res_id].get(counters_date, {"views": None, "downloads": None})
                            res_details["summary_views"] = views_count
                            res_details["summary_downloads"] = downloads_count
                            res_data[res_id][counters_date] = res_details
                        except KeyError:
                            res_data[res_id] = {
                                counters_date: {
                                    "summary_views": views_count,
                                    "summary_downloads": downloads_count,
                                    "views": None,
                                    "downloads": None,
                                }
                            }

    def has_valid_row_data(self, row, check_data_range):
        try:
            return bool([int(row[i]) for i in check_data_range])
        except (IndexError, ValueError):
            return False

    def read_from_log_history(self, log_path, res_data):
        logger.debug("Reading data from log file:", log_path)
        overall_views_count = 0
        overall_downloads_count = 0
        views_regex = (
            r"(\[(?P<date>\d\d\/\w+\/\d\d\d\d)(\:\d\d){3}\s\+\d{4}\]\s\"GET(?!.*\b(?:media)\b)[^\"]+"
            r"/resources/(?P<res_id>\d+)(,[-a-zA-Z0-9_]+)?/?\sHTTP/\d\.\d\"\s[^4]\d\d)"
        )
        downloads_regex = (
            r"\[(?P<date>\d\d\/\w+\/\d\d\d\d)(\:\d\d){3}\s\+\d{4}\]\s\"GET[^\"]+"
            r"/resources/(?P<res_id>\d+)(,[-a-zA-Z0-9_]+)?/(file|csv|jsonld)/?\sHTTP/\d\.\d\"\s3\d\d"
        )
        max_size = 1024 * 1024 * 512
        found_lines = 0
        found_views_lines = 0
        with open(log_path, "r") as log_file:

            def read_chunks():
                return log_file.read(max_size)

            for chunk in iter(read_chunks, ""):
                views_matches = re.findall(views_regex, chunk)
                downloads_matches = re.findall(downloads_regex, chunk)
                found_lines += len(downloads_matches)
                found_views_lines += len(views_matches)
                for match in downloads_matches:
                    match_date = datetime.strptime(match[0], "%d/%b/%Y").date()
                    try:
                        res_details = res_data[match[2]].setdefault(
                            match_date,
                            {
                                "downloads": 0,
                                "views": 0,
                                "summary_views": None,
                                "summary_downloads": None,
                            },
                        )
                        res_details["downloads"] += 1
                        res_data[match[2]][match_date] = res_details
                        overall_downloads_count += 1
                    except KeyError:
                        res_data[match[2]] = {
                            match_date: {
                                "downloads": 1,
                                "views": 0,
                                "summary_views": None,
                                "summary_downloads": None,
                            }
                        }
                for match in views_matches:
                    match_date = datetime.strptime(match[1], "%d/%b/%Y").date()
                    try:
                        res_details = res_data[match[3]].setdefault(
                            match_date,
                            {
                                "downloads": 0,
                                "views": 0,
                                "summary_views": None,
                                "summary_downloads": None,
                            },
                        )
                        res_details["views"] += 1
                        res_data[match[3]][match_date] = res_details
                        overall_views_count += 1
                    except KeyError:
                        res_data[match[3]] = {
                            match_date: {
                                "downloads": 0,
                                "views": 1,
                                "summary_views": None,
                                "summary_downloads": None,
                            }
                        }
        return (
            overall_views_count,
            overall_downloads_count,
            found_lines,
            found_views_lines,
        )

    def find_summary_data_gaps(self, sorted_entries):
        data_gaps = []
        gap_start = 0
        found_gap = False
        for entry_index, entry_details in enumerate(sorted_entries):
            if entry_details["summary_views"] is None and not found_gap:
                found_gap = True
            elif entry_details["summary_views"] is not None and not found_gap:
                gap_start = entry_index
            elif entry_details["summary_views"] is not None and found_gap:
                found_gap = False
                data_gaps.append((gap_start, entry_index))
                gap_start = entry_index
            if found_gap and entry_index == len(sorted_entries) - 1:
                data_gaps.append((gap_start, entry_index))
        return data_gaps

    def fill_summary_data_gaps(self, sorted_entries, data_gaps):
        for gap in data_gaps:
            gap_start = gap[0] + 1
            sliced_entries = sorted_entries[gap_start : gap[1] + 1]
            gap_start_views_count = sorted_entries[gap[0]]["summary_views"]
            gap_end_views_count = sliced_entries[-1]["summary_views"]
            gap_start_downloads_count = sorted_entries[gap[0]]["summary_downloads"]
            gap_end_downloads_count = sliced_entries[-1]["summary_downloads"]
            if gap_end_views_count is not None and gap_start_views_count is not None:
                self.compute_gap_valid_count_values(
                    gap_start_views_count,
                    gap_end_views_count,
                    "views",
                    sliced_entries,
                    sorted_entries,
                    gap_start,
                )
                self.compute_gap_valid_count_values(
                    gap_start_downloads_count,
                    gap_end_downloads_count,
                    "downloads",
                    sliced_entries,
                    sorted_entries,
                    gap_start,
                )
                for i in range(gap[1] - 1, gap_start - 1, -1):
                    new_summary_view = sorted_entries[i + 1]["summary_views"] - sorted_entries[i + 1]["views"]
                    sorted_entries[i]["summary_views"] = (
                        new_summary_view if new_summary_view > 0 else sorted_entries[i + 1]["summary_views"]
                    )
                    new_summary_downloads = sorted_entries[i + 1]["summary_downloads"] - sorted_entries[i + 1]["downloads"]
                    sorted_entries[i]["summary_downloads"] = (
                        new_summary_downloads if new_summary_downloads > 0 else sorted_entries[i + 1]["summary_downloads"]
                    )
            elif gap_end_views_count is None and gap_start_views_count is not None:
                for i in range(gap_start, gap[1] + 1):
                    current_views = sorted_entries[i]["views"] if sorted_entries[i]["views"] is not None else 0
                    current_downloads = sorted_entries[i]["downloads"] if sorted_entries[i]["downloads"] is not None else 0
                    sorted_entries[i]["summary_views"] = sorted_entries[i - 1]["summary_views"] + current_views
                    sorted_entries[i]["summary_downloads"] = sorted_entries[i - 1]["summary_downloads"] + current_downloads

    def compute_gap_valid_count_values(
        self,
        gap_start_count,
        gap_end_count,
        values_type,
        sliced_entries,
        sorted_entries,
        gap,
    ):
        count_of_entries = len(sliced_entries)
        slice_values = [0 if entry[values_type] is None else entry[values_type] for entry in sliced_entries]
        slice_values_sum = sum(slice_values)
        if slice_values_sum == 0:
            slice_profile = [1 / len(sliced_entries) for _ in range(count_of_entries)]
        else:
            slice_profile = [slice_value / slice_values_sum for slice_value in slice_values]
        gap_end_count = max(gap_end_count, gap_start_count)
        slice_summary_diff = gap_end_count - gap_start_count
        if slice_summary_diff != slice_values_sum:
            result_values = self.compute_profiled_values(slice_summary_diff, slice_profile)
        else:
            result_values = slice_values
        for index, new_value in enumerate(result_values):
            sorted_entries[gap + index][values_type] = new_value

    def compute_profiled_values(self, slice_data_diff, slice_data_profile):
        profiled_result_values = [
            Decimal(str(profile_val * slice_data_diff)).quantize(Decimal("1."), rounding=ROUND_HALF_UP)
            for profile_val in slice_data_profile
        ]
        profiled_sum = sum(profiled_result_values)
        profiled_diff = slice_data_diff - profiled_sum
        if profiled_diff > 0:
            profiled_result_values[-1] += profiled_diff
        elif profiled_diff < 0:
            abs_diff = abs(profiled_diff)
            new_profiled_values = []
            for profiled_val in profiled_result_values:
                lower_val = min(profiled_val, abs_diff)
                changed_profiled_val = profiled_val - lower_val
                abs_diff -= lower_val
                new_profiled_values.append(changed_profiled_val)
            profiled_result_values = new_profiled_values
        return profiled_result_values

    def get_count_value(self, sorted_entries, i, count_type):
        if i > 0:
            count_value = sorted_entries[i][count_type] - sorted_entries[i - 1][count_type]
        else:
            if len(sorted_entries) > 1:
                count_value = (
                    sorted_entries[i][count_type] if sorted_entries[i + 1][count_type] - sorted_entries[i][count_type] > 0 else 0
                )
            else:
                count_value = sorted_entries[i][count_type]
        return count_value
