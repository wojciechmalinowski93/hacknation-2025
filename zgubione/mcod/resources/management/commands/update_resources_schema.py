from django.apps import apps
from django.core.management import BaseCommand
from django.core.management.base import CommandError
from tqdm import tqdm

from mcod.resources.tasks import process_resource_file_data_task

description = """
Po zmianie sposobu wyświetlania i indeksowania date i datetime stare zasoby mogą mieć problem ze zmianą typu.
Wynika to z tego, że mają one utworzony schemat a w nim dla typów date i datetime ustawiony format 'default'.
Nowe zasoby mają ustawiony dla tych typów format 'any'.

Te polecenie dla wybranych zasobów zmieni schemat zamieniając 'default' na 'any'.

Zostawiono tu też możliwość ustawienia innego formatu.

Dla wybranego zasobu zmiana ta powinna być możliwa też z poziomu panelu admina.
Przy zmianie schematu - jeśli kolumna jest typu date lub datetime i jej format to 'default', to zostanie on zmieniony na 'any'.
Dotyczy to tylko zasóbów z widokiem tabelarycznym. Nie ma zastosowania dla geo."""  # noqa


def update_schema(schema, dateformat, datetimeformat):
    for field in schema["fields"]:
        if field["type"] == "date":
            field["format"] = dateformat
        elif field["type"] == "datetime":
            field["format"] = datetimeformat
        elif field["type"] == "time":
            field["format"] = datetimeformat
    return schema


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.description = description
        parser.add_argument("--pks", type=str)
        parser.add_argument(
            "--async",
            action="store_const",
            dest="async",
            const=True,
            help="Use celery task",
        )
        parser.add_argument(
            "--dateformat",
            type=str,
            default="any",
            help="Schema datetime format - 'default' or 'any'. Now by default 'any' will be choosen",
        )
        parser.add_argument(
            "--datetimeformat",
            type=str,
            default="any",
            help="Schema datetime format - 'default' or 'any'. Now by default 'any' will be choosen",
        )
        parser.add_argument(
            "--timeformat",
            type=str,
            default="any",
            help="Schema datetime format - 'default' or 'any'. Now by default 'any' will be choosen",
        )

    def handle(self, *args, **options):
        if not options["pks"]:
            raise CommandError("No resource id specified. You must provide at least one.")
        Resource = apps.get_model("resources", "Resource")
        async_ = options.get("async") or False
        date_format = options["dateformat"]
        datetime_format = options["datetimeformat"]

        queryset = Resource.objects.with_tabular_data(pks=(int(pk) for pk in options["pks"].split(",")))
        self.stdout.write("The action will update schema for {} resource(s)".format(queryset.count()))
        for obj in tqdm(queryset, desc="Indexing"):
            if obj.tabular_data_schema:
                tabular_data_schema = update_schema(obj.tabular_data_schema, date_format, datetime_format)
                Resource.objects.filter(pk=obj.id).update(tabular_data_schema=tabular_data_schema)
            if async_:
                process_resource_file_data_task.delay(obj.pk)
            else:
                process_resource_file_data_task.apply(args=(obj.pk,), throw=True)
        self.stdout.write("Done.")
