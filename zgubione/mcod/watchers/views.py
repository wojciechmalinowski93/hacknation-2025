from functools import partial

import falcon
from django.apps import apps

from mcod.core.api.handlers import (
    CreateOneHdlr,
    RemoveManyHdlr,
    RemoveOneHdlr,
    RetrieveManyHdlr,
    RetrieveOneHdlr,
    UpdateManyHdlr,
    UpdateOneHdlr,
)
from mcod.core.api.hooks import login_required
from mcod.core.api.jsonapi.serializers import SubscriptionQuerySchema
from mcod.core.api.views import JsonAPIView
from mcod.watchers.deserializers import (
    ChangeNotificationsStatus,
    ChangeNotificationStatus,
    DeleteNotifications,
    NotificationApiListRequest,
    NotificationApiRequest,
    SubscriptionApiRequest,
    SubscriptionCreateApiRequest,
    SubscriptionListApiRequest,
    SubscriptionUpdateApiRequest,
)
from mcod.watchers.models import DuplicateSubscriptionName, SubscribedObjectDoesNotExist
from mcod.watchers.serializers import NotificationApiResponse, SubscriptionApiResponse
from mcod.watchers.tasks import (
    remove_user_notifications_task,
    update_notifications_status_task,
    update_notifications_task,
)


class SubscriptionsView(JsonAPIView):
    @falcon.before(login_required)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        deserializer_schema = SubscriptionCreateApiRequest
        serializer_schema = partial(SubscriptionApiResponse, many=False)
        database_model = apps.get_model("watchers", "Subscription")

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            try:
                _inst = self.database_model.objects.get_from_data(self.request.user, data, headers=self.request.headers)
                raise falcon.HTTPForbidden(title="403 Forbidden", description="Subscription for this object already exist")
            except SubscribedObjectDoesNotExist:
                raise falcon.HTTPForbidden(title="403 Forbidden", description="Subscribed object does not exist")
            except self.database_model.DoesNotExist:
                try:
                    _inst = self.database_model.objects.create_from_data(self.request.user, data, headers=self.request.headers)
                except DuplicateSubscriptionName:
                    raise falcon.HTTPForbidden(title="403 Forbidden", description="Subscription with given name already exist")

            return _inst

        def _get_included(self, result, *args, **kwargs):
            return [result.to_jsonapi(api_version=getattr(self.request, "api_version", None))]

    class GET(RetrieveManyHdlr):
        deserializer_schema = SubscriptionListApiRequest
        serializer_schema = partial(SubscriptionApiResponse, many=True)
        database_model = apps.get_model("watchers", "Subscription")

        def _get_queryset(self, *args, **kwargs):
            return self.request.user.subscriptions.get_paginated_results(self.request.context.cleaned_data)

        def _get_included(self, result, *args, **kwargs):
            api_version = getattr(self.request, "api_version", None)
            return [_o.to_jsonapi(api_version=api_version) for _o in result.object_list]


class SubscriptionView(JsonAPIView):
    @falcon.before(login_required)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    def on_patch(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PATCH, *args, **kwargs)

    @falcon.before(login_required)
    def on_delete(self, request, response, *args, **kwargs):
        self.handle_delete(request, response, self.DELETE, *args, **kwargs)

    class PATCH(UpdateOneHdlr):
        deserializer_schema = partial(SubscriptionUpdateApiRequest)
        serializer_schema = partial(SubscriptionApiResponse, many=False)
        database_model = apps.get_model("watchers", "Subscription")

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            model = self.database_model
            try:
                return model.objects.update_from_data(id, self.request.user, data)
            except model.DoesNotExist:
                raise falcon.HTTPNotFound
            except DuplicateSubscriptionName:
                raise falcon.HTTPForbidden(title="403 Forbidden", description="Subscription with given name already exist")

        def _get_included(self, result, *args, **kwargs):
            return [result.to_jsonapi(api_version=getattr(self.request, "api_version", None))]

    class DELETE(RemoveOneHdlr):
        database_model = apps.get_model("watchers", "Subscription")

        def clean(self, id, *args, **kwargs):
            model = self.database_model
            try:
                return model.objects.get(pk=id, user=self.request.user)
            except model.DoesNotExist:
                raise falcon.HTTPNotFound

    class GET(RetrieveOneHdlr):
        deserializer_schema = partial(SubscriptionApiRequest)
        serializer_schema = partial(SubscriptionApiResponse, many=False)
        database_model = apps.get_model("watchers", "Subscription")

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                model = self.database_model
                try:
                    self._cached_instance = model.objects.get(pk=id, user=self.request.user, watcher__is_active=True)
                except model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_included(self, result, *args, **kwargs):
            return [result.to_jsonapi(api_version=getattr(self.request, "api_version", None))]


