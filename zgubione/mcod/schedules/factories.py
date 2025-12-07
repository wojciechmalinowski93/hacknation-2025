import factory

from mcod.core.registries import factories_registry
from mcod.schedules import models
from mcod.users.factories import AdminFactory, AgentFactory


class ScheduleFactory(factory.django.DjangoModelFactory):
    start_date = factory.Faker("past_date", start_date="-60d")
    created_by = factory.SubFactory(AdminFactory)

    class Meta:
        model = models.Schedule


class UserScheduleFactory(factory.django.DjangoModelFactory):
    schedule = factory.SubFactory(ScheduleFactory)
    user = factory.SubFactory(AgentFactory)
    created_by = factory.SubFactory(AgentFactory)

    class Meta:
        model = models.UserSchedule


class UserScheduleItemFactory(factory.django.DjangoModelFactory):
    dataset_title = factory.Faker("company", locale="pl_PL")
    organization_name = factory.Faker("company", locale="pl_PL")
    user_schedule = factory.SubFactory(UserScheduleFactory)
    created_by = factory.SubFactory(AgentFactory)

    class Meta:
        model = models.UserScheduleItem


class UserScheduleItemCommentFactory(factory.django.DjangoModelFactory):
    text = "Test comment..."
    user_schedule_item = factory.SubFactory(UserScheduleItemFactory)
    created_by = factory.SubFactory(AgentFactory)

    class Meta:
        model = models.Comment


class NotificationFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Notification


factories_registry.register("schedule_notification", NotificationFactory)
factories_registry.register("schedule", ScheduleFactory)
factories_registry.register("user_schedule", UserScheduleFactory)
factories_registry.register("user_schedule_item", UserScheduleItemFactory)
factories_registry.register("user_schedule_item_comment", UserScheduleItemCommentFactory)
