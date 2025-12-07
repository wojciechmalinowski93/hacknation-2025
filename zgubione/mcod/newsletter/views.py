from functools import partial
from types import SimpleNamespace

import falcon
from django.apps import apps
from django.template.loader import render_to_string
from django.utils.translation import get_language, gettext_lazy as _

from mcod.core.api.handlers import CreateOneHdlr, RetrieveOneHdlr, UpdateOneHdlr
from mcod.core.api.hooks import login_optional
from mcod.core.api.views import JsonAPIView
from mcod.newsletter.deserializers import (
    NewsletterRulesApiRequest,
    SubscribeApiRequest,
    UnsubscribeApiRequest,
)
from mcod.newsletter.serializers import (
    NewsletterRulesApiResponse,
    SubscriptionApiResponse,
    UnsubscribeApiResponse,
)


class SubscribeNewsletterView(JsonAPIView):

    @falcon.before(login_optional)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_optional)
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = partial(NewsletterRulesApiRequest)
        serializer_schema = partial(NewsletterRulesApiResponse, many=False)

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            return self._get_instance(*args, **kwargs)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                lang = get_language()
                try:
                    self._cached_instance = SimpleNamespace(
                        id=1,
                        personal_data_processing=render_to_string(f"newsletter/{lang}/personal_data_processing.txt"),
                        personal_data_use=render_to_string(f"newsletter/{lang}/personal_data_use.txt"),
                        personal_data_use_rules=render_to_string(f"newsletter/{lang}/personal_data_use_rules.txt"),
                    )
                except Exception:
                    raise falcon.HTTPNotFound
            return self._cached_instance

    class POST(CreateOneHdlr):
        deserializer_schema = partial(SubscribeApiRequest, many=False)
        serializer_schema = partial(SubscriptionApiResponse, many=False)
        database_model = apps.get_model("newsletter", "Subscription")

        def _get_data(self, cleaned, *args, **kwargs):
            email = cleaned.get("email")
            user = self.request.user if self.request.user.is_authenticated else None
            if self.database_model.is_enabled(email):
                raise falcon.HTTPForbidden(
                    title=_("Invalid action!"),
                    description=_("Email address already exists"),
                )
            if self.database_model.awaits_for_confirm(email):
                raise falcon.HTTPForbidden(
                    title=_("Invalid action!"),
                    description=_("Your newsletter subsciption awaits for confirmation"),
                )
            self.response.context.data = self.database_model.subscribe(email, user=user)


class UnsubscribeNewsletterView(SubscribeNewsletterView):

    csrf_exempt = True

    class POST(CreateOneHdlr):
        deserializer_schema = partial(UnsubscribeApiRequest, many=False)
        serializer_schema = partial(UnsubscribeApiResponse, many=False)
        database_model = apps.get_model("newsletter", "Subscription")

        def _get_data(self, cleaned, *args, **kwargs):
            activation_code = cleaned.get("activation_code")
            try:
                obj = self.database_model.objects.get(activation_code=activation_code)
            except self.database_model.DoesNotExist:
                raise falcon.HTTPForbidden(title=_("Invalid action!"), description=_("Link is out of date"))
            self.response.context.data = obj.unsubscribe()


class ConfirmNewsletterView(JsonAPIView):

    csrf_exempt = True

    class POST(UpdateOneHdlr):
        deserializer_schema = partial(SubscribeApiRequest, many=False)
        serializer_schema = partial(SubscriptionApiResponse, many=False)
        database_model = apps.get_model("newsletter", "Subscription")

        def clean(self, activation_code, *args, **kwargs):
            return {}

        def _get_data(self, cleaned, activation_code, *args, **kwargs):
            try:
                instance = self.database_model.objects.get(activation_code=activation_code, is_active=False)
            except self.database_model.DoesNotExist:
                raise falcon.HTTPForbidden(
                    title=_("Invalid action!"),
                    description=_("The activation link has expired"),
                )

            instance.confirm_subscription()
            instance.refresh_from_db()
            return instance

    @falcon.before(login_optional)
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)
