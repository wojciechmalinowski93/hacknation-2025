import os

from django.db.models import Q
from django_tqdm import BaseCommand

from mcod.resources.models import Resource, ResourceFile


class Command(BaseCommand):

    @staticmethod
    def get_openness_score(res, res_format):
        openness_score = res.openness_score
        if res_format.lower() in ["xls", "xlsx"]:
            openness_score = 2
        elif res_format.lower() == "csv":
            openness_score = 3
        elif res_format.lower() == "jsonld":
            openness_score = 4
        return openness_score

    @staticmethod
    def get_file(res, create_main, res_format):
        if not create_main and res_format == "csv":
            _file = res.csv_file
        elif not create_main and res_format == "jsonld":
            _file = res.jsonld_file
        else:
            _file = res.file
        return _file

    @staticmethod
    def get_format(res, create_main, res_format):
        if create_main and res.format is None:
            _format = os.path.splitext(res.file.name)[1][1:]
        elif create_main:
            _format = res.format
        else:
            _format = res_format
        return _format

    def create_resource_files(self, qs, create_main, format=None):
        res_files = []
        self.stdout.write(f"Found {qs.count()} files to migrate.")
        for res in qs:
            res_format = self.get_format(res, create_main, format)
            instance_kwargs = {
                "resource": res,
                "file": self.get_file(res, create_main, res_format),
                "openness_score": self.get_openness_score(res, res_format),
                "format": res_format,
            }
            if create_main:
                instance_kwargs.update(
                    {
                        "mimetype": res.file_mimetype,
                        "encoding": res.file_encoding,
                        "info": res.file_info,
                        "is_main": True,
                    }
                )
            res_files.append(ResourceFile(**instance_kwargs))
            if len(res_files) == 1000:
                ResourceFile.objects.bulk_create(res_files)
                res_files = []
        if res_files:
            ResourceFile.objects.bulk_create(res_files)

    def handle(self, *args, **options):
        self.stdout.write("Started migrating resources files to new model.")
        main_files_qs = Resource.raw.filter(files__isnull=True).exclude(Q(file__isnull=True) | Q(file=""))
        self.stdout.write("Migrating main files.")
        self.create_resource_files(main_files_qs, create_main=True)
        csv_files_qs = Resource.raw.exclude(Q(csv_file__isnull=True) | Q(csv_file=""))
        self.stdout.write("Migrating csv files.")
        self.create_resource_files(csv_files_qs, create_main=False, format="csv")
        jsonld_files_qs = Resource.raw.exclude(Q(jsonld_file__isnull=True) | Q(jsonld_file=""))
        self.stdout.write("Migrating jsonld files.")
        self.create_resource_files(jsonld_files_qs, create_main=False, format="jsonld")
        self.stdout.write("Migration completed")
