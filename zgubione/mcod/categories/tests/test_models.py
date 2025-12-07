from django.utils import translation


class TestCategoryModel:
    def test_category_translations(self, db, organization_category):
        assert organization_category.title == "Moja kategoria"
        assert organization_category.slug == "moja-kategoria"
        assert organization_category.description == "Opis kategorii"

        translation.activate("en")
        assert organization_category.title_i18n == "My category"
        # Check if fallback lang working
        assert organization_category.description_i18n == "Opis kategorii"

        translation.activate("pl")
        assert organization_category.title_i18n == "Moja kategoria"
        assert organization_category.description_i18n == "Opis kategorii"

    def test_category_str(self, db, organization_category):
        translation.activate("pl")
        assert str(organization_category) == organization_category.title
