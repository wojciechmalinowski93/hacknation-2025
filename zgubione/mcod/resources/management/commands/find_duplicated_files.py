import hashlib
import os
from collections import defaultdict
from itertools import chain
from string import punctuation

from django.conf import settings
from django_tqdm import BaseCommand

from mcod.reports.tasks import create_resources_report_task
from mcod.resources.models import Resource


class Command(BaseCommand):

    def handle(self, *args, **options):
        found_duplicates = []
        self.stdout.write("Started analyzing resources filename in order to find possible duplicates.")
        possible_duplicates = self.find_possible_duplicates()
        self.stdout.write(f"Found {len(possible_duplicates)} possible duplicates, analyzing content.")
        for filename, duplicates in possible_duplicates.items():
            duplicated_formats = {d["format"] for d in duplicates}
            if len(duplicated_formats) == 1:
                duplicates = self.check_for_content_duplicates(duplicates)
            if duplicates:
                ids = []
                full_names = []
                res_titles = []
                for duplicate in duplicates:
                    ids.append(str(duplicate["pk"]))
                    full_names.append(duplicate["file"])
                    res_titles.append(duplicate["title"])
                found_duplicates.append(
                    {
                        "Id zdublowanych zasobów": "; ".join(ids),
                        "Instytucja": duplicates[0]["dataset__organization__title"],
                        "Nazwy zasobów": "; ".join(res_titles),
                        "Pełne nazwy plików": "; ".join(full_names),
                    }
                )
        found_duplicates = sorted(found_duplicates, key=lambda x: x["Instytucja"])
        self.stdout.write("Creating report of found duplicates.")
        create_resources_report_task.s(
            data=found_duplicates,
            headers=[
                "Id zdublowanych zasobów",
                "Nazwy zasobów",
                "Instytucja",
                "Pełne nazwy plików",
            ],
            report_name="resources_duplicates",
        ).apply_async()

    def chunk_reader(self, fobj, chunk_size=1024):
        """Generator that reads a file in chunks of bytes"""
        while True:
            chunk = fobj.read(chunk_size)
            if not chunk:
                return
            yield chunk

    def get_hash(self, filename, first_chunk_only=False, hash_algo=hashlib.sha1):
        hashobj = hash_algo()
        with open(filename, "rb") as f:
            if first_chunk_only:
                hashobj.update(f.read(1024))
            else:
                for chunk in self.chunk_reader(f):
                    hashobj.update(chunk)
        return hashobj.digest()

    def find_possible_duplicates(self):
        res_details = (
            Resource.objects.published()
            .by_formats(["xlsx", "csv", "xls"])
            .values("file", "pk", "format", "dataset__organization__title", "title")
        )
        names_dict = {}
        for res in res_details:
            filename = res["file"].rsplit(".", 1)[0]
            split_name = filename.rsplit("_", 1)
            suffix = split_name[-1] if len(split_name) > 1 else ""
            no_punctuation = all([p not in suffix for p in punctuation])
            # If we find a suffix which is long enough and contains only mixed letters and digits its probably
            # a suffix assigned by file storage in order to give unique filename
            if len(suffix) >= 6 and not suffix.isnumeric() and not suffix.isalpha() and no_punctuation:
                filename = split_name[0]
            try:
                names_dict[filename].append(res)
            except KeyError:
                names_dict[filename] = [res]
        return {filename: res for filename, res in names_dict.items() if len(res) > 1}

    def find_by_small_hash(self, files_by_size, files_by_small_hash):
        # For all files with the same file size, get their hash on the first 1024 bytes
        for file_size, resources in files_by_size.items():
            if len(resources) < 2:
                continue  # this file size is unique, no need to spend cpu cycles on it

            for res in resources:
                try:
                    small_hash = self.get_hash(res["full_path"], first_chunk_only=True)
                except OSError:
                    # the file access might've changed till the exec point got here
                    continue
                files_by_small_hash[(file_size, small_hash)].append(res)

    def check_for_content_duplicates(self, resources):
        # based on: https://gist.github.com/tfeldmann/fc875e6630d11f2256e746f67a09c1ae
        files_by_small_hash = defaultdict(list)
        files_by_full_hash = dict()

        def get_files_by_size():
            _files_by_size = defaultdict(list)
            for res in resources:
                res["full_path"] = os.path.join(settings.RESOURCES_MEDIA_ROOT, res["file"])
                try:
                    file_size = os.path.getsize(res["full_path"])
                    _files_by_size[file_size].append(res)
                except OSError:
                    continue
            return _files_by_size

        def flatten_duplicates_dct(dct):
            nested_duplicates = [r for r in dct.values() if len(r) > 1]
            flat_duplicates_lst = list(chain.from_iterable(nested_duplicates))
            return flat_duplicates_lst

        files_by_size = get_files_by_size()

        self.find_by_small_hash(files_by_size, files_by_small_hash)
        # For all files with the hash on the first 1024 bytes, get their hash on the full
        # file - collisions will be duplicates
        duplicates_lst = flatten_duplicates_dct(files_by_small_hash)
        for res in duplicates_lst:
            try:
                full_hash = self.get_hash(res["full_path"], first_chunk_only=False)
            except OSError:
                # the file access might've changed till the exec point got here
                continue

            if full_hash in files_by_full_hash:
                files_by_full_hash[full_hash].append(res)
            else:
                files_by_full_hash[full_hash] = [res]

        content_duplicates = flatten_duplicates_dct(files_by_full_hash)
        return content_duplicates
