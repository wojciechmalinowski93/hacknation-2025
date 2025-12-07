import json

from django.contrib.auth import get_user_model
from pytest_bdd import given, parsers, then, when

from mcod.core.tests.fixtures.bdd.common import create_object
from mcod.schedules.factories import (  # noqa
    NotificationFactory,
    ScheduleFactory,
    UserScheduleFactory,
    UserScheduleItemCommentFactory,
    UserScheduleItemFactory,
)
from mcod.schedules.tasks import send_schedule_notifications_task


@given(parsers.parse("{num:d} user schedule items with state {state}"))
def x_user_schedule_items(num, state):
    schedule = ScheduleFactory(state=state)
    user_schedule = UserScheduleFactory(schedule=schedule)
    return UserScheduleItemFactory.create_batch(num, user_schedule=user_schedule)


@given(parsers.parse("schedule data created with {params}"))
def schedule_data(context, params):  # noqa: C901
    kwargs = json.loads(params)

    schedule_id = kwargs.pop("schedule_id")
    schedule_state = kwargs.pop("schedule_state", None)
    schedule_is_blocked = kwargs.pop("schedule_is_blocked", None)
    user_id = kwargs.pop("user_id", None)
    user_schedule_id = kwargs.pop("user_schedule_id", None)
    user_schedule_is_ready = kwargs.pop("user_schedule_is_ready", None)
    user_schedule_item_id = kwargs.pop("user_schedule_item_id", None)
    recommendation_state = kwargs.pop("recommendation_state", None)
    comment_id = kwargs.pop("comment_id", None)
    notification_id = kwargs.pop("notification_id", None)

    schedule_kwargs = {}
    if schedule_state:
        schedule_kwargs["state"] = schedule_state
    if schedule_is_blocked:
        schedule_kwargs["is_blocked"] = schedule_is_blocked
    schedule = create_object("schedule", schedule_id, **schedule_kwargs, **kwargs)

    if user_schedule_id:
        user_schedule_kwargs = {"schedule": schedule}
        if user_id:
            user_schedule_kwargs["user"] = get_user_model().objects.get(pk=user_id)
        if user_schedule_is_ready is not None:
            user_schedule_kwargs["is_ready"] = user_schedule_is_ready
        user_schedule = create_object("user_schedule", user_schedule_id, **user_schedule_kwargs, **kwargs)

        if user_schedule_item_id:
            user_schedule_item_kwargs = {"user_schedule": user_schedule}
            if recommendation_state:
                user_schedule_item_kwargs["recommendation_state"] = recommendation_state
            user_schedule_item = create_object("user_schedule_item", user_schedule_item_id, **user_schedule_item_kwargs, **kwargs)
            if comment_id:
                comment_kwargs = {"user_schedule_item": user_schedule_item}
                if user_id:
                    comment_kwargs["created_by_id"] = user_id
                create_object("user_schedule_item_comment", comment_id, **comment_kwargs, **kwargs)
    if notification_id:
        notification_kwargs = {"actor": schedule, "recipient_id": context.user.id}
        NotificationFactory.create(id=notification_id, **notification_kwargs, **kwargs)


@when("send schedule notifications task")
def schedule_notifications_task_is_sent(context):
    context.send_schedule_notifications_task_result = send_schedule_notifications_task()


@then(parsers.parse("send schedule notifications task result is {result}"))
def schedule_notification_task_result(context, result):
    result = json.loads(result)
    assert context.send_schedule_notifications_task_result == result
