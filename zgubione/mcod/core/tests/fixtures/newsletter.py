import pytest

from mcod.newsletter.models import Subscription


@pytest.fixture
def newsletter_subscription():
    return Subscription.objects.create(email="test@mcod.test", lang="en")
