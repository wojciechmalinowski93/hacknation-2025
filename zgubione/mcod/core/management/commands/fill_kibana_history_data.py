import json
import os
from collections import OrderedDict, defaultdict
from datetime import date, datetime

import requests
from dateutil import relativedelta, rrule
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from mcod.counters.models import ResourceDownloadCounter, ResourceViewCounter
from mcod.histories.models import LogEntry
from mcod.resources.models import Resource


class Command(BaseCommand):

    media_size_result_file = "media_resources_size.json"
    res_count_result_file = "published_resources_count_history.json"
    downloads_count_result_file = "downloads_history.json"
    views_count_result_file = "views_history.json"
    resource_availability_file = "resource_availability_history.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_const",
            dest="data_type",
            const="all",
            help="Recreate all data",
        )
        parser.add_argument(
            "--create_intermediate_files",
            type=str,
            dest="data_type",
            help="Create intermediate json files with historical data, can have one of following values:"
            " resource_counters, media_size, published_resources_count",
        )
        parser.add_argument(
            "file_path",
            type=str,
            help="Path, where intermediate files will be created and stored",
        )
        parser.add_argument(
            "--log_path",
            type=str,
            dest="log_path",
            help="Path, where kibana_statistics.log file is located",
        )

    def handle(self, *args, **options):
        data_type = options["data_type"]
        self.file_path = options["file_path"]
        methods_dict = {
            "resource_counters": "create_counters_files",
            "media_size": "create_media_size_file",
            "published_resources_count": "create_pub_res_file",
        }
        self.zabbix_api_url = settings.ZABBIX_API["url"]
        if data_type == "all":
            if not options["log_path"]:
                raise CommandError("--log_path argument is required when recreating all data in log.")
            self.create_kibana_history_log(options["log_path"])
        else:
            if data_type not in methods_dict:
                raise CommandError(
                    "create_intermediate_files must have one of"
                    " the following values: {}".format(", ".join(methods_dict.keys()))
                )
            getattr(self, methods_dict[data_type])()

    def create_kibana_history_log(self, logs_path):
        orig_log_file = "kibana_statistics.log"
        new_log_file_name = "kibana_statistics_old.log"
        self.create_media_size_file()
        self.create_pub_res_file()
        self.create_counters_files()
        self.stdout.write("Updating kibana_statistics.log file with historical data.")
        data_sources = {
            self.res_count_result_file: "resources_of_public_organizations",
            self.media_size_result_file: "size_of_documents_of_public_organizations",
            self.downloads_count_result_file: "downloads_of_documents_of_public_organizations",
            self.views_count_result_file: "views_of_documents_of_public_organizations",
        }
        with open(logs_path + orig_log_file, "r") as base_file:
            line = base_file.readline()
            line_parts = line.split(" ")
            last_date_str = line_parts[0]
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        main_file_data = {}
        for source_file, source_log_key in data_sources.items():
            with open(self.file_path + source_file, "r") as infile:
                files_data = json.loads(infile.read())
            for dt, date_count in files_data.items():
                try:
                    main_file_data[dt].append((source_log_key, date_count))
                except KeyError:
                    main_file_data[dt] = [(source_log_key, date_count)]
        sorted_dates = sorted([datetime.strptime(date, "%Y-%m-%d").date() for date in main_file_data.keys()])
        sorted_main_file_data = OrderedDict(
            [(date.strftime("%Y-%m-%d"), main_file_data[date.strftime("%Y-%m-%d")]) for date in sorted_dates if date < last_date]
        )
        log_data = []
        for dt, date_details in sorted_main_file_data.items():
            for log_details in date_details:
                log_data.append(f"{dt} 06:00:39,152 kibana-statistics INFO     {log_details[0]} {log_details[1]}\n")
        with open(logs_path + orig_log_file, "r") as base_file:
            base_log_lines = base_file.readlines()
        merged_lines = log_data + base_log_lines
        os.rename(logs_path + orig_log_file, logs_path + new_log_file_name)
        with open(logs_path + orig_log_file, "w") as outfile:
            outfile.writelines(merged_lines)

    def aggregate_counter(self, downloads_counter, views_counter, pub_history_data):
        downloads_counter_history = {}
        views_counter_history = {}
        dates_with_pub_resources = {}
        for res_id, res_pub_periods in pub_history_data.items():
            res_periods = []
            period_start = None
            for dt, pub_status in res_pub_periods.items():
                if pub_status == 1 and not period_start:
                    period_start = dt
                if pub_status == 0 and period_start:
                    res_periods.append((period_start, dt))
                    period_start = None
            if period_start:
                res_periods.append((period_start,))
            self.assign_res_to_published_period(res_id, res_periods, dates_with_pub_resources)
        self.stdout.write("Computing dates count")
        for dt, resources in dates_with_pub_resources.items():
            dt_date = dt.date()
            download_res_count = (
                downloads_counter.filter(resource_id__in=resources, timestamp__lte=dt_date).aggregate(all_count=Sum("count"))[
                    "all_count"
                ]
                or 0
            )
            views_res_count = (
                views_counter.filter(resource_id__in=resources, timestamp__lte=dt_date).aggregate(all_count=Sum("count"))[
                    "all_count"
                ]
                or 0
            )
            downloads_counter_history[dt_date] = download_res_count
            views_counter_history[dt_date] = views_res_count
        return downloads_counter_history, views_counter_history

    def assign_res_to_published_period(self, res_id, res_periods, dates_with_pub_resources):
        for period in res_periods:
            if len(period) == 2:
                start_date = datetime.strptime(period[0], "%Y-%m-%d")
                end_date = datetime.strptime(period[1], "%Y-%m-%d")
            else:
                start_date = datetime.strptime(period[0], "%Y-%m-%d")
                end_date = datetime.now()
            for timestamp in rrule.rrule(freq=rrule.DAILY, dtstart=start_date, until=end_date):
                try:
                    dates_with_pub_resources[timestamp].append(res_id)
                except KeyError:
                    dates_with_pub_resources[timestamp] = [res_id]

    def create_counters_files(self):
        self.stdout.write("Creating downloads and views data history json file.")
        try:
            with open(self.file_path + self.resource_availability_file, "r") as infile:
                pub_history_data = json.load(infile)
        except IOError:
            self.create_res_availability_history()
            with open(self.file_path + self.resource_availability_file, "r") as infile:
                pub_history_data = json.load(infile)
        all_downloads = ResourceDownloadCounter.objects.all()
        all_views = ResourceViewCounter.objects.all()
        downloads_history, views_history = self.aggregate_counter(all_downloads, all_views, pub_history_data)
        self.create_counter_data_file(downloads_history, self.downloads_count_result_file)
        self.create_counter_data_file(views_history, self.views_count_result_file)

    def create_counter_data_file(self, counter_history, counter_file_name):
        counter_history_dates = sorted([date for date in counter_history.keys()])
        sorted_counter_history = OrderedDict(
            [(date.strftime("%Y-%m-%d"), counter_history[date]) for date in counter_history_dates]
        )
        self.save_json_result_file(counter_file_name, sorted_counter_history)

    def datetime_to_str(self, timestamp):
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def auth(self, headers):

        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {
                    "user": settings.ZABBIX_API["user"],
                    "password": settings.ZABBIX_API["password"],
                },
                "id": 1,
                "auth": None,
            }
        )
        response = requests.get(self.zabbix_api_url, headers=headers, data=data)
        return response

    def get_media(self, limit, time_till=None, time_from=None):
        headers = {
            "Content-Type": "application/json-rpc",
        }
        auth_response = self.auth(headers).json()
        TOKEN = auth_response["result"]
        ID = auth_response["id"]
        params = {
            "output": "extend",
            "history": 0,
            "itemids": "31685",
            "sortfield": "clock",
            "sortorder": "ASC",
            "limit": limit,
        }
        if time_till:
            params["time_till"] = time_till

        if time_from:
            params["time_from"] = time_from

        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "history.get",
                "params": params,
                "auth": TOKEN,
                "id": ID,
            }
        )
        response = requests.get(self.zabbix_api_url, headers=headers, data=data)
        return response

    def save_zabbix_api_results(self):
        result = {}
        time_from = None
        while True:
            media = self.get_media(limit=10000, time_from=time_from)

            rows = media.json()["result"]
            if not rows:
                break

            newest = rows[-1]
            time_from = int(newest["clock"]) + 1

            for row in rows:
                datetime_str = self.datetime_to_str(int(row["clock"]))
                date_str, time_str = datetime_str.split()
                result[date_str] = int(float(row["value"]))

        with open(self.file_path + self.zabbix_api_file_name, "w") as file:
            file.write(json.dumps(result, indent=4))

    def merge_zabbix_data(self):
        with open(self.file_path + "zabbix_trends.json") as outfile:
            trends_data = json.loads(outfile.read())
        with open(self.file_path + self.zabbix_api_file_name) as outfile:
            api_data = json.loads(outfile.read())
        merged_data = {**trends_data, **api_data}
        self.save_json_result_file(self.media_size_result_file, merged_data)

    @property
    def zabbix_api_file_name(self):
        today_str = date.today().strftime("%Y_%m_%d")
        file_name = f"zabbix_api_{today_str}.json"
        return file_name

    def save_json_result_file(self, file_name, data):
        with open(self.file_path + file_name, "w") as file:
            file.write(json.dumps(data, indent=4))

    def create_media_size_file(self):
        self.stdout.write("Creating media size history data json file.")
        self.save_zabbix_api_results()
        self.merge_zabbix_data()

    def gen_initial_json(self, init_file_name):
        d = LogEntry.objects.resources_availability_as_dict()
        self.save_json_result_file(init_file_name, d)

    def process_statuses_dict(self, date_to_status):
        updated = {}
        last_status = 0
        for date_str, status in sorted(date_to_status.items()):
            if status == -1:
                status = 0
            if status != last_status:
                updated[date_str] = status
                last_status = status
        return updated

    def post_process_json(self, init_file_name):
        with open(self.file_path + init_file_name) as file:
            input_data = json.loads(file.read())

        empty_keys = []
        for resource_id, date_to_status in sorted(input_data.items()):
            date_to_status = self.process_statuses_dict(date_to_status)
            input_data[resource_id] = date_to_status
            if not date_to_status:
                empty_keys.append(resource_id)

        for resource_id in empty_keys:
            del input_data[resource_id]

        self.save_json_result_file(self.resource_availability_file, input_data)

    def create_res_availability_history(self):
        init_file_name = "resource_availability_history_initial.json"
        if not os.path.isfile(self.file_path + self.resource_availability_file):
            self.stdout.write("Creating resource_availability_history.json")
            self.gen_initial_json(init_file_name)
            self.post_process_json(init_file_name)
        else:
            self.stdout.write("resource_availability_history.json exists, skipping creation.")

    def create_pub_res_file(self):
        self.stdout.write("Creating public resources count history data json file.")
        self.create_res_availability_history()
        self.create_count_history()

    def create_count_history(self):
        with open(self.file_path + self.resource_availability_file) as file:
            history = json.loads(file.read())
        d = defaultdict(int)
        for i, resource in enumerate(Resource.orig.iterator()):
            resource_id = str(resource.id)
            if resource_id not in history:
                continue
            resource_history = history[resource_id]
            last_date_str = None
            for date_str, status in resource_history.items():
                if last_date_str:
                    assert date_str > last_date_str
                    last_date_str = date_str
                d[date_str] += 1 if status == 1 else -1
        new_d = {}
        dt_d = {
            (datetime.strptime(date, "%Y-%m-%d").date() + relativedelta.relativedelta(days=1)).strftime("%Y-%m-%d"): date_data
            for date, date_data in d.items()
        }
        for key in sorted(dt_d):
            new_d[key] = dt_d[key]
        result = {}
        counter = 0
        for key, value in new_d.items():
            counter += value
            result[key] = counter
        self.save_json_result_file(self.res_count_result_file, result)
