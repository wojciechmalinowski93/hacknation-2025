from django.utils.translation import gettext_lazy as _

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import (
    Aggregation,
    HighlightObjectMixin,
    ObjectAttrs,
    Relationship,
    Relationships,
    TopLevel,
)
from mcod.core.api.schemas import ExtSchema
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer
from mcod.lib.serializers import TranslatedStr
from mcod.watchers.serializers import SubscriptionMixin


class InstitutionApiRelationships(Relationships):
    published_datasets = fields.Nested(
        Relationship,
        many=False,
        default=[],
        data_key="datasets",
        _type="dataset",
        url_template="{object_url}/datasets",
        required=True,
    )
    published_resources = fields.Nested(
        Relationship,
        many=False,
        default=[],
        data_key="resources",
        _type="resource",
        required=True,
    )
    subscription = fields.Nested(
        Relationship,
        many=False,
        _type="subscription",
        url_template="{api_url}/auth/subscriptions/{ident}",
    )


class InstitutionApiAggs(ExtSchema):
    by_created = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_created.by_created.buckets",
    )
    by_modified = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_modified.by_modified.buckets",
    )
    by_city = fields.Nested(Aggregation, many=True, attribute="_filter_by_city.by_city.buckets")
    by_institution_type = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_institution_type.by_institution_type.buckets",
    )


class DataSourceAttr(ExtSchema):
    title = fields.Str()
    url = fields.URL()
    source_type = fields.Str()


class InstitutionApiAttrs(ObjectAttrs, HighlightObjectMixin):
    abbreviation = fields.Str()
    city = fields.Str()
    created = fields.Str()
    email = fields.Str()
    epuap = fields.Str()
    fax = fields.Str()
    electronic_delivery_address = fields.Str()
    flat_number = fields.Str()
    followed = fields.Boolean()
    image_url = fields.Str()
    institution_type = fields.Str()
    modified = fields.Str()
    description = TranslatedStr()
    notes = TranslatedStr()
    postal_code = fields.Str()
    regon = fields.Str()
    slug = TranslatedStr()
    sources = fields.Nested(DataSourceAttr, many=True)
    street = fields.Str()
    street_number = fields.Str()
    street_type = fields.Str()
    tel = fields.Str()
    title = TranslatedStr()
    website = fields.Str()

    class Meta:
        relationships_schema = InstitutionApiRelationships
        object_type = "institution"
        url_template = "{api_url}/institutions/{ident}"
        model = "organizations.Organization"


class InstitutionApiResponse(SubscriptionMixin, TopLevel):
    class Meta:
        attrs_schema = InstitutionApiAttrs
        aggs_schema = InstitutionApiAggs


class InstitutionCSVSchema(CSVSerializer, metaclass=CSVSchemaRegistrator):
    id = fields.Integer(data_key=_("id"), required=True)
    title = fields.Str(data_key=_("Title"), default="")
    institution_type = fields.Str(data_key=_("Institution type"), default="")
    datasets_count = fields.Int(data_key=_("The number of datasets"), default=None)

    class Meta:
        ordered = True
        model = "organizations.Organization"


class InstitutionXMLSerializer(ExtSchema):
    id = fields.Integer()
    url = fields.Url(attribute="frontend_absolute_url")
    type = fields.Function(lambda organization: organization.get_institution_type_display())
    title = TranslatedStr()
    abbreviation = fields.Str()
    epuap = fields.Str()
    website = fields.Url()
    created = fields.DateTime(format="iso8601")
    modified = fields.DateTime(format="iso8601")

    postal_code = fields.Str()
    city = fields.Str()
    street = fields.Str()
    street_number = fields.Str()
    street_type = fields.Str()
    flat_number = fields.Str()

    email = fields.Str()
    tel = fields.Str(data_key="phone_number")

    regon = fields.Str()

    published_datasets_count = fields.Method("get_published_datasets_count")
    published_resources_count = fields.Method("get_published_resources_count")

    def get_published_datasets_count(self, organization):
        return self.context["published_datasets_count"]

    def get_published_resources_count(self, organization):
        return self.context["published_resources_count"]


class InstitutionCSVMetadataSerializer(ExtSchema):
    organization_url = fields.Url(attribute="frontend_absolute_url", data_key=_("Organization URL"))
    organization_type = fields.Function(lambda obj: obj.get_institution_type_display(), data_key=_("Institution type"))
    organization_title = TranslatedStr(attribute="title", data_key=_("Name"))
    organization_abbr_title = TranslatedStr(attribute="abbreviation", data_key=_("Abbreviation"), default="")
    organization_id = fields.Str(attribute="id", data_key=_("Id Institution"))
    organization_regon = fields.Str(data_key=_("REGON"), attribute="regon")
    organization_epuap = fields.Str(attribute="epuap", data_key=_("EPUAP"), default="")
    organization_electronic_delivery_address = fields.Str(
        attribute="electronic_delivery_address",
        data_key=_("Address for electronic delivery"),
    )
    organization_website = fields.Url(attribute="website", data_key=_("Website"))
    organization_created = fields.DateTime(attribute="created", data_key=_("Organization created"), format="iso8601")
    organization_modified = fields.DateTime(attribute="modified", data_key=_("Organization modified"), format="iso8601")
    organization_datasets_count = fields.Method("get_published_datasets_count", data_key=_("Number of datasets"))
    organization_resources_count = fields.Method("get_published_resources_count", data_key=_("Number of organization resources"))
    organization_postal_code = fields.Str(attribute="postal_code", data_key=_("Postal code"))
    organization_city = fields.Str(attribute="city", data_key=_("City"))
    organization_street_type = fields.Str(attribute="street_type", data_key=_("Street type"))
    organization_street = fields.Str(attribute="street", data_key=_("Street"))
    organization_street_number = fields.Str(attribute="street_number", data_key=_("Street number"))
    organization_flat_number = fields.Str(attribute="flat_number", data_key=_("Flat number"))
    organization_email = fields.Email(attribute="email", data_key=_("Email"))
    organization_phone_number = fields.Str(attribute="tel", data_key=_("Phone"))

    class Meta:
        ordered = True

    def get_published_datasets_count(self, organization):
        return self.context["published_datasets_count"]

    def get_published_resources_count(self, organization):
        return self.context["published_resources_count"]
