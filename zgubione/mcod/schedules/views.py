import uuid
from collections import namedtuple
from functools import partial

import falcon
from django.utils.translation import gettext_lazy as _

from mcod import settings
from mcod.core.api.handlers import (
    BaseHdlr,
    CreateOneHdlr,
    IncludeMixin,
    RemoveOneHdlr,
    RetrieveManyHdlr as BaseRetrieveManyHdlr,
    RetrieveOneHdlr,
    UpdateManyHdlr,
    UpdateOneHdlr,
)
from mcod.core.api.hooks import login_required
from mcod.core.api.schemas import ListingSchema
from mcod.core.api.views import JsonAPIView, TabularView
from mcod.core.versioning import versioned
from mcod.organizations.models import Organization
from mcod.schedules.deserializers import (
    AdminCreateUserScheduleItemRequest,
    CommentsApiRequest,
    CreateCommentRequest,
    CreateNotificationsApiRequest,
    CreateUserScheduleItemRequest,
    NotificationApiRequest,
    NotificationsApiRequest,
    ScheduleApiRequest,
    SchedulesApiRequest,
    UpdateNotificationApiRequest,
    UpdateUserScheduleRequest,
    UserScheduleApiRequest,
    UserScheduleItemApiRequest,
    UserScheduleItemFormatApiRequest,
    UserScheduleItemInstitutionApiRequest,
    UserScheduleItemsApiRequest,
    UserSchedulesApiRequest,
    get_schedule_deserializer_schema,
    get_user_schedule_item_deserializer_schema,
)
from mcod.schedules.models import Comment, Notification, Schedule, UserSchedule, UserScheduleItem
from mcod.schedules.serializers import (
    CommentApiResponse,
    CreateNotificationsApiResponse,
    ExportUrlApiResponse,
    NotificationApiResponse,
    ScheduleApiResponse,
    UserScheduleApiResponse,
    UserScheduleItemApiResponse,
    UserScheduleItemFormatApiResponse,
    UserScheduleItemInstitutionApiResponse,
)
from mcod.schedules.tasks import send_admin_notification_task, update_notifications_task
from mcod.users.models import User
from mcod.users.serializers import AgentApiResponse


class RetrieveManyHdlr(IncludeMixin, BaseRetrieveManyHdlr):
    pass


class RetrieveTabularMixin:

    def update_context(self):
        data = getattr(self.response.context, "data", None)
        self.response.context.data = UserScheduleItem.objects.none() if not data else data
        # checking if full export is expected.
        cdata = getattr(self.request.context, "cleaned_data", {})
        self.response.context.full = True if cdata.get("full", False) and self.request.user.is_superuser else False
        instance = getattr(self, "_cached_instance", None)
        self.response.context.state = instance.state if instance else cdata.get("state")

    def serialize(self, *args, **kwargs):
        self.prepare_context(*args, **kwargs)
        self.update_context()
        return self.response.context


