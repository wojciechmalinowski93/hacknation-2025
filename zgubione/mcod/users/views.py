import copy
from collections import namedtuple
from functools import partial
from smtplib import SMTPException

import falcon
import marshmallow as ma
from dal import autocomplete
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password as dj_validate_password
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
class BaseSSOView(View):
    pass
from rest_framework import permissions, renderers
from rest_framework.views import APIView

from mcod.academy.models import Course
from mcod.core.api.handlers import CreateOneHdlr, RetrieveOneHdlr, SearchHdlr, UpdateOneHdlr
from mcod.core.api.hooks import (
    get_expired_token_description,
    get_user_pending_description,
    login_required,
)
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned
from mcod.laboratory.models import LabEvent
from mcod.lib.handlers import BaseHandler
from mcod.lib.jwt import get_auth_token
from mcod.lib.triggers import session_store
from mcod.schedules.models import Schedule
from mcod.suggestions.models import AcceptedDatasetSubmission
from mcod.tools.api.dashboard import DashboardMetaSerializer, DashboardSerializer
from mcod.users.constants import LOGINGOVPL_PROCESS, LOGINGOVPL_PROCESS_RESULT, PORTAL_TYPE
from mcod.users.deserializers import (
    ChangePasswordApiRequest,
    ConfirmResetPasswordApiRequest,
    LoginApiRequest,
    MeetingApiSearchRequest,
    RegistrationApiRequest,
    ResendActivationEmailApiRequest,
    ResetPasswordApiRequest,
    UserUpdateApiRequest,
)
from mcod.users.documents import MeetingDoc
from mcod.users.exceptions import SAMLArtException
from mcod.users.forms import AdminLoginForm
from mcod.users.models import LoggingMethod, Meeting, Token
from mcod.users.serializers import (
    ACSResponse,
    ACSTemplateResponse,
    ChangePasswordApiResponse,
    ConfirmResetPasswordApiResponse,
    LoginApiResponse,
    LogoutApiResponse,
    MeetingApiResponse,
    RegistrationApiResponse,
    ResendActivationEmailApiResponse,
    ResetPasswordApiResponse,
    UserApiResponse,
    VerifyEmailApiResponse,
)
from mcod.users.services import logingovpl_service, user_service

User = get_user_model()


class LoginView(JsonAPIView):
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = get_user_model()
        deserializer_schema = LoginApiRequest
        serializer_schema = partial(LoginApiResponse, many=False)

        def _get_data(self, cleaned, *args, **kwargs):
            cleaned = cleaned["data"]["attributes"]
            cleaned["email"] = cleaned["email"].lower()
            try:
                user = User.objects.get(
                    email=cleaned["email"],
                    is_removed=False,
                    is_permanently_removed=False,
                )
            except User.DoesNotExist:
                raise falcon.HTTPUnauthorized(
                    title="401 Unauthorized",
                    description=_("Invalid email or password"),
                    code="account_not_exist",
                )

            if user.state != "active":
                if user.state not in settings.USER_STATE_LIST or user.state == "deleted":
                    raise falcon.HTTPUnauthorized(
                        title="401 Unauthorized",
                        description=_("Account is not available"),
                        code="account_unavailable",
                    )

                if user.state in ("draft", "blocked"):
                    raise falcon.HTTPUnauthorized(
                        title="401 Unauthorized",
                        description=_("Account is blocked"),
                        code="account_unavailable",
                    )

                if user.state == "pending":
                    raise falcon.HTTPForbidden(
                        title="403 Forbidden",
                        description=get_user_pending_description(),
                        code="account_inactive",
                    )

            user = authenticate(request=self.request, **cleaned)

            if user is None:
                raise falcon.HTTPUnauthorized(
                    title="401 Unauthorized",
                    description=_("Invalid email or password"),
                    code="authorization_error",
                )

            if not hasattr(self.request, "session"):
                self.request.session = session_store()

                self.request.META = {}
            login(self.request, user)
            self.request.session.save()
            user.token = get_auth_token(user, self.request.session.session_key)
            user.update_last_logging_method(LoggingMethod.FORM)
            return user


