from django.conf import settings
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.urls import path
from wagtail.core.utils import WAGTAIL_APPEND_SLASH

from mcod.cms import views

if WAGTAIL_APPEND_SLASH:
    serve_pattern = r"^((?:[\w\-]+/)*)$"
else:
    serve_pattern = r"^([\w\-/]*)$"


WAGTAIL_FRONTEND_LOGIN_TEMPLATE = getattr(settings, "WAGTAIL_FRONTEND_LOGIN_TEMPLATE", "wagtailcore/login.html")


urlpatterns = [
    url(
        r"^_util/authenticate_with_password/(\d+)/(\d+)/$",
        views.authenticate_with_password,
        name="wagtailcore_authenticate_with_password",
    ),
    url(
        r"^_util/login/$",
        auth_views.LoginView.as_view(template_name=WAGTAIL_FRONTEND_LOGIN_TEMPLATE),
        name="wagtailcore_login",
    ),
    path("copy_pl_to_en/<int:page_id>/", views.copy_pl_to_en, name="copy_pl_to_en"),
    url(serve_pattern, views.serve, name="wagtail_serve"),
]

form_urls = [
    url(r"^$", views.FormPagesListView.as_view(), name="cms_forms_index"),
    url(
        r"^submissions/(?P<page_id>\d+)/$",
        views.get_submissions_list_view,
        name="cms_forms_list_submissions",
    ),
    url(
        r"^submissions/(?P<page_id>\d+)/delete/$",
        views.DeleteSubmissionsView.as_view(),
        name="cms_forms_delete_submissions",
    ),
]

chooser_urls = [
    url(
        r"^choose-titled-external-link/$",
        views.titled_external_link,
        name="wagtailadmin_choose_page_titled_external_link",
    ),
    url(
        r"^choose-titled-page/$",
        views.titled_browse,
        name="wagtailadmin_choose_titled_page",
    ),
    url(
        r"^choose-titled-page/(\d+)/$",
        views.titled_browse,
        name="wagtailadmin_choose_titled_page_child",
    ),
    url(
        r"^choose-titled-email-link/$",
        views.titled_email_link,
        name="wagtailadmin_choose_page_titled_email_link",
    ),
    url(
        r"^choose-titled-phone-link/$",
        views.titled_phone_link,
        name="wagtailadmin_choose_page_titled_phone_link",
    ),
    url(
        r"^choose-titled-anchor-link/$",
        views.titled_anchor_link,
        name="wagtailadmin_choose_page_titled_anchor_link",
    ),
]