class CommentsView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        return self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["admin", "agent"])
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    @falcon.before(login_required, roles=["admin", "agent"])
    def on_patch(self, request, response, *args, **kwargs):
        self.handle_patch(request, response, self.PATCH, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = CommentsApiRequest
        serializer_schema = partial(CommentApiResponse, many=True)
        database_model = Comment

        def _get_queryset(self, cleaned, *args, **kwargs):
            try:
                obj = UserScheduleItem.objects.get(pk=kwargs.get("id"))
            except UserScheduleItem.DoesNotExist:
                raise falcon.HTTPNotFound
            return self.database_model.objects.get_paginated_results(user_schedule_item=obj, **cleaned)

    class POST(CreateOneHdlr):
        deserializer_schema = CreateCommentRequest
        serializer_schema = CommentApiResponse
        database_model = Comment

        def _get_data(self, cleaned, *args, **kwargs):
            try:
                user_schedule_item = UserScheduleItem.objects.get(pk=kwargs.get("id"))
            except UserScheduleItem.DoesNotExist:
                raise falcon.HTTPNotFound

            data = cleaned["data"]["attributes"]
            self.response.context.data = self.database_model.objects.create(
                user_schedule_item=user_schedule_item,
                created_by=self.request.user,
                **data,
            )

    class PATCH(UpdateOneHdlr):
        deserializer_schema = CreateCommentRequest
        serializer_schema = CommentApiResponse
        database_model = Comment

        def clean(self, *args, **kwargs):
            instance = self._get_instance(*args, **kwargs)
            if instance.created_by_id != self.request.user.pk:
                raise falcon.HTTPForbidden(title="You have no permission to update the resource!")
            return super().clean(validators=None, *args, **kwargs)

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.database_model.objects.get(pk=id)
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            instance = self._get_instance(id, *args, **kwargs)
            for key, val in data.items():
                setattr(instance, key, val)
            instance.modified_by = self.request.user
            instance.save()
            instance.refresh_from_db()
            return instance


class UserScheduleItemsView(JsonAPIView):

    @falcon.before(login_required, roles=["agent"])
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = UserScheduleItemsApiRequest
        serializer_schema = partial(UserScheduleItemApiResponse, many=True)
        database_model = UserScheduleItem
        _includes = {
            "comment": "schedules.Comment",
            "schedule": "schedules.Schedule",
            "user": "users.User",
            "user_schedule": "schedules.UserSchedule",
        }
        _include_map = {
            "comment": "comments_included",
        }

        def _get_queryset(self, cleaned, *args, **kwargs):
            if "id" in kwargs:
                cleaned["user_schedule_id"] = kwargs["id"]
            if "schedule_id" in kwargs:
                cleaned["schedule_id"] = kwargs["schedule_id"]
            return self.database_model.objects.get_paginated_results(
                user=self.request.user.extra_agent_of or self.request.user, **cleaned
            )

    class POST(CreateOneHdlr):
        deserializer_schema = CreateUserScheduleItemRequest
        serializer_schema = UserScheduleItemApiResponse
        database_model = UserScheduleItem

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return super().clean(*args, **kwargs)

        def _get_data(self, cleaned, *args, **kwargs):
            schedule = self._get_instance(*args, **kwargs)
            data = cleaned["data"]["attributes"]
            user_schedule, created = UserSchedule.objects.get_or_create(
                user=self.request.user.extra_agent_of or self.request.user,
                schedule=schedule,
                defaults={"created_by": self.request.user},
            )
            if user_schedule.is_ready:
                raise falcon.HTTPForbidden(title="You cannot add new item - your schedule is set ready!")
            data["user_schedule"] = user_schedule
            data["created_by"] = self.request.user
            self.response.context.data = self.database_model.objects.create(**data)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                schedule = Schedule.get_current_plan()
                if not schedule:
                    raise falcon.HTTPForbidden(title="There is no currently planned schedule yet!")
                if schedule.is_blocked:
                    raise falcon.HTTPForbidden(title="The schedule is blocked!")
                self._cached_instance = schedule
            return self._cached_instance


class AgentView(JsonAPIView):

    @falcon.before(login_required, roles=["admin"])
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["admin"])
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = ScheduleApiRequest
        serializer_schema = AgentApiResponse
        _includes = {
            "schedule": "schedules.Schedule",
            "user_schedule": "schedules.UserSchedule",
            "user_schedule_item": "schedules.UserScheduleItem",
        }
        _include_map = {
            "schedule": "planned_schedule",
            "user_schedule": "_planned_user_schedule",
            "user_schedule_item": "planned_user_schedule_items",
        }

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = User.objects.agents().get(pk=id)
                except User.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

    class POST(CreateOneHdlr):
        deserializer_schema = AdminCreateUserScheduleItemRequest
        serializer_schema = UserScheduleItemApiResponse
        database_model = UserScheduleItem

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = User.objects.agents().get(pk=kwargs["id"])
                except User.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return super().clean(*args, **kwargs)

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            data["created_by"] = self.request.user
            data["user"] = self._get_instance(*args, **kwargs)
            try:
                self.response.context.data = self.database_model.create(**data)
            except Exception as exc:
                raise falcon.HTTPForbidden(title=exc)


