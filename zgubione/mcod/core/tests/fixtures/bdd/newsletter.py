import pytest

from mcod.newsletter.factories import NewsletterFactory


@pytest.fixture
def newsletter():
    return NewsletterFactory.create()
