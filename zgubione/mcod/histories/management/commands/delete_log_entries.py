from django.core.management.base import BaseCommand, CommandError

from mcod.core.registries import history_registry
from mcod.histories.documents import LogEntryDoc
from mcod.histories.models import LogEntry


class Command(BaseCommand):
    help = "Deletes all log entries from the database and from ES index."

    def add_arguments(self, parser):
        parser.add_argument(
            "-y, --yes",
            action="store_true",
            default=None,
            help="Continue without asking confirmation.",
            dest="yes",
        )
        parser.add_argument(
            "--table-name",
            dest="table_name",
            default=None,
            help="Deleted log entries only for specified table_name.",
        )

    def handle(self, *args, **options):
        answer = options["yes"]
        table_name = options["table_name"]
        table_names = history_registry.get_table_names()
        if table_name and table_name not in table_names:
            raise CommandError("Invalid table-name param. Should be one of: {}".format(", ".join(table_names)))
        query = {"content_type__model": table_name} if table_name else {}
        objs = LogEntry.objects.filter(**query)
        self.stdout.write("This action will clear {} log entries from the database and from ES.".format(objs.count()))
        if answer is None:
            response = input("Are you sure you want to continue? [y/N]: ").lower().strip()
            answer = response == "y"

        if answer:
            count, _ = objs.delete()
            self.stdout.write("Deleted %d objects." % count)
            if table_name:
                docs = LogEntryDoc().search().filter("term", table_name=table_name)
            else:
                docs = LogEntryDoc().search().filter()
            result = docs.delete()
            self.stdout.write("Deleted %d objects (ES)." % result.deleted)
        else:
            self.stdout.write("Aborted.")
