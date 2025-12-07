from discourse_django_sso.views import SSOProviderView as BaseSSOProviderView
from django.conf import settings
from django.http.response import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse_lazy

from mcod.discourse import utils
from mcod.discourse.forms import ForumLoginForm
from mcod.users.views import CustomAdminLoginView


class DiscourseLoginView(CustomAdminLoginView):
    form_class = ForumLoginForm
    template_name = "discourse/login.html"


class SSOProviderView(BaseSSOProviderView):
    login_url = reverse_lazy("discourse-login")

    def get(self, request, **kwargs):
        if not settings.DISCOURSE_FORUM_ENABLED:
            return self.handle_no_permission()

        try:
            sso = request.GET["sso"]
            sig = request.GET["sig"]
        except KeyError:
            return HttpResponseBadRequest()
        redirect = utils.ForumProviderService(sso_key=self.sso_secret).get_signed_url(
            user=request.user, redirect_to=self.sso_redirect, sso=sso, signature=sig
        )
        if redirect is None:
            return HttpResponseBadRequest()
        return HttpResponseRedirect(redirect_to=redirect)

    def dispatch(self, request, *args, **kwargs):
        if settings.DISCOURSE_FORUM_ENABLED and request.user.is_authenticated and request.user.has_access_to_forum:
            return super().dispatch(request, *args, **kwargs)

        return self.handle_no_permission()
