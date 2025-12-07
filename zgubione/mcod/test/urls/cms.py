from bokeh.server.django import static_extensions
from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.urls import path
from django.views.generic.base import TemplateView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.documents.api.v2.views import DocumentsAPIViewSet

from mcod.cms import urls as cms_urls
from mcod.cms.api.router import CmsApiRouter
from mcod.cms.api.views import CmsPagesViewSet, ImagesViewSet
from mcod.cms.views import revisions_view

panel_app_config = apps.get_app_config("mcod.pn_apps")

urlpatterns = []

api_router = CmsApiRouter("cmsapi")
api_router.register_endpoint("pages", CmsPagesViewSet)
api_router.register_endpoint("images", ImagesViewSet)
api_router.register_endpoint("documents", DocumentsAPIViewSet)

urlpatterns += [
    path("documents/", include(wagtaildocs_urls)),
    path("api/", api_router.urls),
    path("hypereditor/", include("hypereditor.urls")),
    path(
        "admin/pages/<int:page_id>/revisions/<int:revision_id>/view/",
        revisions_view,
        name="revisions_view",
    ),
    path("admin/", include(wagtailadmin_urls)),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="admin/robots.txt", content_type="text/plain"),
    ),
    path("", include(cms_urls)),
]
urlpatterns += static(settings.IMAGES_URL, document_root=settings.IMAGES_MEDIA_ROOT)
urlpatterns += static_extensions()
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
