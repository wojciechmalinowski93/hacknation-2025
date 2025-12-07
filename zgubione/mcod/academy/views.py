from functools import partial

import falcon

from mcod.academy.deserializers import CourseApiSearchRequest
from mcod.academy.documents import CourseDoc
from mcod.academy.serializers import CourseApiResponse
from mcod.core.api.handlers import SearchHdlr
from mcod.core.api.hooks import login_required
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned


class CoursesSearchApiView(JsonAPIView):
    @falcon.before(
        login_required,
        roles=["official", "agent", "admin", "editor", "lod_admin", "aod_admin"],
    )
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = CourseApiSearchRequest
        serializer_schema = partial(CourseApiResponse, many=True)
        search_document = CourseDoc()
