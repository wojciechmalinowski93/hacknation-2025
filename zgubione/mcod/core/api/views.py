from datetime import datetime

import falcon
from falcon import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from mcod import settings
from mcod.core.api.handlers import RetrieveOneHdlr


class BaseView:

    csrf_exempt = False  # change to True to disable CSRF validation for concrete view.

    def handle(self, request, response, handler, *args, **kwargs):
        response.content_type = self.set_content_type(response, **kwargs)
        response.status = falcon.HTTP_200
        response.media = handler(request, response).run(*args, **kwargs)

    def handle_post(self, request, response, handler, *args, **kwargs):
        response.media = handler(request, response).run(*args, **kwargs)
        response.content_type = self.set_content_type(response, **kwargs)
        response.status = falcon.HTTP_201

    def handle_delete(self, request, response, handler, *args, **kwargs):
        handler(request, response).run(*args, **kwargs)
        response.content_type = None
        response.status = falcon.HTTP_204

    def handle_patch(self, request, response, handler, *args, **kwargs):
        response.content_type = self.set_content_type(response, **kwargs)
        response.status = falcon.HTTP_202
        response.media = handler(request, response).run(*args, **kwargs)

    def handle_bulk_patch(self, request, response, handler, *args, **kwargs):
        handler(request, response).run(*args, **kwargs)
        response.content_type = self.set_content_type(response, **kwargs)
        response.status = falcon.HTTP_202

    def handle_bulk_delete(self, request, response, handler, *args, **kwargs):
        handler(request, response).run(*args, **kwargs)
        response.content_type = self.set_content_type(response, **kwargs)
        response.status = falcon.HTTP_202

    def set_content_type(self, resp, **kwargs):
        return resp.content_type


class JsonAPIView(BaseView):
    def set_content_type(self, resp, **kwargs):
        if resp.content_type not in settings.JSONAPI_MIMETYPES:
            return settings.JSONAPI_MIMETYPES[0]

        return resp.content_type


class TabularView(BaseView):

    def handle(self, request, response, handler, *args, **kwargs):
        super().handle(request, response, handler, *args, **kwargs)
        # https://falcon.readthedocs.io/en/latest/user/recipes/output-csv.html
        response.downloadable_as = "harmonogram-{}.{}".format(
            datetime.today().strftime("%Y-%m-%d"),
            kwargs.get("export_format", "csv"),
        )

    def set_content_type(self, resp, **kwargs):
        return settings.EXPORT_FORMAT_TO_MIMETYPE.get(kwargs.get("export_format", "csv"), resp.content_type)


class RDFView(BaseView):
    def set_content_type(self, resp, rdf_format=None, **kwargs):
        if rdf_format:
            return settings.RDF_FORMAT_TO_MIMETYPE.get(rdf_format, None)

        if resp.content_type not in settings.RDF_MIMETYPES:
            return "application/ld+json"

        return resp.content_type


class XMLRDFView(RDFView):
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    def set_content_type(self, resp, **kwargs):
        return super().set_content_type(resp, rdf_format="xml", **kwargs)


class VocabRDFView(XMLRDFView):
    class GET(RetrieveOneHdlr):
        def _get_data(self, cleaned, *args, **kwargs):
            return self.vocab_class()

        def clean(self, *args, **kwargs):
            return None


class VocabEntryRDFView(VocabRDFView):
    def on_get(self, request, response, *args, **kwargs):
        entry_name = kwargs.get("entry_name")

        if entry_name in self.vocab_class().entries:
            self.handle(request, response, self.GET, *args, **kwargs)
        else:
            response.text = f'''"{self.vocab_name} doesn't have '{entry_name}' entry."'''
            response.status = falcon.HTTP_404

    class GET(VocabRDFView.GET):
        def _get_data(self, cleaned, *args, **kwargs):
            entry_name = kwargs.get("entry_name")
            return self.vocab_class().entries[entry_name]


class MetricsResource:
    def on_get(self, req: Request, resp: Response):
        """Handle /metrics endpoint."""
        resp.status = falcon.HTTP_200
        resp.content_type = CONTENT_TYPE_LATEST
        resp.text = generate_latest().decode("utf-8")
