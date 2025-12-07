from datetime import date
from typing import List

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from mcod.datasets.models import Dataset
from mcod.organizations.factories import OrganizationFactory
from mcod.organizations.models import Organization


class TestOrganizationModel:

    def test_organization_create(self):
        organization = Organization()
        organization.slug = "test"
        organization.title = "test"
        organization.postal_code = "00-001"
        organization.city = "Warszwa"
        organization.street = "Królewska"
        organization.street_number = "27"
        organization.flat_number = "1"
        organization.street_type = "ul"
        organization.email = "email@email.pl"
        organization.fax = "123123123"
        organization.tel = "123123123"
        organization.epuap = "epuap"
        organization.regon = "123123123"
        organization.website = "www.www.www"
        organization.electronic_delivery_address = "AE:PL-98765-43210-SFVYC-19"
        assert organization.id is None
        organization.save()
        assert organization.id is not None
        assert Organization.objects.last().id == organization.id

    def test_required_fields_validation(self):
        org = Organization()
        with pytest.raises(ValidationError) as e:
            org.full_clean()
        e = str(e.value)
        assert "'title'" in e
        assert "'postal_code'" in e
        assert "'city'" in e
        assert "'street'" in e
        assert "'street_type'" in e
        assert "'email'" in e
        assert "'fax'" in e
        assert "'tel'" in e
        assert "'epuap'" in e
        assert "'regon'" in e
        assert "'website'" in e

    def test_str(self, institution):
        institution.name = "test-name"
        institution.title = "Title"
        assert "Title" == str(institution)

    def test_str_no_title(self, institution):
        institution.slug = "test-name"
        institution.title = ""
        assert "test-name" == str(institution)

    def test_short_description(self):
        org = Organization()
        org.description = "<p>Paragraph</p>"
        assert "Paragraph" == org.short_description

    def test_short_description_no_description(self):
        org = Organization()
        org.description = None
        assert "" == org.short_description

    def test_image_url_and_path(self, institution):
        institution.image = SimpleUploadedFile("somefile.jpg", b"""1px""")
        institution.save()
        assert institution.image
        date_folder = date.today().isoformat().replace("-", "")
        image_name = institution.image.name
        assert institution.image.url == f"/media/images/organizations/{image_name}"
        assert institution.image.path == f"{settings.IMAGES_MEDIA_ROOT}/organizations/{image_name}"
        assert date_folder in institution.image.url
        assert date_folder in institution.image.path

    def test_organizations_datasets_count(self, institution_with_datasets):
        assert institution_with_datasets.datasets_count == 2

    def test_delete_organizations_also_delete_his_datasets(self, institution_with_datasets):
        datasets = list(institution_with_datasets.datasets.all())
        institution_with_datasets.delete()
        for dataset in datasets:
            assert dataset not in Dataset.objects.all()
            assert dataset in Dataset.trash.all()

    def test_changing_organization_to_draft_also_set_draft_for_his_datasets(self, institution_with_datasets):
        assert institution_with_datasets.status == "published"
        assert institution_with_datasets.datasets.first().status == "published"

        institution_with_datasets.status = "draft"
        institution_with_datasets.save()

        assert institution_with_datasets.status == "draft"
        assert institution_with_datasets.datasets.first().status == "draft"

    def test_changing_organization_to_published_didnt_publish_his_datasets(self, institution_with_datasets):
        institution = institution_with_datasets
        assert institution.status == "published"
        assert institution.datasets.first().status == "published"

        institution.status = "draft"
        institution.save()

        assert institution.status == "draft"
        assert institution.datasets.first().status == "draft"

        institution.status = "published"
        institution.save()

        assert institution.status == "published"
        assert institution.datasets.first().status == "draft"

    def test_image_absolute_url_without_lang(self, institution):
        institution.image = SimpleUploadedFile("somefile.jpg", b"""1px""")
        institution.save()
        assert institution.image_absolute_url == f"{settings.BASE_URL}{institution.image.url}"

    def test_default_eda(self, institution):
        assert institution.electronic_delivery_address is None

    def test_blank_eda_converted_to_none(self, institution):
        institution.electronic_delivery_address = ""
        institution.save()
        assert institution.electronic_delivery_address is None

    def test_blank_eda_violates_check_constraint_when_bulk_create(self):
        organizations: List[Organization] = OrganizationFactory.build_batch(size=3, electronic_delivery_address="")
        with pytest.raises(IntegrityError) as e:
            Organization.objects.bulk_create(organizations)

        assert "violates check constraint " '"electronic_delivery_address_not_empty_string"' in e.value.args[0]

    def test_blank_eda_violates_check_constraint_when_bulk_update(self):
        organizations: List[Organization] = OrganizationFactory.create_batch(size=3)
        organizations[0].electronic_delivery_address = ""
        with pytest.raises(IntegrityError) as e:
            Organization.objects.bulk_update(
                organizations,
                fields=[
                    "electronic_delivery_address",
                ],
            )

        assert "violates check constraint " '"electronic_delivery_address_not_empty_string"' in e.value.args[0]

    def test_create_many_organizations_same_eda(self):
        eda = "AE:PL-98765-43210-SFVYC-19"
        organizations: List[Organization] = OrganizationFactory.create_batch(
            electronic_delivery_address=eda,
            size=5,
        )

        assert all(eda == org.electronic_delivery_address for org in organizations)