class AgentsView(JsonAPIView):

    @falcon.before(login_required, roles=["admin"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = ListingSchema
        serializer_schema = partial(AgentApiResponse, many=True)
        _includes = {
            "schedule": "schedules.Schedule",
            "user_schedule": "schedules.UserSchedule",
            "user_schedule_item": "schedules.UserScheduleItem",
        }
        _include_map = {
            "schedule": "planned_schedule",
            "user_schedule": "_planned_user_schedule",
            "user_schedule_item": "planned_user_schedule_items",
        }

        def _get_queryset(self, cleaned, *args, **kwargs):
            return User.objects.agents_paginated(**cleaned)


class UserScheduleItemFormatsView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = UserScheduleItemFormatApiRequest
        serializer_schema = partial(UserScheduleItemFormatApiResponse, many=True)

        def _get_debug_query(self, cleaned, *args, **kwargs):
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            UserScheduleItemFormat = namedtuple("format", "id name")
            return [UserScheduleItemFormat(id=idx, name=x) for idx, x in enumerate(UserScheduleItem.FORMATS, start=1)]


class UserScheduleItemInstitutionsView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = UserScheduleItemInstitutionApiRequest
        serializer_schema = partial(UserScheduleItemInstitutionApiResponse, many=True)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = User.objects.get(pk=kwargs["user_id"])
                except User.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_queryset(self, cleaned, *args, **kwargs):
            query = {**cleaned}
            if self.request.user.is_superuser:
                query["agents__isnull"] = False
                if "user_id" in kwargs:  # returns main agent institution as first.
                    user = self._get_instance(*args, **kwargs)
                    return user.agent_institutions_included.get_page(**query)
            else:
                user = self.request.user.extra_agent_of or self.request.user
                query["agents__id"] = user.id
            return Organization.objects.get_paginated_results(**query)


class UserScheduleItemsTabularView(TabularView):

    @falcon.before(login_required, roles=["admin", "agent"], restore_from="token")
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveTabularMixin, RetrieveManyHdlr):
        deserializer_schema = UserScheduleItemsApiRequest
        serializer_schema = partial(UserScheduleItemApiResponse, many=True)
        database_model = UserScheduleItem

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                if "id" in kwargs:
                    try:
                        self._cached_instance = UserSchedule.objects.published().get(pk=kwargs["id"])
                    except UserSchedule.DoesNotExist:
                        raise falcon.HTTPNotFound
                if "schedule_id" in kwargs:
                    try:
                        self._cached_instance = Schedule.objects.published().get(pk=kwargs["schedule_id"])
                    except Schedule.DoesNotExist:
                        raise falcon.HTTPNotFound
            return getattr(self, "_cached_instance", None)

        def _get_queryset(self, cleaned, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            if "id" in kwargs:
                cleaned["user_schedule_id"] = kwargs["id"]
            if "schedule_id" in kwargs:
                cleaned["schedule_id"] = kwargs["schedule_id"]
            return self.database_model.objects.export(user=self.request.user, **cleaned)


class UserScheduleItemView(JsonAPIView):
    @falcon.before(login_required, roles=["admin", "agent"])
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_delete(self, request, response, *args, **kwargs):
        return self.handle_delete(request, response, self.DELETE, *args, **kwargs)

    @falcon.before(login_required, roles=["admin", "agent"])
    def on_patch(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PATCH, *args, **kwargs)

    class DELETE(RemoveOneHdlr):
        database_model = UserScheduleItem

        def clean(self, id, *args, **kwargs):
            try:
                obj = self.database_model.objects.published().get(pk=id)
            except self.database_model.DoesNotExist:
                raise falcon.HTTPNotFound
            if not obj.can_be_deleted_by(self.request.user):
                raise falcon.HTTPForbidden(title="You have no permission to delete the resource!")
            if not self.request.user.is_superuser and obj.schedule.is_blocked:
                raise falcon.HTTPForbidden(title="The schedule is blocked!")
            return obj

    class GET(RetrieveOneHdlr):
        deserializer_schema = UserScheduleItemApiRequest
        serializer_schema = UserScheduleItemApiResponse
        database_model = UserScheduleItem
        include_default = ["comment", "schedule", "user_schedule"]

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    query = {"pk": id}
                    if not self.request.user.is_superuser:
                        query["user_schedule__user"] = self.request.user.extra_agent_of or self.request.user
                    self._cached_instance = self.database_model.objects.published().get(**query)
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

    class PATCH(UpdateOneHdlr):
        deserializer_schema = CreateUserScheduleItemRequest
        serializer_schema = UserScheduleItemApiResponse
        database_model = UserScheduleItem

        def clean(self, *args, **kwargs):
            obj = self._get_instance(*args, **kwargs)
            _schema = get_user_schedule_item_deserializer_schema(obj, self.request.user)
            if _schema:
                self.deserializer = _schema(context={"request": self.request, "obj": obj})
            return super().clean(validators=None, *args, **kwargs)

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    obj = self.database_model.objects.get(pk=id)
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
                if not obj.can_be_updated_by(self.request.user):
                    raise falcon.HTTPForbidden(title="You have no permission to update the resource!")
                if not self.request.user.is_superuser and obj.schedule.is_blocked:
                    raise falcon.HTTPForbidden(title="The schedule is blocked!")
                self._cached_instance = obj
            return self._cached_instance

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            instance = self._get_instance(id, *args, **kwargs)
            for key, val in data.items():
                setattr(instance, key, val)
            instance.save()
            instance.refresh_from_db()
            return instance


class UserSchedulesView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = UserSchedulesApiRequest
        serializer_schema = partial(UserScheduleApiResponse, many=True)
        database_model = UserSchedule
        _include_map = {
            "user_schedule_item": "user_schedule_items_included",
        }

        def _get_queryset(self, cleaned, *args, **kwargs):
            if "schedule_id" in kwargs:
                cleaned["schedule_id"] = kwargs["schedule_id"]
            return self.database_model.objects.get_paginated_results(user=self.request.user, **cleaned)


class ExportUrlView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"], save=True)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = UserScheduleItemsApiRequest
        serializer_schema = ExportUrlApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            export_format = kwargs["export_format"]
            base_url = self.request.relative_uri.split(f".{export_format}")[0]
            query_string = f"?{self.request.query_string}" if self.request.query_string else ""
            url = f"{settings.API_URL}{base_url}/{self.response._token}.{export_format}{query_string}"
            data = {
                "id": str(uuid.uuid4()),
                "url": url,
            }
            return namedtuple("export", "id url")(**data)


class UserSchedulesTabularView(TabularView):

    @falcon.before(login_required, roles=["admin", "agent"], restore_from="token")
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveTabularMixin, RetrieveManyHdlr):
        deserializer_schema = UserSchedulesApiRequest
        serializer_schema = partial(UserScheduleApiResponse, many=True)
        database_model = UserSchedule

        def _get_queryset(self, cleaned, *args, **kwargs):
            kwargs["user_schedule_id__in"] = self.database_model.objects.get_filtered_results(
                user=self.request.user.extra_agent_of or self.request.user,
                **cleaned,
            ).values_list("id", flat=True)
            return UserScheduleItem.objects.export(user=self.request.user, **kwargs)


class UserScheduleView(JsonAPIView):
    @falcon.before(login_required, roles=["admin", "agent"])
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["agent"])
    def on_patch(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PATCH, *args, **kwargs)

    @falcon.before(login_required, roles=["admin"])
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = UserScheduleApiRequest
        serializer_schema = UserScheduleApiResponse
        database_model = UserSchedule
        include_default = ["schedule", "user_schedule_item", "user"]

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            return self._get_instance(*args, **kwargs)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                query = {}
                if "id" in kwargs:
                    query["pk"] = kwargs["id"]
                if not self.request.user.is_superuser:
                    query["user"] = self.request.user.extra_agent_of or self.request.user
                if "id" not in kwargs:  # /auth/user_schedules/current
                    if self.request.user.is_superuser:
                        raise falcon.HTTPNotFound  # impossible get current user schedule for admin.
                    schedule = Schedule.get_current_plan()
                    if not schedule:
                        raise falcon.HTTPNotFound
                    query["schedule"] = schedule
                try:
                    self._cached_instance = self.database_model.objects.get(**query)
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

    class PATCH(UpdateOneHdlr):
        deserializer_schema = UpdateUserScheduleRequest
        serializer_schema = UserScheduleApiResponse
        database_model = UserSchedule

        def clean(self, id, *args, **kwargs):
            obj = self._get_instance(id, *args, **kwargs)
            self.deserializer = self.deserializer_schema(context={"request": self.request, "obj": obj})
            return super().clean(id, *args, validators=None, **kwargs)

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.database_model.objects.get(
                        pk=id,
                        user=self.request.user.extra_agent_of or self.request.user,
                    )
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            instance = self._get_instance(id, *args, **kwargs)
            for key, val in data.items():
                setattr(instance, key, val)
            instance.save()
            instance.refresh_from_db()
            return instance

    class POST(CreateOneHdlr):
        deserializer_schema = AdminCreateUserScheduleItemRequest
        serializer_schema = UserScheduleItemApiResponse
        database_model = UserScheduleItem

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = UserSchedule.objects.published().get(pk=kwargs["id"])
                except UserSchedule.DoesNotExist:
                    raise falcon.HTTPNotFound
                if self._cached_instance.schedule.state == "archival":
                    raise falcon.HTTPForbidden(title="You cannot add new item to archival schedule!")
            return self._cached_instance

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return super().clean(*args, **kwargs)

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            data["user_schedule"] = self._get_instance(*args, **kwargs)
            data["created_by"] = self.request.user
            self.response.context.data = self.database_model.create(**data)


