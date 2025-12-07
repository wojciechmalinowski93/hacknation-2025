from django.urls import path

from mcod.users.views import ACSView, LogingovplSwitchView, LogingovplUnlinkView, SSOView

urlpatterns = [
    path("", SSOView.as_view(), name="logingovpl"),
    path("idp", ACSView.as_view(), name="idp"),
    path("unlink", LogingovplUnlinkView.as_view(), name="unlink"),
    path("switch", LogingovplSwitchView.as_view(), name="switch"),
]
