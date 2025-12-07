import pytest

from mcod.categories.factories import CategoryFactory


@pytest.fixture
def organization_category():
    cat = CategoryFactory.create(title="Moja kategoria", title_en="My category", description="Opis kategorii")
    return cat


@pytest.fixture
def categories():
    categories = CategoryFactory.create_batch(3)
    return categories


@pytest.fixture
def journalism_category(admin):
    from mcod.categories.models import Category

    return Category.objects.create(
        slug="Dziennikarstwo",
        title="Dziennikarstwo",
        title_en="Journalism",
        description="Różnego rodzaju analizy i statystyki związane z dziennikarstwem.",
        description_en="Various analysis, statistics and data related to journalism.",
        created_by=admin,
        modified_by=admin,
        status="published",
    )