class NotificationsView(JsonAPIView):

    @falcon.before(login_required, roles=["admin", "agent"])
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["admin", "agent"])
    def on_patch(self, request, response, *args, **kwargs):
        self.handle_bulk_patch(request, response, self.PATCH, *args, **kwargs)

    @falcon.before(login_required, roles=["admin"])
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = NotificationsApiRequest
        serializer_schema = partial(NotificationApiResponse, many=True)

        def _get_queryset(self, cleaned, *args, **kwargs):
            return self.request.user.notifications.get_paginated_results(**cleaned)

    class PATCH(UpdateManyHdlr):
        deserializer_schema = UpdateNotificationApiRequest
        database_model = Notification

        def _async_run(self, cleaned, *args, **kwargs):
            update_notifications_task.s(self.request.user.id, cleaned["data"]["attributes"]).apply_async()

    class POST(CreateOneHdlr):
        deserializer_schema = CreateNotificationsApiRequest
        serializer_schema = CreateNotificationsApiResponse
        database_model = Notification

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            send_admin_notification_task.s(data["message"], data["notification_type"]).apply_async()
            self.response.context.data = namedtuple("result", "id result success")(
                **{
                    "id": str(uuid.uuid4()),
                    "result": _("Notification was sent"),
                    "success": True,
                }
            )


