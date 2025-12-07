import os
import shutil

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        call_command("migrate")
        init_media_path = os.path.join(settings.DATA_DIR, "initial_data", "media")
        res_src_path = os.path.join(init_media_path, "resources", "20220323")
        res_dst_path = os.path.join(settings.RESOURCES_MEDIA_ROOT, "20220323")
        ds_src_path = os.path.join(init_media_path, "datasets", "archives", "dataset_4210")
        ds_dst_path = os.path.join(settings.DATASETS_MEDIA_ROOT, "archives", "dataset_4210")
        self.copy_files(res_src_path, res_dst_path)
        self.copy_files(ds_src_path, ds_dst_path)
        call_command("loaddata", "basic_data.json")

    def copy_files(self, src_path, dst_path):
        if not os.path.exists(dst_path):
            self.stdout.write(f"Copying media files to {dst_path}.")
            shutil.copytree(src_path, dst_path)
            files = os.listdir(src_path)
            for fname in files:
                shutil.copy2(os.path.join(src_path, fname), dst_path)
        else:
            self.stdout.write(f"Media path {dst_path} for basic data exists, skipping creation.")
