from django.core.management import BaseCommand
from tqdm import tqdm

from mcod.applications.models import Application, ApplicationProposal


class Command(BaseCommand):
    help = "Migrates all existing Application instances into Showcase instances (with related objects)."

    def add_arguments(self, parser):
        parser.add_argument("--application_ids", type=str)
        parser.add_argument("--application_proposal_ids", type=str)
        parser.add_argument(
            "-y, --yes",
            action="store_true",
            default=None,
            help="Continue without asking confirmation.",
            dest="yes",
        )
        parser.add_argument(
            "--app",
            type=str,
            default="110,309,484,632,1216,1221,1223,1224,1225,1232,1233,1235,1237,1241,1242,1243,1244,1246,1247,1252,"
            "1256,1258,1259,1263",
            help='comma separated list of application ids to migrate as showcase with category: "app".',
        )
        parser.add_argument(
            "--www",
            type=str,
            default="282,586,676,751,783,915,923,954,959,960,979,1104,1215,1234,1248,1250,1253,1260,1261,1262,1264",
            help='comma separated list of application ids to migrate as showcase with category: "www".',
        )
        parser.add_argument(
            "--other",
            type=str,
            default="1239,1245",
            help='comma separated list of application ids to migrate as showcase with category: "other".',
        )

    def handle(self, *args, **options):  # noqa: C901
        app = [int(x) for x in options["app"].split(",") if x]
        www = [int(x) for x in options["www"].split(",") if x]
        other = [int(x) for x in options["other"].split(",") if x]
        answer = options["yes"]

        a_query = {}
        if options["application_ids"]:
            a_query["pk__in"] = (int(x) for x in options["application_ids"].split(",") if x)
        a_qs = Application.raw.filter(**a_query)

        ap_query = {"application": None}
        if options["application_proposal_ids"]:
            ap_query["pk__in"] = (int(x) for x in options["application_proposal_ids"].split(",") if x)
        ap_qs = ApplicationProposal.raw.filter(**ap_query)

        self.stdout.write("This action will migrate:")
        self.stdout.write("- {} applications to showcases (with related proposals)".format(a_qs.count()))
        self.stdout.write("- {} applications proposals (w/o related application) to showcase proposals".format(ap_qs.count()))
        if answer is None:
            response = input("Are you sure you want to continue? [y/N]: ").lower().strip()
            answer = response == "y"

        if answer:
            exceptions = []
            for obj in tqdm(a_qs, desc="Applications"):
                category = None
                if obj.id in app:
                    category = "app"
                elif obj.id in www:
                    category = "www"
                elif obj.id in other:
                    category = "other"
                try:
                    obj.migrate_to_showcase(category)
                except Exception as exc:
                    exceptions.append(f"Application (id:{obj.id}): {exc}")
            for obj in tqdm(ap_qs, desc="Application Proposals"):
                try:
                    obj.migrate_to_showcase_proposal()
                except Exception as exc:
                    exceptions.append(f"Application Proposal (id:{obj.id}): {exc}")
            for exc in exceptions:
                self.stdout.write(self.style.ERROR(exc))
        else:
            self.stdout.write("Aborted.")
