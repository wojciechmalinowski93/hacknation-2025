import pytest

from mcod.suggestions.factories import DatasetSubmission


@pytest.fixture
def dataset_submission():
    return DatasetSubmission.create()
