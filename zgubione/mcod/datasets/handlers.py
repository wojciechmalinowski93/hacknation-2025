import os
import zipfile
from functools import partial

import falcon
from django.apps import apps

from mcod.core.api.handlers import RetrieveManyHdlr, RetrieveOneHdlr
from mcod.counters.lib import Counter
from mcod.datasets.deserializers import DatasetResourcesDownloadApiRequest
from mcod.datasets.serializers import DatasetResourcesCSVSerializer, DatasetXMLSerializer


class CSVMetadataViewHandler(RetrieveManyHdlr):
    deserializer_schema = DatasetResourcesDownloadApiRequest
    database_model = apps.get_model("datasets", "Dataset")
    serializer_schema = partial(DatasetResourcesCSVSerializer, many=True)

    def _get_data(self, cleaned, *args, **kwargs):
        return self._get_queryset(cleaned, *args, **kwargs).with_metadata_fetched()

    def prepare_context(self, *args, **kwargs):
        super().prepare_context(*args, **kwargs)
        self.response.context.serializer_schema = self.serializer

    def serialize(self, *args, **kwargs):
        self.prepare_context(*args, **kwargs)
        self.response.downloadable_as = "{}.csv".format(kwargs.get("id", "katalog"))
        return self.response.context


class XMLMetadataViewHandler(RetrieveManyHdlr):
    deserializer_schema = DatasetResourcesDownloadApiRequest
    database_model = apps.get_model("datasets", "Dataset")
    serializer_schema = partial(DatasetXMLSerializer, many=True)

    def _get_data(self, cleaned, *args, **kwargs):
        return self._get_queryset(cleaned, *args, **kwargs).with_metadata_fetched()

    def prepare_context(self, *args, **kwargs):
        super().prepare_context(*args, **kwargs)
        self.response.context.serializer_schema = self.serializer

    def serialize(self, *args, **kwargs):
        self.prepare_context(*args, **kwargs)
        self.response.downloadable_as = "{}.xml".format(kwargs.get("id", "katalog"))
        return self.response.context


class ArchiveDownloadViewHandler(RetrieveOneHdlr):

    database_model = apps.get_model("datasets", "Dataset")

    def serialize(self, *args, **kwargs):
        try:
            zip_path = self._cached_instance.archived_resources_files.path
        except ValueError:
            raise falcon.HTTPNotFound
        try:
            with open(zip_path, "rb") as f:
                zipped_files = f.read()
            with zipfile.ZipFile(zip_path) as z:
                resources_ids = list([os.path.dirname(x).split("_")[-1] for x in z.namelist()])
                counter = Counter()
                for res_id in resources_ids:
                    counter.incr_download_count(res_id)
        except FileNotFoundError:
            raise falcon.HTTPNotFound
        self.response.downloadable_as = os.path.basename(zip_path)

        return zipped_files
