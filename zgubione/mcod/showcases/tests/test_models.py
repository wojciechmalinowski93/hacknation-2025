from datetime import date

import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.db.models.query import QuerySet

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.showcases.models import Showcase, ShowcaseProposal


class TestShowcaseModel:
    def test_can_not_create_empty_showcase(self):
        with pytest.raises(ValidationError) as e:
            a = Showcase()
            a.full_clean()
        assert "'title'" in str(e.value)
        assert "'url'" in str(e.value)
        assert "'notes'" in str(e.value)

    def test_create_application(self):
        a = Showcase()
        a.category = "app"
        a.license_type = "free"
        a.slug = "test-name"
        a.title = "Test name"
        a.notes = "Treść"
        a.url = "http://smth.smwheere.com"
        assert a.full_clean() is None
        assert a.id is None
        a.save()
        assert a.id is not None
        assert a.status == "published"

    def test_add_dataset(self, showcase, dataset):
        showcase.datasets.set([dataset])
        assert showcase.full_clean() is None
        showcase.save()
        obj = Showcase.objects.get(id=showcase.id)
        assert dataset in obj.datasets.all()

    def test_add_tag(self, showcase, tag):
        showcase.tags.set([tag])
        assert showcase.full_clean() is None
        showcase.save()
        app = Showcase.objects.get(id=showcase.id)
        assert tag in app.tags.all()

    def test_showcase_has_proper_columns_and_relations(self, showcase):
        obj_dict = showcase.__dict__
        fields = [
            "id",
            "slug",
            "title",
            "notes",
            "author",
            "status",
            "modified",
            "created_by_id",
            "image",
            "created",
            "url",
        ]
        for f in fields:
            assert f in obj_dict
        assert isinstance(showcase.datasets.all(), QuerySet)
        assert isinstance(showcase.tags.all(), QuerySet)

    def test_safe_delete(self, showcase):
        assert showcase.status == "published"
        showcase.delete()
        assert showcase.is_removed is True
        with pytest.raises(ObjectDoesNotExist) as e:
            Showcase.objects.get(id=showcase.id)
        assert "Showcase matching query does not exist." in str(e.value)
        assert Showcase.raw.get(id=showcase.id)

    def test_unsafe_delete(self, showcase):
        assert showcase.status == "published"
        showcase.delete(soft=False)
        with pytest.raises(ObjectDoesNotExist) as e:
            Showcase.objects.get(id=showcase.id)
        assert "Showcase matching query does not exist." in str(e.value)

    def test_image_path_and_url(self, showcase, small_image):
        showcase.image = small_image
        showcase.save()
        run_on_commit_events()
        showcase.refresh_from_db()
        assert showcase.image
        assert showcase.image_thumb
        date_folder = date.today().isoformat().replace("-", "")
        image_name = showcase.image.name
        assert showcase.image.url == f"/media/showcases/{image_name}"
        assert showcase.image.path == f"{settings.SHOWCASES_MEDIA_ROOT}/{image_name}"
        assert date_folder in showcase.image.url
        assert date_folder in showcase.image.path

    def test_main_page_position_on_create(self):
        showcase1 = Showcase.objects.create(title="test showcase 1", notes="test description 1")
        assert showcase1.main_page_position is None, "main page position should be None if not specified"

    def test_main_page_position_no_duplicates(self):
        showcase1 = Showcase.objects.create(title="test showcase 1", notes="test description 1", main_page_position=1)
        assert showcase1.main_page_position == 1

        with pytest.raises(IntegrityError):
            Showcase.objects.create(
                title="test showcase 2",
                notes="test description 2",
                main_page_position=1,
            )

    def test_main_page_position_can_have_multiple_nones(self):
        showcase1 = Showcase.objects.create(title="test showcase 1", notes="test description 1", main_page_position=None)
        assert showcase1.main_page_position is None

        showcase2 = Showcase.objects.create(title="test showcase 2", notes="test description 2", main_page_position=None)
        assert showcase2.main_page_position is None

    def test_showcases_with_decision(self):
        obj = ShowcaseProposal.objects.create(
            title="test",
            notes="test",
            decision="accepted",
        )
        qs = ShowcaseProposal.objects.with_decision()
        assert obj in qs

    def test_showcases_without_decision(self):
        obj = ShowcaseProposal.objects.create(
            title="test",
            notes="test",
            decision="",
        )
        qs = ShowcaseProposal.objects.without_decision()
        assert obj in qs

    def test_showcaseproposal_cannot_be_converted_again(self):
        showcase = Showcase.objects.create(
            title="test showcase 1",
            notes="test description 1",
        )
        obj = ShowcaseProposal.objects.create(
            title="test",
            notes="test",
            decision="accepted",
            showcase=showcase,
        )
        assert not obj.convert_to_showcase()
