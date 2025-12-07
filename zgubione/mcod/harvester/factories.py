import datetime

import factory

from mcod.categories.factories import CategoryFactory
from mcod.core.registries import factories_registry
from mcod.harvester.models import FREQUENCY_CHOICES, DataSource, DataSourceImport
from mcod.organizations.factories import (
    OrganizationFactory,
    PrivateOrganizationFactory,
    StateOrganizationFactory,
)
from mcod.organizations.models import Organization
from mcod.users.factories import AdminFactory


class DataSourceFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("text", max_nb_chars=80, locale="pl_PL")
    description = factory.Faker("paragraph", nb_sentences=5, locale="pl_PL")
    frequency_in_days = factory.Faker("random_element", elements=[x[0] for x in FREQUENCY_CHOICES])
    status = factory.Faker("random_element", elements=[x[0] for x in DataSource.STATUS_CHOICES])
    license_condition_db_or_copyrighted = factory.Faker("text", max_nb_chars=300, locale="pl_PL")
    institution_type = factory.Faker("random_element", elements=[x[0] for x in Organization.INSTITUTION_TYPE_CHOICES])
    source_type = factory.Faker("random_element", elements=[x[0] for x in DataSource.SOURCE_TYPE_CHOICES])
    created_by = factory.SubFactory(AdminFactory)

    class Meta:
        model = DataSource


class CKANDataSourceFactory(DataSourceFactory):
    source_type = "ckan"
    portal_url = factory.Faker("url")
    api_url = factory.Faker("url")
    category = factory.SubFactory(CategoryFactory)


class CKANDataSourceFactoryNoPrivateInstitution(DataSourceFactory):
    source_type = "ckan"
    portal_url = factory.Faker("url")
    api_url = factory.Faker("url")
    category = factory.SubFactory(CategoryFactory)
    institution_type = factory.Faker(
        "random_element",
        elements=[Organization.INSTITUTION_TYPE_STATE, Organization.INSTITUTION_TYPE_LOCAL, Organization.INSTITUTION_TYPE_OTHER],
    )


class XMLDataSourceFactory(DataSourceFactory):
    source_type = "xml"
    xml_url = factory.Faker("url")
    organization = factory.SubFactory(OrganizationFactory)


class XMLDataSourceOwnedByStateOrganizationFactory(XMLDataSourceFactory):
    organization = factory.SubFactory(StateOrganizationFactory)


class XMLDataSourceOwnedByPrivateOrganizationFactory(XMLDataSourceFactory):
    organization = factory.SubFactory(PrivateOrganizationFactory)


class DCATDataSourceFactory(DataSourceFactory):
    source_type = "dcat"
    api_url = factory.Faker("url")
    organization = factory.SubFactory(OrganizationFactory)
    sparql_query = "SELECT * WHERE {?s <some.uri/with/id> ?o}"


class DataSourceImportFactory(factory.django.DjangoModelFactory):
    start = factory.Faker("past_datetime", start_date="-30d", tzinfo=datetime.timezone.utc)
    datasource = factory.SubFactory(DataSourceFactory)

    class Meta:
        model = DataSourceImport


factories_registry.register("datasource", DataSourceFactory)
factories_registry.register("ckan_datasource", CKANDataSourceFactory)
factories_registry.register("ckan_datasource_no_private_institution", CKANDataSourceFactoryNoPrivateInstitution)
factories_registry.register("xml_datasource", XMLDataSourceFactory)
factories_registry.register("xml_datasource_owned_by_state_institution", XMLDataSourceOwnedByStateOrganizationFactory)
factories_registry.register("xml_datasource_owned_by_private_institution", XMLDataSourceOwnedByPrivateOrganizationFactory)
factories_registry.register("dcat_datasource", DCATDataSourceFactory)
factories_registry.register("datasourceimport", DataSourceImportFactory)
