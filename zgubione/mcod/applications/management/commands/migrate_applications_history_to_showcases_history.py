from django.core.management import BaseCommand
from tqdm import tqdm

from mcod.applications.models import Application, ApplicationProposal
from mcod.histories.models import LogEntry
from mcod.showcases.models import Showcase, ShowcaseProposal


class Command(BaseCommand):
    help = "Migrates application history to showcase history (as from applications to showcases post migration task)."

    def add_arguments(self, parser):
        parser.add_argument("--showcase_ids", type=str)
        parser.add_argument("--showcase_proposal_ids", type=str)
        parser.add_argument(
            "-y, --yes",
            action="store_true",
            default=None,
            help="Continue without asking confirmation.",
            dest="yes",
        )

    def handle(self, *args, **options):
        s_query = {}
        if options["showcase_ids"]:
            s_query["pk__in"] = (int(x) for x in options["showcase_ids"].split(",") if x)
        s_qs = Showcase.raw.filter(**s_query)

        sp_query = {}
        if options["showcase_proposal_ids"]:
            sp_query["pk__in"] = (int(x) for x in options["showcase_proposal_ids"].split(",") if x)
        sp_qs = ShowcaseProposal.raw.filter(**sp_query)

        self.stdout.write(
            "The action will upgrade history for {} showcases and {} showcase proposals".format(s_qs.count(), sp_qs.count())
        )
        answer = options["yes"]
        if answer is None:
            response = input("Are you sure you want to continue? [y/N]: ").lower().strip()
            answer = response == "y"
        if answer:
            for obj in tqdm(s_qs, desc="Showcases"):
                from_obj = Application.raw.filter(id=obj.id).first()
                if from_obj:
                    LogEntry.migrate_history(from_obj, obj)
            for obj in tqdm(sp_qs, desc="Showcase Proposals"):
                from_obj = ApplicationProposal.raw.filter(id=obj.id).first()
                if from_obj:
                    LogEntry.migrate_history(from_obj, obj)
        else:
            self.stdout.write("Aborted.")
