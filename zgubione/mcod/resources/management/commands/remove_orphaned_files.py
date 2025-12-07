from django.apps import apps
from django_tqdm import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--show-files-limit",
            type=int,
            default=10,
            help="Max. number of files displayed in console (default: 10)",
        )

    def handle(self, *args, **options):
        resource_model = apps.get_model("resources", "Resource")
        resources_files = resource_model.get_resources_files()
        counter = 0
        for file_path in resource_model.get_all_files():
            if file_path not in resources_files:
                new_file_path = resource_model.remove_orphaned_file(file_path)
                counter += 1
                self.stdout.write(f"{file_path} was moved to {new_file_path}")

        self.stdout.write(f"Done! {counter} files was removed.")
