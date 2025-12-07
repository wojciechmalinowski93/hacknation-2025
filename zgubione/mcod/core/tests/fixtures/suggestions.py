import pytest

from mcod.suggestions.models import AcceptedDatasetSubmission, Suggestion


@pytest.fixture
def accepted_dataset_submission() -> AcceptedDatasetSubmission:
    return AcceptedDatasetSubmission.objects.create(
        decision="accepted",
        status="published",
        title="test title",
        notes="TEST NOTES",
        organization_name="TEST ORGANIZATION",
        is_active=True,
    )


@pytest.fixture
def public_accepted_dataset_submission() -> AcceptedDatasetSubmission:
    return AcceptedDatasetSubmission.objects.create(
        decision="accepted",
        status="published",
        title="public test title",
        notes="PUBLIC TEST NOTES",
        organization_name="TEST ORGANIZATION",
        is_published_for_all=True,
        is_active=True,
    )


@pytest.fixture
def suggestion() -> Suggestion:
    return Suggestion.objects.create(notes="test suggestion notes")
