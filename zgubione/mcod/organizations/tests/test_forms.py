import copy

import pytest
from namedlist import namedlist

from mcod.lib.helpers import change_namedlist
from mcod.organizations.forms import OrganizationForm
from mcod.organizations.models import Organization

fields = [
    "slug",
    "title",
    "institution_type",
    "postal_code",
    "city",
    "street",
    "street_number",
    "flat_number",
    "street_type",
    "email",
    "fax",
    "tel",
    "epuap",
    "regon",
    "website",
    "status",
    "validity",
]

entry = namedlist("entry", fields)

empty = entry(
    slug=None,
    title=None,
    institution_type=None,
    postal_code=None,
    city=None,
    street=None,
    street_number=None,
    flat_number=None,
    street_type=None,
    email=None,
    fax=None,
    tel=None,
    epuap=None,
    regon=None,
    website=None,
    status=None,
    validity=False,
)

minimal = change_namedlist(
    empty,
    {
        "title": "Organization title",
        "slug": "organization-title",
        "institution_type": "local",
        "postal_code": "00-001",
        "city": "Warszawa",
        "street": "Królewska",
        "street_number": 1,
        "flat_number": 1,
        "street_type": "ul",
        "email": "r@wp.pl",
        "fax": "123123123",
        "tel": "123123123",
        "epuap": "123123123",
        "regon": "123456785",
        "website": "http://test.pl",
        "status": "draft",
        "validity": True,
    },
)

validity_false = change_namedlist(minimal, {"validity": False})

organization_form_data_requirement = {
    "title": ["Organization title", True],
    "slug": ["organization-title-2", False],
    "institution_type": ["local", True],
    "postal_code": ["00-001", True],
    "city": ["Warszawa", True],
    "street": ["Królewska", True],
    "street_number": [1, False],
    "flat_number": [1, False],
    "street_type": ["ul", True],
    "email": ["r@wp.pl", True],
    "fax": ["123123123", False],
    "tel": ["123123123", True],
    "epuap": ["123123123", False],
    "electronic_delivery_address": ["AE:PL-98765-43210-SFVYC-19", False],
    "regon": ["123456785", True],
    "website": ["http://test.pl", False],
    "status": ["draft", True],
}