class RegistrationView(JsonAPIView):
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = get_user_model()
        deserializer_schema = RegistrationApiRequest
        serializer_schema = RegistrationApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            if User.objects.filter(email__iexact=data["email"]):
                raise falcon.HTTPForbidden(
                    title="403 Forbidden",
                    description=_("This e-mail is already used"),
                    code="email_already_used",
                )
            data["email"] = data["email"].lower()
            user = User.objects.create_user(**data)
            try:
                user.send_registration_email()
            except SMTPException:
                raise falcon.HTTPInternalServerError(description=_("Email cannot be sent"), code="email_send_error")
            return user


class AccountView(JsonAPIView):
    @falcon.before(login_required)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    @versioned
    def on_put(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PUT, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        serializer_schema = partial(UserApiResponse, many=False)
        include_default = ["institution"]
        _includes = {
            "institution": "organizations.Organization",
            "agent_institution": "organizations.Organization",
            "agent_institution_main": "organizations.Organization",
        }
        _include_map = {
            "agent_institution": "agent_institutions_included",
            "agent_institution_main": "agent_organization",
        }

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            return self._get_instance(*args, **kwargs)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                self._cached_instance = self.request.user
            return self._cached_instance

    class PUT(UpdateOneHdlr):
        database_model = get_user_model()
        deserializer_schema = UserUpdateApiRequest
        serializer_schema = UserApiResponse

        def clean(self, *args, **kwargs):
            return super().clean(self.request.user.id, validators=None, *args, **kwargs)

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]

            user = self.request.user
            for attr, val in data.items():
                setattr(user, attr, val)
            user.save(update_fields=list(data.keys()))
            user.refresh_from_db()
            return user


class DashboardView(JsonAPIView):
    @falcon.before(login_required)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, handler=self.GET, *args, **kwargs)

    class GET(BaseHandler):
        deserializer_schema = ma.Schema()
        serializer_schema = DashboardSerializer(many=False)
        meta_serializer = DashboardMetaSerializer(many=False)

        def _data(self, request, cleaned, *args, **kwargs):
            data = {
                "aggregations": self._get_aggregations(request.user),
            }
            if "schedules" in data["aggregations"]:
                notifications = request.user.schedule_dashboard_notifications
                data["aggregations"]["schedules"].update(
                    {
                        "notifications": notifications,
                        "notifications_count": notifications.count(),
                    }
                )
            return data

        def _get_aggregations(self, user):
            result = {
                "subscriptions": user.get_dashboard_subscriptions(),
            }
            if user.has_access_to_academy_in_dashboard:
                result.update({"academy": self._get_academy_aggregations()})

            if user.has_access_to_laboratory_in_dashboard:
                result.update({"lab": self._get_laboratory_aggregations()})
            if user.has_access_to_suggestions_in_dashboard:
                result.update({"suggestions": self._get_suggestions_aggregations()})
            if user.has_access_to_meetings_in_dashboard:
                result.update({"meetings": self._get_meetings_aggregations()})
            schedules_aggregations = Schedule.get_dashboard_aggregations_for(user)
            if schedules_aggregations:
                result.update({"schedules": schedules_aggregations})

            result.update({"fav_charts": self._get_fav_charts_aggregations(user)})
            if user.is_superuser:
                result.update(
                    {
                        "analytical_tools": self._get_analytical_tools(),
                        "cms_url": settings.CMS_URL,
                    }
                )
            return result

        @staticmethod
        def _get_laboratory_aggregations():
            return {
                "analyses": LabEvent.objects.filter(
                    event_type="analysis",
                ).count(),
                "researches": LabEvent.objects.filter(
                    event_type="research",
                ).count(),
            }

        @staticmethod
        def _get_meetings_aggregations():
            today = timezone.now().date()
            objs = Meeting.objects.published()
            return {
                "planned": objs.filter(start_date__gte=today).count(),
                "finished": objs.filter(start_date__lt=today).count(),
            }

        @staticmethod
        def _get_academy_aggregations():
            courses = Course.objects.with_schedule()
            return {state: courses.filter(_course_state=state).count() for state in Course.COURSE_STATES}

        @staticmethod
        def _get_suggestions_aggregations():
            objs = AcceptedDatasetSubmission.objects.filter(status__in=AcceptedDatasetSubmission.PUBLISHED_STATUSES)
            return {
                "active": objs.filter(is_active=True).count(),
                "inactive": objs.filter(is_active=False).count(),
            }

        @staticmethod
        def _get_fav_charts_aggregations(user: User):
            _default = {"slot-1": {}, "slot-2": {}}
            fav_charts = user.fav_charts or {}
            _default.update(fav_charts)
            for key, item in _default.items():
                if item:
                    _default[key]["thumb_url"] = f"{settings.BASE_URL}/pn-apps/charts/{key}.png"

            return _default

        @staticmethod
        def _get_analytical_tools():
            return [
                {"name": "Kibana", "url": settings.KIBANA_URL},
                {"name": "Metabase", "url": settings.METABASE_URL},
            ]


