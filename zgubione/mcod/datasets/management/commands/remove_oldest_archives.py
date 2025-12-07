import os

from django_tqdm import BaseCommand

from mcod.core.storages import get_storage


class Command(BaseCommand):

    def handle(self, *args, **options):

        archives_storage = get_storage("datasets_archives")
        archive_dirs = [x[0] for x in os.walk(archives_storage.location) if x[0] != archives_storage.location]
        for directory in archive_dirs:
            non_symlinks = [
                os.path.join(directory, f) for f in os.listdir(directory) if not os.path.islink(os.path.join(directory, f))
            ]
            if len(non_symlinks) > 1:
                files_with_dt = sorted(
                    [(file_path, os.path.getmtime(file_path)) for file_path in non_symlinks],
                    key=lambda x: x[1],
                )
                for f in files_with_dt[1:]:
                    os.remove(f[0])
