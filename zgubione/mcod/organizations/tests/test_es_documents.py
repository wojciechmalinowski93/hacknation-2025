from typing import List

import pytest

from mcod.organizations.documents import InstitutionDocument


@pytest.mark.elasticsearch
def test_electronic_delivery_address_in_es_institution_document():
    required_institution_document_fields = [
        "image_url",
        "abbreviation",
        "postal_code",
        "city",
        "street_type",
        "street",
        "street_number",
        "flat_number",
        "email",
        "epuap",
        "fax",
        "tel",
        "electronic_delivery_address",
        "regon",
        "website",
        "institution_type",
        "published_datasets_count",
        "published_resources_count",
        "sources",
        "description",
        "published_datasets",
        "published_resources",
        "id",
        "model",
        "slug",
        "title",
        "title_synonyms",
        "title_exact",
        "notes",
        "notes_synonyms",
        "notes_exact",
        "keywords",
        "modified",
        "created",
        "verified",
        "search_date",
        "search_type",
        "status",
        "visualization_types",
        "subscriptions",
        "views_count",
    ]

    all_fields_from_document: List[str] = list(InstitutionDocument._doc_type.mapping.properties.properties.to_dict().keys())

    for required_field in required_institution_document_fields:
        assert required_field in all_fields_from_document