class NotificationView(NotificationsView):

    @falcon.before(login_required, roles=["admin", "agent"])
    def on_patch(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PATCH, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = NotificationApiRequest
        serializer_schema = NotificationApiResponse

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.request.user.notifications.get(pk=id)
                except self.request.user.notifications.model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

    class PATCH(UpdateOneHdlr):
        database_model = Notification
        deserializer_schema = UpdateNotificationApiRequest
        serializer_schema = NotificationApiResponse

        def clean(self, *args, **kwargs):
            return super().clean(validators=None, *args, **kwargs)

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.database_model.objects.get(pk=id)
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
                if self._cached_instance not in self.request.user.notifications.all():
                    raise falcon.HTTPForbidden(title="You have no permission to update the resource.")
            return self._cached_instance

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            instance = self._get_instance(id, *args, **kwargs)
            for key, val in data.items():
                setattr(instance, key, val)
            instance.save()
            instance.refresh_from_db()
            return instance


class ScheduleView(JsonAPIView):
    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["admin"])
    def on_patch(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PATCH, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = ScheduleApiRequest
        serializer_schema = ScheduleApiResponse
        database_model = Schedule
        include_default = ["user_schedule", "user_schedule_item"]
        _includes = {
            "agent": "users.User",
            "user_schedule": "schedules.UserSchedule",
            "user_schedule_item": "schedules.UserScheduleItem",
        }

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                if "schedule_id" in kwargs:
                    instance = self.database_model.objects.filter(
                        pk=kwargs["schedule_id"],
                        status=self.database_model.STATUS.published,
                    ).first()
                else:
                    instance = self.database_model.get_current_plan()
                if not instance:
                    raise falcon.HTTPNotFound
                self._cached_instance = instance
            return self._cached_instance

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            return self._get_instance(*args, **kwargs)

        def _get_included_ids(self, result, field):
            user = self.request.user
            user = user.extra_agent_of or user if not user.is_superuser else None
            qs = None
            if field == "user_schedule_item":
                qs = result.user_schedule_items_included
                if user:
                    qs = qs.filter(user_schedule__user=user)
            elif field == "user_schedule":
                qs = result.user_schedules.all()
                if user:
                    qs = qs.filter(user=user)
            elif field == "agent":
                qs = result.total_agents if self.request.user.is_superuser else None
            return qs.values_list("id", flat=True) if qs else []

        def _get_include_params(self, field):
            params = super()._get_include_params(field)
            if field == "agent":
                params["order_by"] = ("agent_organization_main__title", "email")
            return params

    class PATCH(UpdateOneHdlr):
        database_model = Schedule
        serializer_schema = ScheduleApiResponse

        def clean(self, *args, **kwargs):
            obj = self._get_instance(*args, **kwargs)
            _schema = get_schedule_deserializer_schema(obj)
            if _schema:
                self.deserializer = _schema(context={"request": self.request, "obj": obj})
            return super().clean(obj.id, *args, validators=None, **kwargs)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                if "schedule_id" in kwargs:
                    instance = self.database_model.objects.filter(
                        pk=kwargs["schedule_id"],
                        status=self.database_model.STATUS.published,
                    ).first()
                else:
                    instance = self.database_model.get_current_plan()
                if not instance:
                    raise falcon.HTTPNotFound
                self._cached_instance = instance
            return self._cached_instance

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            instance = self._get_instance(*args, **kwargs)
            for key, val in data.items():
                setattr(instance, key, val)
            instance.save()
            instance.refresh_from_db()
            return instance


class ScheduleTabularView(TabularView):

    @falcon.before(login_required, roles=["admin", "agent"], restore_from="token")
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveTabularMixin, RetrieveManyHdlr):
        deserializer_schema = ScheduleApiRequest
        serializer_schema = ScheduleApiResponse
        database_model = UserScheduleItem

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                if "schedule_id" in kwargs:
                    instance = Schedule.objects.filter(pk=kwargs["schedule_id"], status=Schedule.STATUS.published).first()
                else:
                    instance = Schedule.get_current_plan()
                if not instance:
                    raise falcon.HTTPNotFound
                self._cached_instance = instance
            return self._cached_instance

        def _get_queryset(self, cleaned, *args, **kwargs):
            schedule = self._get_instance(*args, **kwargs)
            if schedule:
                cleaned["schedule_id"] = schedule.id
            return self.database_model.objects.export(user=self.request.user, **cleaned)


