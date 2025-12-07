from django.conf import settings

from mcod.discourse import tasks


def user_logout(signal, request, user, **kwargs):
    if settings.DISCOURSE_FORUM_ENABLED:
        tasks.user_logout_task.s(user.id).apply_async()