class LogoutView(JsonAPIView):
    @falcon.before(login_required)
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = get_user_model()
        serializer_schema = LogoutApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            _user_id = self.request.user.id
            logout(self.request)
            return namedtuple("User", ["id", "is_logged_out"])(_user_id, True)


class ResetPasswordView(JsonAPIView):
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)
        response.status = falcon.HTTP_200

    class POST(CreateOneHdlr):
        deserializer_schema = partial(ResetPasswordApiRequest, many=False)
        serializer_schema = partial(ResetPasswordApiResponse, many=False)
        database_model = get_user_model()

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            try:
                user = self.database_model.objects.get(email=data["email"])
            except self.database_model.DoesNotExist:
                raise falcon.HTTPNotFound(description=_("Account not found"), code="account_not_found")
            try:
                msgs_count = user.send_password_reset_email()
            except SMTPException:
                raise falcon.HTTPInternalServerError(description=_("Email cannot be sent"), code="email_send_error")
            user.is_password_reset_email_sent = bool(msgs_count)
            return user


class ConfirmResetPasswordView(JsonAPIView):
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = get_user_model()
        deserializer_schema = ConfirmResetPasswordApiRequest
        serializer_schema = ConfirmResetPasswordApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            token = kwargs.get("token")
            try:
                token = Token.objects.get(token=token, token_type=1)
            except Token.DoesNotExist:
                raise falcon.HTTPNotFound()
            if not token.is_valid:
                raise falcon.HTTPBadRequest(description=_("Expired token"), code="expired_token")
            token.user.set_password(data["new_password1"])
            token.user.save()
            token.invalidate()
            token.user.is_confirmed = True
            return token.user


class ChangePasswordView(JsonAPIView):
    @falcon.before(login_required)
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = get_user_model()
        deserializer_schema = ChangePasswordApiRequest
        serializer_schema = ChangePasswordApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            user = self.request.user
            data = cleaned["data"]["attributes"]
            is_valid = user.check_password(data["old_password"])
            if not is_valid:
                raise falcon.HTTPUnprocessableEntity(
                    description=_("Wrong password"),
                )
            try:
                dj_validate_password(data["new_password1"])
            except DjangoValidationError as e:
                raise falcon.HTTPUnprocessableEntity(
                    description=e.error_list[0].message,
                )
            if data["new_password1"] != data["new_password2"]:
                raise falcon.HTTPUnprocessableEntity(
                    description=_("Passwords not match"),
                )
            user.set_password(data["new_password1"])
            user.save()
            user.is_password_changed = True
            return user


class VerifyEmailView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        database_model = get_user_model()
        serializer_schema = VerifyEmailApiResponse

        def clean(self, token, *args, **kwargs):
            try:
                token = Token.objects.get(token=token, token_type=0)
            except Token.DoesNotExist:
                raise falcon.HTTPNotFound()

            if not token.is_valid:
                raise falcon.HTTPBadRequest(description=get_expired_token_description(), code="expired_token")

            token.user.state = "active" if token.user.state == "pending" else token.user.state
            token.user.email_confirmed = timezone.now()
            token.user.save()
            token.invalidate()

            return {}

        def _get_data(self, cleaned, token, *args, **kwargs):
            return namedtuple("Token", ["id", "is_verified"])(token, True)


