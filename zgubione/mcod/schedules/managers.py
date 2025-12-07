from notifications.base.models import NotificationQuerySet as BaseNotificationQuerySet

from mcod.core.db.managers import QuerySetMixin, TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet


class NotificationQuerySet(QuerySetMixin, BaseNotificationQuerySet):

    def get_filtered_results(self, **kwargs):
        unread = kwargs.get("unread")
        if unread is True:
            qs = self.unread()
        elif unread is False:
            qs = self.read()
        else:
            qs = self.filter()
        return qs


class ScheduleQuerySet(QuerySetMixin, SoftDeletableQuerySet):

    def published(self):
        return self.filter(status="published")

    def archival(self):
        return self.filter(state="archival")

    def implemented(self):
        return self.filter(state="implemented")

    def planned(self):
        return self.filter(state="planned")

    def get_filtered_results(self, **kwargs):
        sort = [x for x in kwargs.pop("sort", []) if x.lstrip("-") in ["created", "end_date", "id", "new_end_date"]]
        if not sort:
            sort = ["-end_date"]
        query = {}
        if "state" in kwargs:
            query["state"] = kwargs["state"]
        qs = self.published().filter(**query)
        return qs.order_by(*sort)


class CommentQuerySet(QuerySetMixin, SoftDeletableQuerySet):

    def get_filtered_results(self, **kwargs):
        sort = [x for x in kwargs.pop("sort", []) if x.lstrip("-") in ["created", "id"]]
        query = {}
        if "user_schedule_item" in kwargs:
            query["user_schedule_item"] = kwargs["user_schedule_item"]
        qs = self.published().filter(**query)
        return qs.order_by(*sort) if sort else qs

    def published(self):
        return self.filter(status="published")


class UserScheduleItemQuerySet(QuerySetMixin, SoftDeletableQuerySet):

    def get_filtered_results(self, **kwargs):
        sort = [x for x in kwargs.pop("sort", []) if x.lstrip("-") in ["created", "id", "institution"]]
        sort_map = {
            "institution": "organization_name",
            "-institution": "-organization_name",
        }
        sort = [sort_map.get(x, x) for x in sort]
        if not sort:
            sort = ["-created"]
        export = kwargs.get("export", False)
        full = kwargs.get("full", False)
        if export:
            sort = ["organization_name", "organization_unit"]

        user = kwargs.get("user")
        query = {}
        if user and not user.is_superuser:
            query["user_schedule__user"] = user.extra_agent_of or user
        if "user_schedule_id" in kwargs:
            query["user_schedule_id"] = kwargs["user_schedule_id"]
        if "schedule_id" in kwargs:
            query["user_schedule__schedule_id"] = kwargs["schedule_id"]
        if "state" in kwargs:
            query["user_schedule__schedule__state"] = kwargs["state"]
        if "q" in kwargs:
            query["dataset_title__trigram_similar"] = kwargs["q"]

        if export and user and user.is_superuser and not full:
            query["recommendation_state"] = "recommended"

        qs = self.published().filter(**query)
        if "exclude_id" in kwargs:
            qs = qs.exclude(id=kwargs["exclude_id"])
        return qs.order_by(*sort)

    def export(self, **kwargs):
        return self.get_filtered_results(export=True, **kwargs)

    def published(self):
        return self.filter(status="published")


class UserScheduleQuerySet(QuerySetMixin, SoftDeletableQuerySet):

    def get_filtered_results(self, **kwargs):
        is_ready = kwargs.get("is_ready")
        sort = [x for x in kwargs.pop("sort", []) if x.lstrip("-") in ["created", "email", "id", "institution"]]
        state = kwargs.get("state")
        user = kwargs.get("user")
        query = {}
        if isinstance(is_ready, bool):
            query["is_ready"] = is_ready
        if "schedule_id" in kwargs:
            query["schedule_id"] = kwargs["schedule_id"]
        if state:
            query["schedule__state"] = state
        if user and not user.is_superuser:
            query["user"] = user.extra_agent_of or user

        qs = self.filter(**query)

        sort_map = {
            "institution": "user__agent_organization_main__title",
            "-institution": "-user__agent_organization_main__title",
            "email": "user__email",
            "-email": "-user__email",
        }
        sort = [sort_map.get(x, x) for x in sort]
        if not sort:
            sort = ["user__agent_organization_main__title"]
        return qs.order_by(*sort)

    def published(self):
        return self.filter(status="published")


class BaseManagerMixin:
    def get_filtered_results(self, **kwargs):
        return super().get_queryset().get_filtered_results(**kwargs)

    def get_paginated_results(self, **kwargs):
        return super().get_queryset().get_paginated_results(**kwargs)


class CommentManagerMixin(BaseManagerMixin):
    _queryset_class = CommentQuerySet


class CommentManager(CommentManagerMixin, SoftDeletableManager):

    def published(self):
        return super().get_queryset().published()


class CommentTrashManager(CommentManagerMixin, TrashManager):
    pass


class ScheduleManagerMixin(BaseManagerMixin):
    _queryset_class = ScheduleQuerySet

    def archival(self):
        return super().get_queryset().archival()

    def implemented(self):
        return super().get_queryset().implemented()

    def planned(self):
        return super().get_queryset().planned()


class UserScheduleItemManagerMixin(BaseManagerMixin):
    _queryset_class = UserScheduleItemQuerySet

    def published(self):
        return super().get_queryset().published()

    def export(self, **kwargs):
        return super().get_queryset().export(**kwargs)


class UserScheduleManagerMixin(BaseManagerMixin):
    _queryset_class = UserScheduleQuerySet


class ScheduleManager(ScheduleManagerMixin, SoftDeletableManager):

    def published(self):
        return super().get_queryset().published()


class ScheduleTrashManager(ScheduleManagerMixin, TrashManager):
    pass


class UserScheduleItemManager(UserScheduleItemManagerMixin, SoftDeletableManager):
    pass


class UserScheduleItemTrashManager(UserScheduleItemManagerMixin, TrashManager):
    pass


class UserScheduleManager(UserScheduleManagerMixin, SoftDeletableManager):

    def published(self):
        return super().get_queryset().published()


class UserScheduleTrashManager(UserScheduleManagerMixin, TrashManager):
    pass
