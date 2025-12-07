from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils.six.moves import input

from mcod.lib.rdf.store import get_sparql_store


def boolean_input(question, default=None):
    result = input("%s " % question)
    if not result and default is not None:
        return default
    while result not in ["y", "n"]:
        result = input("Please answer y (yes) or n (no): ")
    return result[0].lower() == "y"


class Command(BaseCommand):
    help = "Adds, updates and removes data from RDF database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create",
            action="store_const",
            dest="action",
            const="create",
            help="Create the data in RDF database",
        )
        parser.add_argument(
            "--delete",
            action="store_const",
            dest="action",
            const="delete",
            help="Delete the RDF database",
        )
        parser.add_argument(
            "--rebuild",
            action="store_const",
            dest="action",
            const="rebuild",
            help="Delete the RDF database and then recreate and populate it",
        )

        parser.add_argument(
            "--init_catalog_metadata",
            action="store_const",
            dest="action",
            const="init_catalog_metadata",
            help="Initialize main catalog metadata",
        )

        parser.add_argument(
            "--reinit_catalog_metadata",
            action="store_const",
            dest="action",
            const="reinit_catalog_metadata",
            help="Delete and create main catalog metadata.",
        )

        parser.add_argument(
            "--delete_catalog_metadata",
            action="store_const",
            dest="action",
            const="delete_catalog_metadata",
            help="Delete main catalog metadata",
        )

        parser.add_argument(
            "--models",
            metavar="app[.model]",
            type=str,
            nargs="*",
            help="Specify the model or app to be updated in rdf database",
        )
        parser.add_argument("--dataset_ids", type=str, default="")
        parser.add_argument("--resource_ids", type=str, default="")
        parser.add_argument("-f", "--force", dest="force", action="store_true", help="force execution")

    def handle(self, *args, **options):
        if not options["action"]:
            raise CommandError(
                "No action specified. Must be one of"
                " '--create', '--delete', '--rebuild', '--init_catalog_metadata',"
                " '--delete_catalog_metadata' or '--reinit_catalog_metadata' ."
            )

        action = options["action"]
        self.sparql_store = get_sparql_store()

        if action in [
            "create",
            "delete",
            "rebuild",
            "init_catalog_metadata",
            "delete_catalog_metadata",
            "reinit_catalog_metadata",
        ]:
            getattr(self, f"_{action}")(options)
        else:
            raise CommandError(
                "Invalid action. Must be one of"
                " '--create', '--delete', '--rebuild', '--init_catalog_metadata',"
                " '--delete_catalog_metadata' or '--reinit_catalog_metadata' ."
            )

    def _get_models(self, args):
        """
        Get Models from registry that match the --models args
        """
        all_models = [apps.get_model(name) for name in ["datasets.Dataset", "resources.Resource"]]
        if args:
            models = []
            for arg in args:
                arg = arg.lower()
                match_found = False

                for model in all_models:
                    if model._meta.app_label == arg:
                        models.append(model)
                        match_found = True
                    elif (
                        "{}.{}".format(
                            model._meta.app_label.lower(),
                            model._meta.model_name.lower(),
                        )
                        == arg
                    ):
                        models.append(model)
                        match_found = True

                if not match_found:
                    raise CommandError("No model or app named {}".format(arg))
        else:
            models = all_models

        return set(models)

    def _get_objects(self, model_name, options):
        models = self._get_models(options["models"])
        model = apps.get_model(model_name)
        ids = [x for x in options[f"{model._meta.model_name}_ids"].split(",") if x]
        query = {"id__in": ids} if ids else {}
        return model.objects.filter(**query).order_by("id") if model in models else model.objects.none()

    def _create(self, options, is_confirmed=False):
        is_confirmed = (
            options["force"] or is_confirmed or boolean_input("Are you sure you want to push data into Graph Store? [y/n]:")
        )
        if is_confirmed:
            datasets = self._get_objects("datasets.Dataset", options)
            for obj in datasets:
                self.stdout.write(f'Push into Graph Store dataset: id {obj.id}, "{obj}"')
                self.sparql_store.add_object(obj)

            resources = self._get_objects("resources.Resource", options)
            for obj in resources:
                self.stdout.write(f'Push into Graph Store resource: id {obj.id}, "{obj}" in RDF database...')
                self.sparql_store.add_object(obj)
            if not ("resource_ids" in options or "dataset_ids" in options):
                self._init_catalog_metadata(options)
        else:
            self.stdout.write("Aborted")

    def _delete(self, options, is_confirmed=False):
        is_confirmed = (
            options["force"] or is_confirmed or boolean_input("Are you sure you want to delete existing Graph Store? [y/n]:")
        )
        if is_confirmed:
            self.stdout.write("Delete RDF database...", ending="")
            self.sparql_store.update("DROP ALL")
            self.stdout.write(self.style.SUCCESS("OK"))
        else:
            self.stdout.write("Aborted")

    def _rebuild(self, options):
        try:
            is_confirmed = options["force"] or boolean_input("Are you sure you want to rebuild Graph Store? [y/n]:")
            if is_confirmed:
                self._delete(options, is_confirmed)
                self._create(options, is_confirmed)
            else:
                self.stdout.write("Aborted")
        except KeyboardInterrupt:
            raise CommandError("\nExecution of command interrupted by user!")

    def _init_catalog_metadata(self, options):
        dataset = apps.get_model("datasets.Dataset")
        resource = apps.get_model("resources.Resource")
        catalog_modified = resource.objects.all().aggregate(Max("modified"))["modified__max"]
        datasets_urls = [ds.frontend_absolute_url for ds in dataset.objects.filter(status="published")]
        context = {"dataset_refs": datasets_urls, "catalog_modified": catalog_modified}
        self.stdout.write("Initializing catalog metadata.")
        self.sparql_store.add_catalog_metadata(context)

    def _delete_catalog_metadata(self, options):
        self.sparql_store.delete_catalog_metadata()

    def _reinit_catalog_metadata(self, options):
        self._delete_catalog_metadata(options)
        self._init_catalog_metadata(options)
