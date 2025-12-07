from functools import partial

import falcon

from mcod.core.api.handlers import SearchHdlr
from mcod.core.api.hooks import login_required
from mcod.core.api.views import JsonAPIView
from mcod.laboratory.deserializer import LaboratoriesApiRequest
from mcod.laboratory.documents import LabEventDoc
from mcod.laboratory.serializer import LaboratoriesApiResponse


class LaboratorySearchApiView(JsonAPIView):
    @falcon.before(login_required)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = LaboratoriesApiRequest
        serializer_schema = partial(LaboratoriesApiResponse, many=True)
        search_document = LabEventDoc()

        def clean(self, *args, **kwargs):
            cleaned = super().clean(*args, **kwargs)
            if "sort" not in cleaned:
                cleaned["sort"] = "-execution_date"
            return cleaned
