import pytest
from _pytest.fixtures import FixtureRequest
from bs4 import BeautifulSoup
from django.db import models
from django.test import Client
from django.urls import reverse

from mcod.tags.models import Tag


def admin_url(model: models.Model, action: str, *args):
    """Build an admin URL for the given model and action (e.g., 'add', 'change', 'history')."""
    opts = model._meta
    return reverse(f"admin:{opts.app_label}_{opts.model_name}_{action}", args=args)


@pytest.fixture
def tag():
    return Tag.objects.create(name="OldName", language="en")


# -------- ADD permissions --------
@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_fixture, can_add",
    [
        ("active_editor", True),
        ("admin", True),
    ],
)
def test_add_permission_by_role(request: FixtureRequest, user_fixture: str, can_add: bool) -> None:
    """Verify who can add a Tag via the admin 'add' view."""
    user = request.getfixturevalue(user_fixture)
    client = Client()
    client.force_login(user)

    add_url = admin_url(Tag, "add") + "?lang=en"
    name = f"ParamTag-{user_fixture}"

    resp = client.post(add_url, {"name": name, "language": "en", "_save": "Save"}, follow=False)
    # after clicking "save", django redirects to other page (302). After click "save and stay", response code is 200
    if can_add:
        assert resp.status_code in (200, 302)
        assert Tag.objects.filter(name=name).exists()
    else:
        assert resp.status_code == 403
        assert not Tag.objects.filter(name=name).exists()


# -------- EDIT permissions --------
@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_fixture, can_edit",
    [
        ("active_editor", False),
        ("admin", True),
    ],
)
def test_edit_permission_by_role(request: FixtureRequest, tag: Tag, user_fixture: str, can_edit: bool) -> None:
    user = request.getfixturevalue(user_fixture)
    client = Client()
    client.force_login(user)

    change_url = admin_url(Tag, "change", tag.pk)
    resp = client.post(change_url, {"name": "NewName", "language": "en", "_save": "Save"}, follow=False)

    if can_edit:
        assert resp.status_code == 302
        tag.refresh_from_db()
        assert tag.name == "NewName"
    else:
        assert resp.status_code == 403
        tag.refresh_from_db()
        assert tag.name == "OldName"


# -------- HISTORY page permissions --------
@pytest.mark.parametrize(
    "user_fixture, expected_status",
    [
        ("active_editor", 403),
        ("admin", 200),
    ],
)
def test_history_access_by_role(request: FixtureRequest, tag: Tag, user_fixture: str, expected_status: int) -> None:
    """Parametrized history access: editor→redirect to change; admin→200 OK."""
    user = request.getfixturevalue(user_fixture)
    client = Client()
    client.force_login(user)

    history_url = admin_url(Tag, "history", tag.pk)
    resp = client.get(history_url, follow=False)
    assert resp.status_code == expected_status


# -------- Main page cases --------
@pytest.mark.parametrize(
    "user_fixture, history_link_visible_in_html",
    [
        ("active_editor", False),
        ("admin", True),
    ],
)
def test_history_link_visibility_by_role(
    request: FixtureRequest, user_fixture: str, history_link_visible_in_html: bool, tag: Tag
) -> None:
    user = request.getfixturevalue(user_fixture)
    client = Client()
    client.force_login(user)
    html = client.get(admin_url(Tag, "change", tag.pk)).content.decode()

    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("a.historylink")
    assert (link is not None) == history_link_visible_in_html


@pytest.mark.parametrize(
    "user_fixture, tag_list_button_visible_in_html",
    [
        ("active_editor", False),
        ("admin", True),
    ],
)
def test_index_tag_button_visibility_by_role(
    request: FixtureRequest, user_fixture: str, tag_list_button_visible_in_html: bool
) -> None:
    user = request.getfixturevalue(user_fixture)
    client = Client()
    client.force_login(user)
    html = client.get("/").content.decode()

    soup = BeautifulSoup(html, "html.parser")
    selector = "table.applist tr td.col-2 > a#TagChangeButton.changelink.icon"
    matches = soup.select(selector)

    present = len(matches) > 0
    assert present == tag_list_button_visible_in_html


@pytest.mark.parametrize(
    "user_fixture, resource_list_button_visible_in_html",
    [
        ("active_editor", True),
        ("admin", True),
    ],
)
def test_index_resource_button_visibility_by_role(
    request: FixtureRequest, user_fixture: str, resource_list_button_visible_in_html: bool
) -> None:
    user = request.getfixturevalue(user_fixture)
    client = Client()
    client.force_login(user)
    html = client.get("/").content.decode()
    soup = BeautifulSoup(html, "html.parser")
    selector = "table.applist tr td.col-2 > a#ResourceChangeButton.changelink.icon"
    matches = soup.select(selector)

    present = len(matches) > 0
    assert present == resource_list_button_visible_in_html