class SchedulesView(JsonAPIView):
    @falcon.before(login_required, roles=["admin", "agent"])
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required, roles=["admin"])
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        database_model = Schedule
        deserializer_schema = SchedulesApiRequest
        serializer_schema = partial(ScheduleApiResponse, many=True)

        def _get_queryset(self, cleaned, *args, **kwargs):
            return self.database_model.objects.get_paginated_results(**cleaned)

        def _get_included_ids(self, result, field):
            user = self.request.user
            user = user.extra_agent_of or user if not user.is_superuser else None
            result_ids = [x.id for x in result]
            qs = None
            if field == "user_schedule":
                query = {"schedule_id__in": result_ids}
                if user:
                    query["user"] = user
                qs = UserSchedule.objects.published().filter(**query)
            elif field == "user_schedule_item":
                query = {"user_schedule__schedule_id__in": result_ids}
                if user:
                    query["user_schedule__user"] = user
                qs = UserScheduleItem.objects.published().filter(**query)
            return qs.values_list("id", flat=True) if qs else []

    class POST(CreateOneHdlr):
        serializer_schema = ScheduleApiResponse
        database_model = Schedule

        def _get_data(self, cleaned, *args, **kwargs):
            try:
                self.response.context.data = self.database_model.create(created_by=self.request.user)
            except Exception as exc:
                raise falcon.HTTPForbidden(title=exc)
