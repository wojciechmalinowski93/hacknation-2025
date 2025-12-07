from unittest import mock

from django.db import transaction


def run_on_commit_events():
    conn = transaction.get_connection()
    while conn.run_on_commit:
        with mock.patch(
            "django.db.backends.base.base.BaseDatabaseWrapper.validate_no_atomic_block",
            lambda arg: False,
        ):
            conn.run_and_clear_commit_hooks()
