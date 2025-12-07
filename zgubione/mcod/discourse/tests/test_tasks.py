from typing import TYPE_CHECKING

from mcod.discourse.tasks import user_logout_task, user_sync_task
from mcod.discourse.tests.utils import discourse_response_mocker

if TYPE_CHECKING:
    from mcod.users.models import User


def test_user_sync_task_deactivate_user(inactive_admin):
    with discourse_response_mocker(inactive_admin):
        result = user_sync_task(inactive_admin.pk)
    assert result == {"result": "ok"}


def test_user_sync_task_activate_user(admin):
    with discourse_response_mocker(admin):
        result = user_sync_task(admin.pk)
    admin.refresh_from_db()
    assert admin.discourse_user_name == "admin"
    assert admin.discourse_api_key == "1234567"
    assert result == {"result": "ok"}


def test_user_logout_task_skips_without_discourse_credentials(admin: "User"):
    with discourse_response_mocker(admin):
        result = user_logout_task(admin.pk)
    assert result == {"result": "ok, but skipping logout, no discourse credentials"}


def test_user_logout_task_with_discourse_credentials(admin_with_discourse_credentials: "User"):
    with discourse_response_mocker(admin_with_discourse_credentials):
        result = user_logout_task(admin_with_discourse_credentials.pk)
    assert result == {"result": "ok"}