class ResendActivationEmailView(JsonAPIView):
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = get_user_model()
        deserializer_schema = ResendActivationEmailApiRequest
        serializer_schema = ResendActivationEmailApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            try:
                user = self.database_model.objects.get(email=data["email"])
            except self.database_model.DoesNotExist:
                raise falcon.HTTPNotFound(description=_("Account not found"), code="account_not_found")
            try:
                msgs_count = user.resend_activation_email()
                user.is_activation_email_sent = bool(msgs_count)
                self.response.context.data = user
            except SMTPException:
                raise falcon.HTTPInternalServerError(description=_("Email cannot be sent"), code="email_send_error")


class CustomAdminLoginView(DjangoLoginView):
    form_class = AdminLoginForm
    template_name = "admin/login.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_active and request.user.is_staff:
            # Already logged-in, redirect to admin index
            index_path = reverse("admin:index", current_app=settings.COMPONENT)
            return HttpResponseRedirect(index_path)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        """New logic (setting flag last_logging_method) when user form is valid."""
        response = super().form_valid(form)
        if form.is_valid():
            user: User = form.get_user()
            user.update_last_logging_method(LoggingMethod.FORM)
            user.save()
        return response


class MeetingsView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = MeetingApiSearchRequest
        serializer_schema = partial(MeetingApiResponse, many=True)
        search_document = MeetingDoc()


class SSOView(BaseSSOView):

    def get(self, request, *args, **kwargs):
        """Prepare an envelope and send it to the login.gov.pl service
        or render the template mocking that service.
        """
        if settings.USERS_TEST_LOGINGOVPL:
            context = {"in_response_to": self.get_authn_request_id()}
            return render(request, "logingovpl/test_login_gov_pl.html", context=context)
        return super().get(request, *args, **kwargs)

    def get_authn_request_id(self):
        """Prepare the request identifier needed to the later processing of logging or linking
        via the login.gov.pl service.
        """
        portal = self.request.GET.get("portal")
        is_admin_panel = True if portal == "admin" else False
        user_identifier = self.request.user.id if self.request.user.is_authenticated else None
        return logingovpl_service.prepare_authn_request_id(user_identifier, is_admin_panel)


class ACSView(APIView):
    """/idp endpoint view responsible for handling login.gov.pl requests."""

    permission_classes = [permissions.AllowAny]
    renderer_classes = [renderers.JSONRenderer]

    def post(self, request, *args, **kwargs):  # noqa
        """Link or log-in user, based on the data received from the login.gov.pl service."""

        if settings.USERS_TEST_LOGINGOVPL:
            serializer = ACSTemplateResponse(data=request.data)
        else:
            serializer = ACSResponse(data=request.data)

        unknown_url = logingovpl_service.get_redirect_url(
            PORTAL_TYPE.UNKNOWN, LOGINGOVPL_PROCESS.UNKNOWN, LOGINGOVPL_PROCESS_RESULT.UNKNOWN
        )
        if not serializer.is_valid():
            return HttpResponseRedirect(unknown_url)
        try:
            logingovpl_data = logingovpl_service.get_logingovpl_data_and_logout(
                request_data=serializer.validated_data, is_logingovpl_mocked=settings.USERS_TEST_LOGINGOVPL
            )
        except SAMLArtException:
            return HttpResponseRedirect(unknown_url)

        portal = logingovpl_service.get_portal_or_none_from_authn_request_id(logingovpl_data.in_response_to)
        process = logingovpl_service.get_process_or_none_from_authn_request_id(logingovpl_data.in_response_to)

        if portal is None or process is None:
            return HttpResponseRedirect(unknown_url)

        error_url = logingovpl_service.get_redirect_url(portal, process, LOGINGOVPL_PROCESS_RESULT.ERROR)
        success_url = logingovpl_service.get_redirect_url(portal, process, LOGINGOVPL_PROCESS_RESULT.SUCCESS)

        # linking process
        if process == LOGINGOVPL_PROCESS.LINK:
            user_id = logingovpl_service.get_user_id_or_none_from_authn_request_id(logingovpl_data.in_response_to)
            user = user_service.get_active_session_user_or_none(user_id, portal)

            if user is None:
                return HttpResponseRedirect(error_url)

            user_service.link_to_logingovpl(user, logingovpl_data.user.pesel)
            return HttpResponseRedirect(success_url)

        # logging process
        if process == LOGINGOVPL_PROCESS.LOGIN:
            user = user_service.get_last_user_by_pesel_or_none(logingovpl_data.user.pesel, portal)
            if user is None:
                return HttpResponseRedirect(error_url)

            user_service.login_by_logingovpl(request, user)
            user.update_last_logging_method(LoggingMethod.WK)
            return HttpResponseRedirect(success_url)

        # not linking nor logging process
        return HttpResponseRedirect(unknown_url)


