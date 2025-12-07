from django.conf import settings
from django.conf.urls import url
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import activate
from django.views.decorators.vary import vary_on_cookie
from fancy_cache import cache_page
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from wagtail.api.v2.utils import BadRequestError, page_models_from_string
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.core.models import Page, PageRevision
from wagtail.images.api.v2.views import ImagesAPIViewSet

from mcod.cms.api.serializers import CmsPageSerializer
from mcod.cms.utils import filter_page_type


class ImagesViewSet(ImagesAPIViewSet):
    body_fields = ImagesAPIViewSet.body_fields + ["alt_i18n"]
    listing_default_fields = ImagesAPIViewSet.listing_default_fields + ["alt_i18n"]
    known_query_parameters = ImagesAPIViewSet.known_query_parameters.union(["lang"])

    response_field_name_changes = {"alt_i18n": "alt"}

    def _activate_language(self, request):
        lang = request.query_params.get("lang", "pl")
        if lang in settings.LANGUAGE_CODES:
            activate(lang)

    def _change_field_name(self, data):
        for field_name, goal_name in self.response_field_name_changes.items():
            data[goal_name] = data.pop(field_name)

    def get_queryset(self):
        self._activate_language(self.request)
        return super().get_queryset()

    def listing_view(self, request):
        response = super().listing_view(request)
        for item_data in response.data["items"]:
            self._change_field_name(item_data)
        return response

    def detail_view(self, request, pk):
        response = super().detail_view(request, pk)
        self._change_field_name(response.data)
        return response


class CmsPagesViewSet(PagesAPIViewSet):
    base_serializer_class = CmsPageSerializer
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(
        ["type", "child_of", "descendant_of", "lang", "rev", "locale"]
    )
    body_fields = BaseAPIViewSet.body_fields + [
        "title",
    ]
    meta_fields = BaseAPIViewSet.meta_fields + [
        "html_url",
        "url_path",
        "slug",
        "show_in_menus",
        "seo_title",
        "search_description",
        "first_published_at",
        "last_published_at",
        "parent",
        "children",
        "locale",
    ]
    listing_default_fields = BaseAPIViewSet.listing_default_fields + [
        "title",
        "html_url",
        "slug",
        "first_published_at",
        "last_published_at",
        "url_path",
    ]
    nested_default_fields = BaseAPIViewSet.nested_default_fields + [
        "title",
    ]
    detail_only_fields = ["parent"]
    lookup_field = "url_path"
    lookup_url_kwarg = None

    def _activate_language(self, request):
        lang = request.query_params.get("lang", "pl")
        if lang in settings.LANGUAGE_CODES:
            activate(lang)

    def is_superuser_rev_request(self):
        return bool(
            self.request.user
            and self.request.user.is_superuser
            and self.request.query_params.get("rev")
            and self.kwargs.get("url_path")
        )

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
        )
        if self.is_superuser_rev_request():
            rev_id = self.request.query_params.get("rev")
            query_filter = {
                "revisions__content_json__icontains": '"{}": "{}"'.format(self.lookup_field, self.kwargs[lookup_url_kwarg])
            }
            obj = queryset.filter(**query_filter).order_by("revisions__id").first()
            if not obj:
                raise Http404("No Page matches the given query.")

            if rev_id in ("latest", "-1"):
                obj = obj.get_latest_revision_as_page()
            else:
                try:
                    rev_id = int(rev_id)
                    revision = obj.revisions.get(pk=rev_id)
                    obj = revision.as_page_object()
                except (ValueError, PageRevision.DoesNotExist):
                    raise Http404("No such Page Revision.")

        else:
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(queryset, **filter_kwargs)
            obj = obj.specific

        return obj

    @method_decorator(
        cache_page(
            cache_timeout=settings.CMS_API_CACHE_TIMEOUT,
            key_prefix="cms-api",
            remember_all_urls=True,
            remember_stats_all_urls=True,
        )
    )
    @method_decorator(vary_on_cookie)
    def page_view(self, request, url_path=None):
        return self._page_view(request, url_path=url_path)

    def _page_view(self, request, url_path=None):
        url_path = "" if not url_path else url_path
        url_parts = [part.strip("/") for part in url_path.split("/") if part]
        self.kwargs["url_path"] = "/{}/".format("/".join(url_parts)).replace("//", "/")
        instance = self.get_object()
        self._activate_language(request)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_queryset(self):
        self._activate_language(self.request)
        request = self.request

        try:
            models = page_models_from_string(request.GET.get("type", "wagtailcore.Page"))
        except (LookupError, ValueError):
            raise BadRequestError("type doesn't exist")

        _qs = Page.objects.all().public()
        if not (request.user and request.user.is_superuser):
            _qs = _qs.live()

        if self.request.site:
            _qs = _qs.descendant_of(self.request.site.root_page, inclusive=True)
        else:
            # No sites configured
            _qs = _qs.none()

        if not models:
            return _qs
        if len(models) == 1:
            return models[0].objects.filter(id__in=_qs.values_list("id", flat=True))
        return filter_page_type(_qs, models)

    @classmethod
    def get_urlpatterns(cls):
        return [
            url(r"^$", cls.as_view({"get": "page_view"}), name="detail"),
            url(r"^(?P<url_path>.*)/$", cls.as_view({"get": "page_view"}), name="detail"),
        ]

    @classmethod
    def get_object_detail_urlpath(cls, model, url_path, namespace=""):
        if namespace:
            url_name = namespace + ":detail"
        else:
            url_name = "detail"

        url_path = url_path.strip("/")
        result = reverse(url_name, args=(url_path,))
        return result

    def post(self, request, url_path, **kwargs):
        try:
            url_path = url_path.strip()
            page = Page.objects.get(url_path="/{}/".format(url_path))
            return page.specific.save_post(request)
        except Page.DoesNotExist:
            raise NotFound
