from falcon.routing import BaseConverter

from mcod.settings import EXPORT_FORMAT_TO_MIMETYPE, RDF_FORMAT_TO_MIMETYPE


class ExportFormatConverter(BaseConverter):
    def convert(self, value):
        return value if value in list(EXPORT_FORMAT_TO_MIMETYPE.keys()) else None


class RDFFormatConverter(BaseConverter):
    def convert(self, value):
        return value if value in list(RDF_FORMAT_TO_MIMETYPE.keys()) else None