class LogingovplUnlinkView(APIView):
    permission_classes = [permissions.AllowAny]
    renderer_classes = [renderers.JSONRenderer]

    def get(self, request, *args, **kwargs):  # noqa
        error_url = logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.UNLINK, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        success_url = logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.UNLINK, LOGINGOVPL_PROCESS_RESULT.SUCCESS
        )
        if not request.user.is_authenticated:
            return HttpResponseRedirect(error_url)

        user_service.unlink_from_logingovpl(request.user)
        return HttpResponseRedirect(success_url)


class LogingovplSwitchView(APIView):
    permission_classes = [permissions.AllowAny]
    renderer_classes = [renderers.JSONRenderer]

    def get(self, request, *args, **kwargs):  # noqa
        user = copy.copy(request.user)
        logout(request)

        email = logingovpl_service.check_attr_email(request.query_params.get("email"))
        portal = logingovpl_service.check_attr_portal(request.query_params.get("portal"))
        error_url = logingovpl_service.get_redirect_url(portal, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR)
        success_url = logingovpl_service.get_redirect_url(portal, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.SUCCESS)

        if email is None or portal is None or not user.is_authenticated:
            return HttpResponseRedirect(error_url)

        new_user = user_service.get_user_to_switch_or_none(user, email)
        if new_user is None:
            return HttpResponseRedirect(error_url)

        user_service.login_by_logingovpl(request=request, user=new_user)
        new_user.token = get_auth_token(new_user, request.session.session_key)
        new_user.update_last_logging_method(LoggingMethod.WK)

        response = HttpResponseRedirect(success_url)
        response.set_cookie(
            settings.API_TOKEN_COOKIE_NAME,
            new_user.token,
            domain=settings.SESSION_COOKIE_DOMAIN,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            secure=settings.SESSION_COOKIE_SECURE,
            path=settings.SESSION_COOKIE_PATH,
            max_age=settings.JWT_EXPIRATION_DELTA,
        )
        response.set_cookie(
            settings.SESSION_COOKIE_NAME,
            request.session.session_key,
            domain=settings.SESSION_COOKIE_DOMAIN,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            secure=settings.SESSION_COOKIE_SECURE,
            path=settings.SESSION_COOKIE_PATH,
            max_age=settings.JWT_EXPIRATION_DELTA,
        )
        return response


class StaffAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self) -> QuerySet:
        qs: QuerySet = get_user_model().objects.autocomplete(self.request.user, self.q)
        return qs.filter(is_staff=True).order_by("email")


class AdminAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self) -> QuerySet:
        qs: QuerySet = get_user_model().objects.autocomplete(self.request.user, self.q)
        return qs.filter(is_superuser=True).order_by("email")


class AgentAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self) -> QuerySet:
        qs: QuerySet = get_user_model().objects.agents().autocomplete(self.request.user, self.q)
        return qs.order_by("email")
