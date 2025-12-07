import pytest
from namedlist import namedlist

from mcod.lib.helpers import change_namedlist
from mcod.showcases.forms import ShowcaseForm
from mcod.showcases.models import Showcase

fields = [
    "title",
    "slug",
    "notes",
    "author",
    "status",
    "url",
    "image",
    "validity",
]

entry = namedlist("entry", fields)

minimal = entry(
    title="only required fields",
    slug="application-name",
    notes="notes",
    author=None,
    status="published",
    url="http://test.pl",
    image=None,
    validity=True,
)

full = entry(
    title="Full",
    slug="application-name",
    notes="notes",
    author="Someone",
    status="published",
    url="http://test.pl",
    image="/smth/smwhre/1.jpg",
    validity=True,
)


class TestApplicationFormValidity:
    """
    * - Not null fields:

    fields of application:

    id                  *   auto
    title               *
    slug                *   auto/manual - base on title
    notes               *
    author
    status               *   choices
    creator_user_id     *   auto
    url             *
    # date  -  odchodzimy od tego na rzecz TimeStampedModel
    image

    """

    @pytest.mark.parametrize(
        ", ".join(fields),
        [
            # correct scenarios
            minimal,
            full,
            #
            # incorect scenarios
            # title
            #   no title
            change_namedlist(minimal, {"title": None, "validity": False}),
            #   too long
            change_namedlist(minimal, {"title": "T" * 301, "validity": False}),
            # name                *   auto/manual - base on title
            #   no name
            change_namedlist(minimal, {"title": "no name", "slug": None, "validity": True}),
            #   too long name
            change_namedlist(
                minimal,
                {"title": "too long name", "slug": "T" * 601, "validity": False},
            ),
            # notes               *
            change_namedlist(minimal, {"title": "no notes", "notes": None, "validity": False}),
            # author
            #   author too long
            change_namedlist(
                minimal,
                {"title": "to long author", "author": "a" * 51, "validity": False},
            ),
            # status               *   choices
            #   No status choice
            change_namedlist(minimal, {"title": "no status", "status": None, "validity": False}),
            #   wrong choice value of status
            change_namedlist(minimal, {"title": "wrong status", "status": "XXX", "validity": False}),
            #   no app url
            change_namedlist(minimal, {"title": "no url", "url": None, "validity": False}),
            #   to long app_url
            change_namedlist(
                minimal,
                {
                    "title": "too long app url",
                    "url": "http://smth." + "a" * 300 + ".pl",
                    "validity": False,
                },
            ),
            #   wrong url format
            change_namedlist(
                minimal,
                {"title": "wrong url format", "url": "wrong format", "validity": False},
            ),
        ],
    )
    def test_application_form_validity(self, title, slug, notes, author, status, url, image, validity):
        form = ShowcaseForm(
            data={
                "category": "app",
                "license_type": "free",
                "title": title,
                "slug": slug,
                "notes": notes,
                "author": author,
                "status": status,
                "url": url,
                "image": image,
            }
        )
        assert form.is_valid() is validity

        if validity and title != "no name":
            form.save()
            assert Showcase.objects.last().title == title

    def test_showcase_form_add_datasets(self, dataset):
        form = ShowcaseForm(
            data={
                "category": "app",
                "license_type": "free",
                "title": "Test with dataset title",
                "slug": "test-with-dataset-title",
                "url": "http://test.pl",
                "notes": "tresc",
                "status": "published",
                "datasets": [dataset],
            }
        )
        assert form.is_valid() is True
        form.save()
        obj = Showcase.objects.last()
        assert obj.title == "Test with dataset title"
        assert dataset in obj.datasets.all()

    def test_showcase_form_add_invalid_datasets(self):
        form = ShowcaseForm(
            data={
                "category": "app",
                "license_type": "free",
                "title": "Test with dataset title",
                "slug": "test-with-dataset-title",
                "url": "http://test.pl",
                "notes": "tresc",
                "status": "published",
                "datasets": "aaaa",
            }
        )
        assert form.is_valid() is False
        assert form.errors == {"datasets": ["Podaj listę wartości."]}

    def test_showcase_form_add_tags(self, tag, tag_pl):
        data = {
            "category": "app",
            "license_type": "free",
            "title": "Test add tag",
            "slug": "test-add-tag",
            "url": "http://test.pl",
            "notes": "tresc",
            "status": "published",
            "tags_pl": [tag_pl.id],
        }

        form = ShowcaseForm(data=data)
        assert form.is_valid() is True
        form.save()
        assert not form.errors
        obj = Showcase.objects.last()
        assert obj.slug == "test-add-tag"
        assert tag_pl in obj.tags.all()
