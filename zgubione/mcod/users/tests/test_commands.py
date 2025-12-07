import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

User = get_user_model()


def test_createsuperuser_with_custom_user_model():
    call_command("createsuperuser", "--noinput", email="testsuperuser@test.com")

    superusers_count = User.objects.filter(email="testsuperuser@test.com").count()
    superuser = User.objects.get(email="testsuperuser@test.com")

    with pytest.raises(CommandError) as extinfo:
        call_command("createsuperuser", "--noinput", email="testsuperuser@test.com")
        assert "That Email is already taken" in str(extinfo.value)
    assert superusers_count == 1
    assert superuser.is_superuser
    assert superuser.state == "active"
