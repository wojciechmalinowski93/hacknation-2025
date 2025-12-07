import csv
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F, Q
from django_elasticsearch_dsl.registries import registry

from mcod import settings
from mcod.cms.models import FormPageSubmission
from mcod.cms.models.formpage import Formset
from mcod.core.api.search.tasks import update_document_task, update_with_related_task
from mcod.datasets.models import Dataset
from mcod.reports.models import Report
from mcod.resources.models import Resource, ResourceFile
from mcod.resources.tasks import (
    entrypoint_process_resource_file_validation_task,
    update_resource_has_table_has_map_task,
    update_resource_validation_results_task,
)

task_list = ["file_tasks", "data_tasks", "link_tasks"]

MEDIA_PATH = "/usr/src/mcod_backend/media/"


class Command(BaseCommand):
    help = "Various fixes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_const",
            dest="action",
            const="all",
            help="Run all fixes",
        )
        parser.add_argument(
            "--searchhistories",
            action="store_const",
            dest="action",
            const="searchhistories",
            help="Run fixes for search history",
        )
        parser.add_argument(
            "--datasets",
            action="store_const",
            dest="action",
            const="datasets",
            help="Run fixes for datasets",
        )
        parser.add_argument(
            "--resources",
            action="store_const",
            dest="action",
            const="resources",
            help="Run fixes for resources",
        )

        parser.add_argument(
            "--articlecategories",
            action="store_const",
            dest="action",
            const="articlecategories",
            help="Run fixes for article categories",
        )

        parser.add_argument(
            "--resourcedatadate",
            action="store_const",
            dest="action",
            const="resourcedatadate",
            help="Run fix that set data_date for resources with files",
        )

        parser.add_argument(
            "--migratefollowings",
            action="store_const",
            dest="action",
            const="migratefollowings",
            help="Copy following to subscriptions",
        )

        parser.add_argument(
            "--setverified",
            action="store_const",
            dest="action",
            const="setverified",
            help="Fix verfied for datasets and resources",
        )

        parser.add_argument("--pks", type=str, default="")

        parser.add_argument(
            "--resourcesformats",
            action="store_const",
            dest="action",
            const="resourcesformats",
            help="Run fixes for resources formats",
        )

        parser.add_argument(
            "--resources-links",
            action="store_const",
            dest="action",
            const="resources-links",
            help="Run fixes for resources links",
        )

        parser.add_argument(
            "--resources-validation-results",
            action="store_const",
            dest="action",
            const="resources-validation-results",
            help="Updates link_tasks_last_status, file_tasks_last_status, data_tasks_last_status of resources",
        )

        parser.add_argument(
            "--resources-has-table-has-map",
            action="store_const",
            dest="action",
            const="resources-has-table-has-map",
            help="Updates has_table and has_map attributes of resources",
        )

        parser.add_argument(
            "--submissions-to-new-format",
            action="store_const",
            dest="action",
            const="submissions-to-new-format",
            help="Converts FormDataSubmissions form_data field to new format",
        )

        parser.add_argument(
            "--submissions-to-old-format",
            action="store_const",
            dest="action",
            const="submissions-to-old-format",
            help="Converts FormDataSubmissions form_data field to old format",
        )

        parser.add_argument(
            "--submissions-formdata-save",
            action="store_const",
            dest="action",
            const="submissions-formdata-save",
            help="Saves FormDataSubmissions form_data field to file",
        )

        parser.add_argument(
            "--submissions-formdata-load",
            action="store_const",
            dest="action",
            const="submissions-formdata-load",
            help="Loads data from file into FormDataSubmissions form_data field",
        )

        parser.add_argument(
            "--reports-id-column",
            action="store_const",
            dest="action",
            const="reports-id-column",
            help="Changes column name in reports from ID to id",
        )

        parser.add_argument(
            "--resources-openness-score",
            action="store_const",
            dest="action",
            const="resources-openness-score",
            help="Recompute openness score for resources with fifth degree",
        )

        parser.add_argument(
            "--resources-links-protocol",
            action="store_const",
            dest="action",
            const="resources-links-protocol",
            help="Change resources links protocol to https based on protocol report",
        )

        parser.add_argument(
            "--resource-http-link",
            action="store_const",
            dest="action",
            const="resource-http-link",
            help="Change resources links protocol to https based on passed --pks parameter",
        )

        parser.add_argument(
            "-y, --yes",
            action="store_true",
            default=None,
            help="Continue without asking confirmation.",
            dest="yes",
        )
        parser.add_argument(
            "--history-other",
            action="store_true",
            default=False,
            help="Migrate history from history_other table.",
            dest="history_other",
        )
        parser.add_argument(
            "--table-name",
            dest="table_name",
            default=None,
            help="Migrates history only for specified table_name.",
        )

    def fix_resources(self):
        rs = Resource.objects.filter(dataset__is_removed=True)
        for r in rs:
            print(f"Resource ({r.id}) is set as removed because dataset ({r.dataset.id}) is removed")
            r.is_removed = True
            r.save()
        rs = Resource.objects.filter(dataset__is_permanently_removed=True)
        for r in rs:
            print(f"Resource ({r.id}) is set as permanently removed because dataset ({r.dataset.id}) is permanently removed")
            r.is_permanently_removed = True
            r.save()
        rs = Resource.objects.filter(dataset__status="draft")
        for r in rs:
            if r.status == "published":
                print(f"Status of resource ({r.id}) is change to draft because dataset ({r.dataset.id}) is draft")
                r.status = "draft"
                r.save()

    def fix_searchhistories(self):
        from mcod.searchhistories.models import SearchHistory

        print("Fixing search history")

        searchhistories = SearchHistory.objects.filter(query_sentence="*")

        for s in searchhistories:
            print(f"Removing search history id:{s.id} , url:{s.url}")
            s.delete()

        print("Done.")

    def fix_datasets(self):
        from django.db.models import CharField
        from django.db.models.functions import Length

        ds = Dataset.objects.filter(organization__is_removed=True)
        for d in ds:
            print(f"Dataset ({d.id}) is set as removed because organization ({d.organization.id}) is removed")
            d.is_removed = True
            d.save()
        ds = Dataset.objects.filter(organization__is_permanently_removed=True)
        for d in ds:
            print(
                f"Dataset ({d.id}) is set as permanently removed because "
                f"organization ({d.organization.id}) is permanently removed"
            )
            d.is_permanently_removed = True
            d.save()
        ds = Dataset.objects.filter(organization__status="draft")
        for d in ds:
            if d.status == "published":
                print(
                    f"Status of dataset ({d.id}) is changed to draft because organization ({d.organization.id}) is draft"
                )  # noqa
                d.status = "draft"
                d.save()

        print("Fixing slugs")

        CharField.register_lookup(Length, "length")
        datasets = Dataset.objects.filter(title__length__gt=90)
        for d in datasets:
            Dataset.objects.filter(pk=d.id).update(slug=d.get_unique_slug())

    def fix_resources_data_date(self):
        """
        Ustawia dla istniejących zasobów data_date na wartość z created
        """
        print("Przygotowuje się do ustawienia daty danych dla istniejących zasobów ...")
        resources_with_files = Resource.raw.all()
        print(f"Do zaktualizowania: {resources_with_files.count()}")
        resources_with_files.update(data_date=F("created"))
        print("Operacja zakończona")

    def fix_resources_validation_results(self):
        resources = Resource.raw.order_by("id")
        for obj in resources:
            update_resource_validation_results_task.s(obj.id).apply_async()

    def fix_resources_has_table_has_map(self):
        resources = Resource.raw.order_by("id")
        for obj in resources:
            update_resource_has_table_has_map_task.s(obj.id).apply_async()

    def verified_for_published_datasets(self):
        # region istniejace zbiory
        print("Rozpoczynam aktualizację dat verified dla istniejących zbiorów i ich zasobów: ")
        datasets = Dataset.objects.filter(status="published")
        datasets_count = datasets.count()
        i = 0
        for dataset in datasets:
            i += 1
            print(f"Ustawiam verified dla dataset id={dataset.id:6}\t{i}/{datasets_count}")
            resources = dataset.resources.filter(status="published")
            if resources:
                resources_dates = []
                for r in resources:
                    tasks_dates = []
                    for t in task_list:
                        tasks = getattr(r, t).all()
                        if tasks:
                            last_task = tasks.latest("date_done")
                            tasks_dates.append(last_task.date_done)

                    if tasks_dates:
                        verified_date = max(tasks_dates)
                    else:
                        verified_date = r.created

                    resources_dates.append(verified_date)
                    Resource.objects.filter(pk=r.id).update(verified=verified_date)

                Dataset.objects.filter(pk=dataset.id).update(verified=max(resources_dates))

            else:
                Dataset.objects.filter(pk=dataset.id).update(verified=dataset.created)
        print("Aktualizacja verified dla istniejących zbiorów i ich zasobów zakończona")
        print()

    def verified_for_removed_resources(self):
        # usunięte zasoby
        print("Aktualizacja verified dla usuniętych zasobów")
        resources = Resource.trash.all()
        resources_count = resources.count()
        i = 0
        for r in resources:
            i += 1
            print(f"Ustawiam verified dla zasobu id={r.id:6}\t{i}/{resources_count}")
            tasks_dates = []
            for t in task_list:
                tasks = getattr(r, t).all()
                if tasks:
                    last_task = tasks.latest("date_done")
                    tasks_dates.append(last_task.date_done)

            if tasks_dates:
                verified_date = max(tasks_dates)
            else:
                verified_date = r.created
            Resource.objects.filter(pk=r.id).update(verified=verified_date)
        print("Aktualizacja verified dla usuniętych zasobów zakończona")
        print()

    def verified_for_draft_resources(self):
        # szkice zasobów
        print("Aktualizacja verified dla szkiców zasobów")
        resources = Resource.objects.filter(status="draft")
        resources_count = resources.count()
        i = 0
        for r in resources:
            i += 1
            print(f"Ustawiam verified dla zasobu id={r.id:6}\t{i}/{resources_count}")
            tasks_dates = []
            for t in task_list:
                tasks = getattr(r, t).all()
                if tasks:
                    last_task = tasks.latest("date_done")
                    tasks_dates.append(last_task.date_done)

            if tasks_dates:
                verified_date = max(tasks_dates)
            else:
                verified_date = r.created
            Resource.objects.filter(pk=r.id).update(verified=verified_date)
        print("Aktualizacja verified dla szkiców zasobów zakończona")
        print()

    def verified_for_removed_datasets(self):
        # usunięte zbiory
        print("Aktualizacja verified dla usuniętych zbiorów")
        datasets = Dataset.trash.all()
        datasets_count = datasets.count()
        i = 0
        for dataset in datasets:
            i += 1
            print(f"Ustawiam verified dla dataset id={dataset.id:6}\t{i}/{datasets_count}")
            Dataset.objects.filter(pk=dataset.id).update(verified=dataset.created)
        print("Aktualizacja verified dla usniętych zbiorów zakończona")
        print()

    def verified_for_draft_datasets(self):
        # szkice zbiorów
        print("Aktualizacja verified dla szkiców zbiorów")
        datasets = Dataset.objects.filter(status="draft")
        datasets_count = datasets.count()
        i = 0
        for dataset in datasets:
            i += 1
            print(f"Ustawiam verified dla dataset id={dataset.id:6}\t{i}/{datasets_count}")
            Dataset.objects.filter(pk=dataset.id).update(verified=dataset.created)
        print("Aktualizacja verified dla szkiców zbiorów zakończona")

    def fix_verified(self):
        """
        Ustawia początkową wartośc verified
        """
        self.verified_for_published_datasets()
        self.verified_for_removed_resources()
        self.verified_for_draft_resources()
        self.verified_for_removed_datasets()
        self.verified_for_draft_datasets()

    def fix_followings(self):
        from mcod.users.models import UserFollowingDataset
        from mcod.watchers.models import ModelWatcher, Subscription

        for following in UserFollowingDataset.objects.all():
            watcher, _ = ModelWatcher.objects.get_or_create_from_instance(following.dataset)
            Subscription.objects.get_or_create(
                user=following.follower,
                watcher=watcher,
                name="dataset-%i" % following.dataset.id,
            )

    def fix_resources_links(self):
        self.stdout.write("Fixing of resources broken links - with . (dot) suffix.")
        counter = 0
        for obj in Resource.objects.filter(link__endswith="."):
            if obj.file_url.startswith(settings.API_URL) and obj.format:
                broken_link = obj.link
                fixed_link = f"{obj.link}{obj.format}"
                obj.link = fixed_link
                obj.save()
                counter += 1
                self.stdout.write(f"Resource with id: {obj.id} link changed from {broken_link} to {fixed_link}")
        self.stdout.write(f"Number of fixes: {counter}")

    def fix_resources_formats(self):
        print("Fixing invalid resource formats (with format='True')")

        res_ids = list(Resource.raw.filter(format="True").values_list("pk", flat=True))
        objs = ResourceFile.objects.filter(resource_id__in=res_ids)
        for obj in objs:
            print(f"Resource with invalid format found: id:{obj.resource_id} , format:{obj.resource.format}")
            entrypoint_process_resource_file_validation_task.s(obj.id, update_link=False).apply_async_on_commit()
        if objs.count():
            print("Done.")
        else:
            print("Resources with format='True' was not found.")

    def convert_form_page_submissions_to_new_format(self):
        print("Converting FormPageSubmissions form_data to NEW format.")
        for submission in FormPageSubmission.objects.all():
            print(f"FormPageSubmission's ({submission.id}) form_data is:\n{submission.form_data}")
            submission_modified = False
            formsets = Formset.objects.filter(page=submission.page)
            for question in formsets:
                question_id = str(question.ident)

                results = submission.form_data.get(question_id)
                if isinstance(results, list):
                    fields_ids = (field.id for field in question.fields)
                    submission.form_data[question_id] = dict(zip(fields_ids, results))
                    submission_modified = True

            if submission_modified:
                submission.save()
                print(f"Converted FormPageSubmission's ({submission.id}) form_data to:\n{submission.form_data}")

    def convert_form_page_submissions_to_old_format(self):
        print("Converting FormPageSubmissions form_data to OLD format.")
        for submission in FormPageSubmission.objects.all():
            print(f"FormPageSubmission's ({submission.id}) form_data is:\n{submission.form_data}")
            submission_modified = False
            formsets = Formset.objects.filter(page=submission.page)
            for question in formsets:
                question_id = str(question.ident)

                results = submission.form_data.get(question_id)
                if isinstance(results, dict):
                    new_results = [None] * len(question.fields)
                    field_id_to_index_map = {field.id: index for index, field in enumerate(question.fields)}

                    for field_id, result in results.items():
                        field_index = field_id_to_index_map[field_id]
                        new_results[field_index] = result

                    submission.form_data[question_id] = new_results
                    submission_modified = True

            if submission_modified:
                submission.save()
                print(f"Converted FormPageSubmission's ({submission.id}) form_data to:\n{submission.form_data}")

    def save_form_page_submissions_form_data_to_file(self):
        Path(MEDIA_PATH).mkdir(parents=True, exist_ok=True)
        filepath = os.path.join(MEDIA_PATH, "FormPageSubmissions.json")
        print(f"Saving FormPageSubmissions form_data to file:{filepath}")
        data = json.dumps({submission.id: submission.form_data for submission in FormPageSubmission.objects.all()})
        print(data)
        with open(filepath, "w") as file:
            file.write(data)

    def load_form_page_submissions_form_data_from_file(self):
        filepath = os.path.join(MEDIA_PATH, "FormPageSubmissions.json")
        print(f"Loading FormPageSubmissions form_data from file:{filepath}")
        with open(filepath) as file:
            data = json.load(file)

        for submission_id, form_data in data.items():
            submission = FormPageSubmission.objects.get(id=submission_id)
            print(f"FormPageSubmission's ({submission.id}) form_data before load:\n{submission.form_data}")
            submission.form_data = form_data
            submission.save()
            print(f"FormPageSubmission's ({submission.id}) form_data after load:\n{submission.form_data}")

    def fix_reports_id_column(self):
        def file_starts_with_text(path, text):
            with open(path) as file:
                return file.read(len(text)) == text

        def fix_id_column(path):
            with open(path, "rb") as file:
                content = file.read()
            assert content.startswith(b"ID;")
            content = b"id" + content[2:]
            with open(path, "wb") as file:
                file.write(content)

        for report in Report.objects.all():
            if not report.file:
                print(f"report {report.id} doesn't have file")
                continue

            filepath = report.file
            if filepath.startswith("/media/"):
                filepath = filepath[1:]

            fullpath = os.path.join(settings.ROOT_DIR, filepath)
            if not os.path.exists(fullpath):
                print(f"file {fullpath} doesn't exist")
                continue

            if not file_starts_with_text(fullpath, "ID;"):
                continue

            print(f"converting report {report.id} with file {report.file}")
            fix_id_column(filepath)

    def fix_resources_openness_score(self):
        res_to_update = []
        resources = Resource.objects.filter(
            Q(openness_score=5) | (Q(openness_score=3, jsonld_file__isnull=False) & ~Q(jsonld_file=""))
        )
        self.stdout.write("Found {} resources to recompute openness score".format(resources.count()))
        for resource in resources:
            try:
                self.stdout.write("Recomputing openness score for res with id {}".format(resource.pk))
                resource.openness_score, _ = resource.get_openness_score()
                res_to_update.append(resource)
            except Exception as err:
                self.stdout.write("Error while recomputing openness score for res with id {}: {}".format(resource.pk, err))
        self.stdout.write("Updating resources score in db and ES.")
        Resource.objects.bulk_update(res_to_update, ["openness_score"])
        for res in res_to_update:
            update_with_related_task.s("resources", "Resource", res.id).apply_async_on_commit()

    def _get_pks(self, **options):
        pks_str = options.get("pks")
        return (int(pk) for pk in pks_str.split(",") if pk) if pks_str else None

    def fix_resource_http_link(self, **options):
        pks = self._get_pks(**options)
        if not pks:
            raise CommandError("Passing of --pks parameter is required!")
        resources = Resource.objects.filter(pk__in=pks, link__startswith="http://")
        if resources:
            self.stdout.write(f"Number of resources to fix: {resources.count()}")
            answer = options["yes"]
            if answer is None:
                response = input("Are you sure you want to continue? [y/N]: ").lower().strip()
                answer = response == "y"
            if answer:
                edited_resources = []
                for obj in resources:
                    obj.link = obj.link.replace("http://", "https://")
                    edited_resources.append(obj)
                self.stdout.write("Attempting to update resources in db and ES.")
                Resource.objects.bulk_update(edited_resources, ["link"])
                for obj in resources:
                    update_document_task.s("resources", "resource", obj.id).apply_async()
                self.stdout.write(f"Updated {resources.count()} resources.")
            else:
                self.stdout.write("Aborted.")
        else:
            self.stdout.write("No resources found!")

    def fix_resources_links_protocol(self):
        self.stdout.write("Reading resource data from https_protocol_report")
        latest_report = None
        try:
            latest_report = Report.objects.filter(file__contains="http_protocol_resources").latest("created")
        except Report.DoesNotExist:
            self.stdout.write(
                "No http_protocol_resources report,"
                " you need to generate report first with: manage.py create_https_protocol_report."
            )
        if latest_report:
            file_path = latest_report.file
            self.stdout.write(f"Reading data from report: {file_path}")
            full_path = str(settings.ROOT_DIR) + file_path
            with open(full_path) as csvfile:
                report_data = csv.reader(csvfile, delimiter=",")
                next(report_data, None)
                resources_ids = [row[0] for row in report_data if "Wymagana poprawa" in row[2]]
            self.stdout.write(f"Found {len(resources_ids)} resources to update link protocol.")
            edited_resources = []
            resources = Resource.objects.filter(pk__in=resources_ids, link__contains="http://")
            edited_ids = []
            for res in resources:
                old_link = res.link
                res.link = old_link.replace("http://", "https://")
                edited_resources.append(res)
                edited_ids.append(res.pk)
            self.stdout.write("Attempting to update resources in db and ES.")
            Resource.objects.bulk_update(edited_resources, ["link"])
            docs = registry.get_documents((Resource,))
            for doc in docs:
                self.stdout.write(f"Updating document {doc} in ES")
                doc().update(Resource.objects.filter(pk__in=edited_ids))
            self.stdout.write(f"Updated {resources.count()} resources.")

    def handle(self, *args, **options):
        if not options["action"]:
            raise CommandError(
                "No action specified. Must be one of"
                " '--all','--searchhistories', '--resources', '--datasets', "
                "'--resourcedatadate', '--resourcesformats', '--migratefollowings', "
                "'--setverified', '--resources-links', '--resources-validation-results', "
                "'--resources-has-table-has-map', '--submissions-to-new-format', '--submissions-to-old-format', "
                "'--submissions-formdata-save', '--submissions-formdata-load', '--reports-id-column',"
                " '--resources-openness-score', '--resources-links-protocol', '--resource-http-link'."
            )
        action = options["action"]

        actions = {
            "datasets": self.fix_datasets,
            "resources-links": self.fix_resources_links,
            "migratefollowings": self.fix_followings,
            "resourcedatadate": self.fix_resources_data_date,
            "resources": self.fix_resources,
            "resourcesformats": self.fix_resources_formats,
            "searchhistories": self.fix_searchhistories,
            "setverified": self.fix_verified,
            "resources-validation-results": self.fix_resources_validation_results,
            "resources-has-table-has-map": self.fix_resources_has_table_has_map,
            "submissions-to-new-format": self.convert_form_page_submissions_to_new_format,
            "submissions-to-old-format": self.convert_form_page_submissions_to_old_format,
            "submissions-formdata-save": self.save_form_page_submissions_form_data_to_file,
            "submissions-formdata-load": self.load_form_page_submissions_form_data_from_file,
            "reports-id-column": self.fix_reports_id_column,
            "resources-openness-score": self.fix_resources_openness_score,
            "resources-links-protocol": self.fix_resources_links_protocol,
            "resource-http-link": self.fix_resource_http_link,
        }
        if action == "all":
            self.fix_searchhistories()
            self.fix_datasets()
            self.fix_resources()
        elif action == "resource-http-link":
            self.fix_resource_http_link(**options)
        elif action in actions.keys():
            actions[action]()
