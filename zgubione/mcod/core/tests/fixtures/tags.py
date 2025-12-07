import pytest

from mcod.tags.factories import TagFactory


@pytest.fixture
def tag():
    t = TagFactory.create()
    return t


@pytest.fixture
def tag_pl():
    t = TagFactory.create(language="pl")
    return t


@pytest.fixture
def tag_en():
    t = TagFactory.create(language="en")
    return t


@pytest.fixture
def fakenews_tag(admin):
    from mcod.tags.models import Tag

    return Tag.objects.create(name="fakenews", created_by=admin, modified_by=admin, status="published")


@pytest.fixture
def top50_tag(admin):
    from mcod.tags.models import Tag

    return Tag.objects.create(name="top50", created_by=admin, modified_by=admin, status="published")


@pytest.fixture
def analysis_tag(admin):
    from mcod.tags.models import Tag

    return Tag.objects.create(name="analysis", created_by=admin, modified_by=admin, status="published")