class SubscriptionNotificationsView(JsonAPIView):
    @falcon.before(login_required)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = partial(NotificationApiListRequest)
        serializer_schema = partial(NotificationApiResponse, many=True)
        database_model = apps.get_model("watchers", "Notification")

        def clean(self, id, *args, validators=None, locations=None, **kwargs):
            model = apps.get_model("watchers", "Subscription")

            try:
                model.objects.get(pk=id, user=self.request.user, watcher__is_active=True)
            except model.DoesNotExist:
                raise falcon.HTTPNotFound

            result = super().clean(*args, validators=validators, locations=locations, **kwargs)
            return result

        def _get_queryset(self, cleaned, id, *args, **kwargs):
            cleaned = self.request.context.cleaned_data
            result = self.database_model.objects.get_paginated_results(self.request.user, cleaned, subscription_id=id)
            return result

        def _get_included(self, result, *args, **kwargs):
            incl, ids = [], []
            for _o in result.object_list:
                watcher = _o.subscription.watcher
                if watcher.id in ids:
                    continue
                incl.append(_o.subscription.to_jsonapi(api_version=getattr(self.request, "api_version", None)))
                ids.append(watcher.id)
            return incl


class NotificationsView(JsonAPIView):
    @falcon.before(login_required)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    def on_patch(self, request, response, *args, **kwargs):
        self.handle_bulk_patch(request, response, self.PATCH, *args, **kwargs)

    @falcon.before(login_required)
    def on_delete(self, request, response, *args, **kwargs):
        self.handle_bulk_delete(request, response, self.DELETE, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = NotificationApiListRequest
        serializer_schema = partial(NotificationApiResponse, many=True)
        database_model = apps.get_model("watchers", "Notification")

        def _get_queryset(self, *args, **kwargs):
            return self.database_model.objects.get_paginated_results(
                self.request.user,
                self.request.context.cleaned_data,
            )

        def _get_included(self, result, *args, **kwargs):
            incl, ids = [], []
            api_version = getattr(self.request, "api_version", None)
            for _o in result.object_list:
                watcher = _o.subscription.watcher
                if watcher.id in ids:
                    continue
                if watcher.object_name == "query":
                    incl.append(SubscriptionQuerySchema(many=False, context={"api_version": api_version}).dump(_o.subscription))
                else:
                    incl.append(_o.subscription.to_jsonapi(api_version=api_version))
                ids.append(watcher.id)
            return incl

    class PATCH(UpdateManyHdlr):
        deserializer_schema = partial(ChangeNotificationsStatus)
        database_model = apps.get_model("watchers", "Notification")

        def _async_run(self, cleaned, *args, **kwargs):
            update_notifications_task.s(self.request.user.id, cleaned["data"]).apply_async()

    class DELETE(RemoveManyHdlr):
        database_model = apps.get_model("watchers", "Notification")
        deserializer_schema = partial(DeleteNotifications)

        def _async_run(self, cleaned, *args, **kwargs):
            remove_user_notifications_task.s(self.request.user.id, cleaned["data"]).apply_async()


class NotificationsStatusView(JsonAPIView):
    @falcon.before(login_required)
    def on_delete(self, request, response, *args, **kwargs):
        self.handle_bulk_delete(request, response, self.DELETE, *args, **kwargs)

    @falcon.before(login_required)
    def on_patch(self, request, response, *args, **kwargs):
        self.handle_bulk_patch(request, response, self.PATCH, *args, **kwargs)

    class DELETE(RemoveManyHdlr):
        database_model = apps.get_model("watchers", "Notification")

        def _async_run(self, cleaned, *args, **kwargs):
            update_notifications_status_task.s(self.request.user.id, status="read").apply_async()

    class PATCH(UpdateManyHdlr):
        database_model = apps.get_model("watchers", "Notification")

        def _async_run(self, cleaned, *args, **kwargs):
            update_notifications_status_task.s(self.request.user.id, status="new").apply_async()


class NotificationView(JsonAPIView):
    @falcon.before(login_required)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    def on_patch(self, request, response, *args, **kwargs):
        self.handle(request, response, self.PATCH, *args, **kwargs)

    @falcon.before(login_required)
    def on_delete(self, request, response, *args, **kwargs):
        self.handle_delete(request, response, self.DELETE, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = partial(NotificationApiRequest)
        serializer_schema = partial(NotificationApiResponse, many=False)
        database_model = apps.get_model("watchers", "Notification")

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                model = self.database_model
                try:
                    self._cached_instance = model.objects.get(pk=id, subscription__user_id=self.request.user.id)
                except model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_included(self, result, *args, **kwargs):
            return [result.subscription.to_jsonapi(api_version=getattr(self.request, "api_version", None))]

    class PATCH(UpdateOneHdlr):
        deserializer_schema = partial(ChangeNotificationStatus)
        serializer_schema = partial(NotificationApiResponse, many=False)
        database_model = apps.get_model("watchers", "Notification")

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                model = self.database_model
                try:
                    self._cached_instance = model.objects.get(pk=id, subscription__user=self.request.user)
                except model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            instance = self._get_instance(id, *args, **kwargs)
            model = self.database_model
            model.objects.filter(pk=id, subscription__user=self.request.user).update(**data)
            instance.refresh_from_db()
            return instance

    class DELETE(RemoveOneHdlr):
        database_model = apps.get_model("watchers", "Notification")

        def clean(self, id, *args, **kwargs):
            model = self.database_model
            try:
                return model.objects.get(pk=id, subscription__user=self.request.user)
            except model.DoesNotExist:
                raise falcon.HTTPNotFound