class TestOrganizationFormValidity:
    """
    * - Not null fields:

    """

    @pytest.mark.parametrize(
        ", ".join(fields),
        [
            # correct scenarios
            minimal,  # minimal is full :)
            # incorrect scenarios
            # institution_type
            #   wrongo choice
            change_namedlist(
                validity_false,
                {"title": "Wrong institution type choice", "institution_type": "12345"},
            ),
            # postal_code
            #   wrong postal_code format
            change_namedlist(validity_false, {"postal_code": "12345"}),
            # city
            change_namedlist(
                validity_false,
                {
                    "title": "Too long city name",
                    "city": "a" * 201,
                },
            ),
            # street_type
            change_namedlist(
                validity_false,
                {
                    "title": "Too long street_type",
                    "street_type": "a" * 51,
                },
            ),
            # street_number
            change_namedlist(
                validity_false,
                {
                    "title": "Too long street_number",
                    "street_type": "a" * 201,
                },
            ),
            # flat_number
            change_namedlist(
                validity_false,
                {
                    "title": "Too long flat_number",
                    "street_type": "a" * 201,
                },
            ),
            # email
            change_namedlist(
                validity_false,
                {
                    "title": "Too long email",
                    "email": "a@" + "a" * 300 + ".pl",
                },
            ),
            change_namedlist(
                validity_false,
                {
                    "title": "Wrong email type",
                    "email": "a",
                },
            ),
            # regon
            change_namedlist(
                validity_false,
                {
                    "title": "Wrong regon",
                    "regon": "123456789",
                },
            ),
            # website
            change_namedlist(
                validity_false,
                {
                    "title": "Wrong website",
                    "website": "123456789",
                },
            ),
        ],
    )
    def test_dataset_form_validity(
        self,
        slug,
        title,
        institution_type,
        postal_code,
        city,
        street,
        street_number,
        flat_number,
        street_type,
        email,
        fax,
        tel,
        epuap,
        regon,
        website,
        status,
        validity,
    ):
        form = OrganizationForm(
            data={
                "slug": slug,
                "title": title,
                "institution_type": institution_type,
                "postal_code": postal_code,
                "city": city,
                "street": street,
                "street_number": street_number,
                "flat_number": flat_number,
                "street_type": street_type,
                "email": email,
                "fax": fax,
                "tel": tel,
                "epuap": epuap,
                "regon": regon,
                "website": website,
                "status": status,
            }
        )

        assert form.is_valid() is validity

    def test_create_and_save(self):
        data = {
            "title": "Organization title",
            "slug": "organization-title-1",
            "institution_type": "local",
            "postal_code": "00-001",
            "city": "Warszawa",
            "street": "Królewska",
            "street_number": 1,
            "flat_number": 1,
            "street_type": "ul",
            "email": "r@wp.pl",
            "fax": "123123123",
            "tel": "123123123",
            "epuap": "123123123",
            "regon": "123456785",
            "website": "http://test.pl",
            "status": "draft",
        }
        form = OrganizationForm(data=data)
        assert form.is_valid()
        form.save()
        last_ds = Organization.objects.last()
        assert last_ds.title == data["title"]

    def test_save_add_users_to_existing_organization(self, institution, active_editor):
        data = {
            "title": "Organization title",
            "slug": "organization-title-2",
            "institution_type": "local",
            "postal_code": "00-001",
            "city": "Warszawa",
            "street": "Królewska",
            "street_number": 1,
            "flat_number": 1,
            "street_type": "ul",
            "email": "r@wp.pl",
            "fax": "123123123",
            "tel": "123123123",
            "epuap": "123123123",
            "regon": "123456785",
            "website": "http://test.pl",
            "status": "draft",
            "users": [
                active_editor.id,
            ],
        }

        assert active_editor not in institution.users.all()
        form = OrganizationForm(data=data, instance=institution)
        assert form.instance.pk
        assert form.is_valid()
        saved_org = form.save(commit=False)
        assert active_editor in saved_org.users.all()

    def test_create_organization_and_add_users(self, active_editor):
        data = {
            "title": "Organization title",
            "slug": "organization-title-10",
            "institution_type": "local",
            "postal_code": "00-001",
            "city": "Warszawa",
            "street": "Królewska",
            "street_number": 1,
            "flat_number": 1,
            "street_type": "ul",
            "email": "r@wp.pl",
            "fax": "123123123",
            "tel": "123123123",
            "epuap": "123123123",
            "regon": "123456785",
            "website": "http://test.pl",
            "status": "draft",
            "users": [
                active_editor.id,
            ],
        }

        form = OrganizationForm(data=data)
        assert form.is_valid()
        saved_org = form.save()
        assert active_editor in saved_org.users.all()

    def test_add_users_to_unsaved_organization(self, active_editor):
        data = {
            "title": "Organization title",
            "slug": "organization-title",
            "institution_type": "local",
            "postal_code": "00-001",
            "city": "Warszawa",
            "street": "Królewska",
            "street_number": 1,
            "flat_number": 1,
            "street_type": "ul",
            "email": "r@wp.pl",
            "fax": "123123123",
            "tel": "123123123",
            "epuap": "123123123",
            "regon": "123456785",
            "website": "http://test.pl",
            "status": "draft",
            "users": [
                active_editor.id,
            ],
        }

        form = OrganizationForm(data=data)
        assert form.is_valid()
        saved_org = form.save(commit=False)
        with pytest.raises(ValueError):
            saved_org.users.all()

    @pytest.mark.parametrize(
        "tested_field, form_data",
        [
            (tested_field, copy.deepcopy(organization_form_data_requirement))
            for tested_field in organization_form_data_requirement.keys()
        ],
    )
    def test_organization_form_fields_requirement(self, tested_field, form_data):

        is_field_required = form_data[tested_field][1]
        del form_data[tested_field]

        form_data_for_test = {k: form_data[k][0] for k in form_data.keys()}

        form = OrganizationForm(data=form_data_for_test)
        if is_field_required:
            assert not form.is_valid()
        else:
            assert form.is_valid()
