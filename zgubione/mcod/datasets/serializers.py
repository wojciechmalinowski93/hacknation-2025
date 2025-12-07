import marshmallow as ma
from django.apps import apps
from django.db.models.manager import Manager
from django.utils.html import strip_tags
from django.utils.translation import get_language, gettext_lazy as _
from querystring_parser import builder

from mcod import settings
from mcod.core.api import fields, schemas
from mcod.core.api.jsonapi.serializers import (
    Aggregation,
    ExtAggregation,
    HighlightObjectMixin,
    ObjectAttrs,
    Relationship,
    Relationships,
    TopLevel,
)
from mcod.core.api.rdf import fields as rdf_fields
from mcod.core.api.rdf.profiles.common import HYDRAPagedCollection
from mcod.core.api.rdf.schema_mixins import ProfilesMixin
from mcod.core.api.rdf.schemas import ResponseSchema as RDFResponseSchema
from mcod.core.api.schemas import ExtSchema
from mcod.core.choices import SOURCE_TYPE_CHOICES_FOR_ADMIN
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer, ListWithoutNoneStrElement
from mcod.datasets.models import UPDATE_FREQUENCY
from mcod.lib.extended_graph import ExtendedGraph
from mcod.lib.serializers import KeywordsList, TranslatedStr
from mcod.organizations.serializers import (
    InstitutionCSVMetadataSerializer,
    InstitutionXMLSerializer,
)
from mcod.regions.serializers import RDFRegionSchema, RegionBaseSchema, RegionSchema
from mcod.resources.serializers import (
    ResourceCSVMetadataSerializer,
    ResourceRDFMixin,
    ResourceXMLSerializer,
    SupplementSchema,
    supplements_dump,
)
from mcod.watchers.serializers import SubscriptionMixin

_UPDATE_FREQUENCY = dict(UPDATE_FREQUENCY)

Organization = apps.get_model("organizations", "Organization")
Category = apps.get_model("categories", "Category")
Dataset = apps.get_model("datasets", "Dataset")


UPDATE_FREQUENCY_TO_DCAT_PREFIX = "http://publications.europa.eu/resource/authority/frequency/"
UPDATE_FREQUENCY_TO_DCAT = {
    "notApplicable": "UNKNOWN",
    "yearly": "ANNUAL",
    "everyHalfYear": "ANNUAL_2",
    "quarterly": "QUARTERLY",
    "monthly": "MONTHLY",
    "weekly": "WEEKLY",
    "daily": "DAILY",
    "irregular": "IRREG",
    "notPlanned": "NOT_PLANNED",
}


class CategoryRDFNestedSchema(ProfilesMixin, ma.Schema):
    code = ma.fields.Str()
    title_pl = ma.fields.Str(attribute="title_translated.pl")
    title_en = ma.fields.Str(attribute="title_translated.en")


class ResourceRDFNestedSchema(ResourceRDFMixin, ma.Schema):
    pass


class DatasetOrganization:
    def __init__(self, dataset):
        self.org = dataset.organization
        self.dataset = dataset

    def __getattr__(self, item):
        if item == "dataset":
            return self.dataset
        else:
            return getattr(self.org, item)


class OrganizationRDFMixin(ProfilesMixin):
    id = ma.fields.Str(attribute="id")
    access_url = ma.fields.Str(attribute="frontend_absolute_url")
    title_pl = ma.fields.Str(attribute="title_translated.pl")
    title_en = ma.fields.Str(attribute="title_translated.en")
    email = ma.fields.Str()
    regon = ma.fields.Str()


class OrganizationRDFNestedSchema(OrganizationRDFMixin, ma.Schema):
    dataset_frontend_absolute_url = ma.fields.Function(lambda o: o.dataset.frontend_absolute_url)


def resources_dump(dataset, context):
    return ResourceRDFNestedSchema(many=True, context=context).dump(dataset.resources.filter(status="published"))


def organization_dump(dataset, context):
    return OrganizationRDFNestedSchema(many=False, context=context).dump(DatasetOrganization(dataset))


def categories_dump(dataset, context):
    context = {**context, "dataset_uri": dataset.frontend_absolute_url}
    return CategoryRDFNestedSchema(many=True, context=context).dump(dataset.categories.all())


class DcatUpdateFrequencyField(fields.String):
    @fields.after_serialize
    def to_dcat(self, value=None):
        dcat_value = UPDATE_FREQUENCY_TO_DCAT.get(value)
        if dcat_value:
            dcat_value = f"{UPDATE_FREQUENCY_TO_DCAT_PREFIX}{dcat_value}"
        return dcat_value


class DatasetRDFResponseSchema(ProfilesMixin, RDFResponseSchema):
    identifier = ma.fields.Function(lambda ds: ds.frontend_absolute_url)
    id = ma.fields.Str()
    frontend_absolute_url = ma.fields.Str()
    title_pl = ma.fields.Str(attribute="title_translated.pl")
    title_en = ma.fields.Str(attribute="title_translated.en")
    notes_pl = ma.fields.Str(attribute="notes_translated.pl")
    notes_en = ma.fields.Str(attribute="notes_translated.en")
    status = ma.fields.Str()
    created = ma.fields.DateTime()
    modified = ma.fields.DateTime()
    landing_page = fields.Function(lambda ds: ds.frontend_absolute_url)
    version = ma.fields.Str()
    tags = rdf_fields.Tags(ma.fields.Str())
    resources = ma.fields.Function(resources_dump)
    organization = ma.fields.Function(organization_dump)
    categories = ma.fields.Function(categories_dump)
    supplements = ma.fields.Function(supplements_dump)
    update_frequency = DcatUpdateFrequencyField()
    license = ma.fields.Function(lambda ds: ds.license_link)
    logo = ma.fields.Str(attribute="image_absolute_url")
    spatial = ma.fields.Nested(RDFRegionSchema, many=True, attribute="regions")

    @staticmethod
    def _from_path(es_resp, path):
        try:
            obj = es_resp
            for step in path.split("."):
                obj = getattr(obj, step)
            return obj
        except AttributeError:
            return None

    @ma.pre_dump(pass_many=True)
    def extract_pagination(self, data, many, **kwargs):
        request = self.context["request"] if "request" in self.context else None
        cleaned_data = dict(getattr(request.context, "cleaned_data", {})) if request else {}

        def _get_page_link(page_number):
            cleaned_data["page"] = page_number
            return "{}{}?{}".format(settings.API_URL, request.path, builder.build(cleaned_data))

        if self.many:
            page, per_page = cleaned_data.get("page", 1), cleaned_data.get("per_page", 20)
            self.context["count"] = self._from_path(data, "hits.total")
            self.context["per_page"] = per_page

            items_count = self._from_path(data, "hits.total")
            if page > 1:
                self.context["first_page"] = _get_page_link(1)
                self.context["prev_page"] = _get_page_link(page - 1)
            if items_count:
                max_count = min(items_count, 10000)
                off = 1 if max_count % per_page else 0
                last_page = max_count // per_page + off
                if last_page > 1:
                    self.context["last_page"] = _get_page_link(last_page)
                if page * per_page < max_count:
                    self.context["next_page"] = _get_page_link(page + 1)

        return data

    @ma.pre_dump(pass_many=True)
    def prepare_datasets(self, data, many, **kwargs):
        self.context["dataset_refs"] = []
        if self.many:
            self.context["catalog_modified"] = self._from_path(data, "aggregations.catalog_modified.value_as_string")
            dataset_ids = [x.id for x in data]
            data = Dataset.objects.filter(pk__in=dataset_ids)
        return data

    @ma.post_dump(pass_many=False)
    def prepare_graph_triples(self, data, **kwargs):
        self.context["dataset_refs"].append(data["frontend_absolute_url"])
        dataset = self.get_rdf_class_for_model(model=Dataset)()
        return dataset.to_triples(data, self.include_nested_triples)

    @ma.post_dump(pass_many=True)
    def prepare_graph(self, data, many, **kwargs):
        graph = ExtendedGraph(ordered=True)
        self.add_bindings(graph=graph)

        # Jeżeli many == True, to serializujemy katalog.
        if many:
            triples = []
            # Dla katalogu, w data, mamy listę list, trzeba to spłaszczyć.
            for _triples in data:
                triples.extend(_triples)

            self.add_pagination_bindings(graph=graph)
            paged_collection = HYDRAPagedCollection()
            triples.extend(paged_collection.to_triples(self.context))
            catalog = self.get_rdf_class_for_catalog()()
            triples.extend(catalog.to_triples(self.context))
        else:
            triples = data
        for triple in triples:
            graph.add(triple)
        return graph

    class Meta:
        model = "datasets.Dataset"


class DatasetCategoryAttr(ExtSchema):
    id = fields.Str()
    title = TranslatedStr()
    code = fields.Str()

    @ma.pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        if isinstance(data, Manager):
            data = data.all()
        return data


class LicenseConditionDescriptionSchema(ExtSchema):
    license_condition_db_or_copyrighted = fields.Str()
    license_condition_personal_data = fields.Str()
    license_condition_modification = fields.Str()
    license_condition_responsibilities = fields.Str()
    license_condition_cc40_responsibilities = fields.Str()
    license_condition_source = fields.Str()
    license_condition_custom_description = fields.Str()
    license_condition_default_cc40 = fields.Str()


class SourceSchema(ExtSchema):
    title = fields.Str()
    type = fields.Str(attribute="source_type")
    url = fields.URL()
    update_frequency = TranslatedStr()
    last_import_timestamp = fields.DateTime()


class SourceXMLSchema(ExtSchema):
    title = fields.Str()
    url = fields.URL()
    update_frequency = TranslatedStr()
    last_import_timestamp = fields.DateTime()


class TransUpdateFreqField(fields.String):
    @fields.after_serialize
    def translate(self, value=None):
        if value:
            value = str(_(_UPDATE_FREQUENCY[value]))
        return value


class InstitutionAggregation(ExtAggregation):
    class Meta:
        model = "organizations.Organization"
        title_field = "title_i18n"


class CategoryAggregation(ExtAggregation):
    class Meta:
        model = "categories.Category"
        title_field = "title_i18n"


class LicenseAggregation(schemas.ExtSchema):
    id = fields.String(attribute="key")
    title = fields.String()
    doc_count = fields.Integer()

    @ma.pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        if many:
            for item in data:
                item["title"] = Dataset.LICENSE_CODE_TO_NAME.get(item.key)
        return data


class UpdateFrequencyAggregation(schemas.ExtSchema):
    id = fields.String(attribute="key")
    title = fields.String()
    doc_count = fields.Integer()

    @ma.pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        if many:
            for item in data:
                item["title"] = _UPDATE_FREQUENCY.get(item.key)
        return data


class BoolDataAggregation(schemas.ExtSchema):
    id = fields.String(attribute="key_as_string")
    title = fields.String()
    doc_count = fields.Integer()

    @ma.post_dump(pass_many=True)
    def ensure_keys(self, data, many, **kwargs):
        only_true = self.context.get("only_true", False)
        val_dict = {"false": _("No"), "true": _("Yes")}
        if many:
            values = [x["id"] for x in data]
            if "false" not in values:
                data.append({"id": "false", "doc_count": 0})
            if "true" not in values:
                data.append({"id": "true", "doc_count": 0})
            for item in data:
                item["title"] = str(val_dict.get(item["id"]))
            data = [x for x in data if x["id"] == "true"] if only_true else data
        return data


class DatasetApiAggregations(ExtSchema):
    by_created = fields.Nested(Aggregation, many=True, attribute="_filter_by_created.by_created.buckets")
    by_modified = fields.Nested(Aggregation, many=True, attribute="_filter_by_modified.by_modified.buckets")
    by_verified = fields.Nested(Aggregation, many=True, attribute="_filter_by_verified.by_verified.buckets")
    by_format = fields.Nested(Aggregation, many=True, attribute="_filter_by_format.by_format.buckets")
    by_institution = fields.Nested(
        InstitutionAggregation,
        many=True,
        attribute="_filter_by_institution.by_institution.inner.buckets",
    )
    by_types = fields.Nested(Aggregation, many=True, attribute="_filter_by_types.by_types.buckets")
    by_visualization_types = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_visualization_types.by_visualization_types.buckets",
    )
    by_category = fields.Nested(
        CategoryAggregation,
        many=True,
        attribute="_filter_by_category.by_category.inner.buckets",
    )
    by_categories = fields.Nested(
        CategoryAggregation,
        many=True,
        attribute="_filter_by_categories.by_categories.inner.buckets",
    )
    by_openness_score = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_openness_score.by_openness_score.buckets",
    )
    by_tag = fields.Nested(Aggregation, many=True, attribute="_filter_by_tag.by_tag.inner.buckets")
    by_keyword = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_keyword.by_keyword.inner.inner.buckets",
    )


class DatasetApiRelationships(Relationships):
    institution = fields.Nested(
        Relationship,
        many=False,
        _type="institution",
        path="institutions",
        url_template="{api_url}/institutions/{ident}",
    )
    resources = fields.Nested(
        Relationship,
        many=False,
        default=[],
        _type="resource",
        url_template="{object_url}/resources",
    )
    showcases = fields.Nested(
        Relationship,
        many=False,
        default=[],
        _type="showcase",
        url_template="{object_url}/showcases",
    )
    subscription = fields.Nested(
        Relationship,
        many=False,
        _type="subscription",
        url_template="{api_url}/auth/subscriptions/{ident}",
    )

    def filter_data(self, data, **kwargs):
        if not self.context.get("is_listing", False):
            if "resources" in data:
                data["resources"] = data["resources"].filter(status="published")
            if "showcases" in data:
                data["showcases"] = data["showcases"].filter(status="published")
        return data


class DatasetApiAttrs(ObjectAttrs, HighlightObjectMixin):
    title = TranslatedStr()
    slug = TranslatedStr()
    notes = TranslatedStr()
    categories = fields.Nested(DatasetCategoryAttr, many=True)
    category = fields.Nested(DatasetCategoryAttr, many=False)
    formats = fields.List(fields.String())
    types = fields.List(fields.String())
    keywords = KeywordsList(TranslatedStr())
    openness_scores = fields.List(fields.Int())
    license_chosen = fields.Integer()
    license_condition_db_or_copyrighted = fields.String()
    license_condition_personal_data = fields.String()
    license_condition_original = fields.Boolean()
    license_condition_timestamp = fields.Boolean()
    license_condition_custom_description = fields.String()
    license_condition_default_cc40 = fields.Boolean()
    license_name = fields.String()
    license_description = fields.String()
    update_frequency = TransUpdateFreqField()
    views_count = fields.Int(attribute="computed_views_count")
    downloads_count = fields.Int(attribute="computed_downloads_count")
    url = fields.String()
    followed = fields.Boolean()
    modified = fields.DateTime()
    resource_modified = fields.DateTime()
    created = fields.DateTime()
    verified = fields.DateTime()
    visualization_types = ListWithoutNoneStrElement(fields.Str())
    source = fields.Nested(SourceSchema)
    image_url = fields.Str()
    image_alt = TranslatedStr()
    has_dynamic_data = fields.Boolean()
    has_high_value_data = fields.Boolean()
    has_high_value_data_from_ec_list = fields.Boolean()
    has_research_data = fields.Boolean()
    is_promoted = fields.Boolean()
    regions = fields.Nested(RegionSchema, many=True)
    archived_resources_files_url = fields.Str()
    current_condition_descriptions = fields.Nested(LicenseConditionDescriptionSchema)
    supplement_docs = fields.Nested(SupplementSchema, data_key="supplements", many=True)

    class Meta:
        relationships_schema = DatasetApiRelationships
        object_type = "dataset"
        url_template = "{api_url}/datasets/{ident}"
        model = "datasets.Dataset"


class DatasetApiResponse(SubscriptionMixin, TopLevel):
    class Meta:
        attrs_schema = DatasetApiAttrs
        aggs_schema = DatasetApiAggregations


class CommentApiRelationships(Relationships):
    dataset = fields.Nested(
        Relationship,
        many=False,
        _type="dataset",
        url_template="{api_url}/datasets/{ident}",
    )


class CommentAttrs(ObjectAttrs):
    comment = fields.Str(required=True, example="Looks unpretty")

    class Meta:
        object_type = "comment"
        path = "datasets"
        url_template = "{api_url}/datasets/{data.dataset.id}/comments/{ident}"
        relationships_schema = CommentApiRelationships


class CommentApiResponse(TopLevel):
    class Meta:
        attrs_schema = CommentAttrs


class DatasetCSVSchema(CSVSerializer, metaclass=CSVSchemaRegistrator):
    id = fields.Integer(data_key=_("id"), required=True)
    uuid = fields.Str(data_key=_("uuid"), default="")
    title = fields.Str(data_key=_("title"), default="")
    notes = fields.Str(data_key=_("notes"), default="")
    url = fields.Str(data_key=_("url"), default="")
    update_frequency = fields.Str(data_key=_("Update frequency"), default="")
    method_of_sharing = fields.Method("get_method_of_sharing", data_key=_("Method of sharing"))
    institution = fields.Str(data_key=_("Institution"), attribute="organization.id", default="")
    category = fields.Str(data_key=_("Category"), default="")
    status = fields.Str(data_key=_("Status"), default="")
    is_licence_set = fields.Boolean(data_key=_("Conditions for re-use"), default=None)
    created_by = fields.Int(attribute="created_by.id", data_key=_("created_by"), default=None)
    created = fields.DateTime(data_key=_("created"), default=None)
    modified_by = fields.Int(attribute="modified_by.id", data_key=_("modified_by"), default=None)
    modified = fields.DateTime(data_key=_("modified"), default=None)
    followers_count = fields.Str(data_key=_("The number of followers"), default=None)
    has_high_value_data = fields.MetaDataNullBoolean(data_key=_("Dataset has high value data"))
    has_high_value_data_from_ec_list = fields.MetaDataNullBoolean(data_key=_("Dataset has high value data from the EC list"))
    has_dynamic_data = fields.MetaDataNullBoolean(data_key=_("Dataset has dynamic data"))
    has_research_data = fields.MetaDataNullBoolean(data_key=_("Dataset has research data"))

    class Meta:
        ordered = True
        model = "datasets.Dataset"

    def get_method_of_sharing(self, obj: Dataset) -> str:
        return SOURCE_TYPE_CHOICES_FOR_ADMIN.get(obj.source_type, obj.source_type)


class DatasetXMLSerializer(ExtSchema):
    id = fields.Integer()
    url = fields.Url(attribute="frontend_absolute_url")
    title = TranslatedStr()
    notes = TranslatedStr()
    keywords = fields.Function(lambda dataset: (tag.name for tag in getattr(dataset, f"tags_{get_language()}")))
    categories = fields.Nested(DatasetCategoryAttr, many=True)
    update_frequency = TransUpdateFreqField()
    created = fields.DateTime()
    verified = fields.DateTime()
    views_count = fields.Int(attribute="computed_views_count")
    downloads_count = fields.Int(attribute="computed_downloads_count")
    published_resources_count = fields.Int(attribute="published_resources__count")
    license = fields.Str(attribute="license_name")
    conditions = fields.Str(attribute="formatted_condition_descriptions")
    organization = fields.Method("get_organization")
    resources = fields.Nested(ResourceXMLSerializer, attribute="published_resources", many=True)
    supplement_docs = fields.Nested(SupplementSchema, data_key="supplements", many=True)

    source = fields.Nested(SourceXMLSchema)
    has_high_value_data = fields.Bool()
    has_high_value_data_from_ec_list = fields.Bool()
    has_dynamic_data = fields.Bool()
    has_research_data = fields.Bool()
    regions = fields.Nested(RegionBaseSchema, many=True)

    def get_organization(self, dataset: Dataset):
        context = {
            "published_datasets_count": dataset.organization_published_datasets__count,
            "published_resources_count": dataset.organization_published_resources__count,
        }
        return InstitutionXMLSerializer(many=False, context=context).dump(dataset.organization)


class DatasetXMLWriterSerializer(DatasetXMLSerializer):
    """
    Custom serializer for XML file creation. Serializer overrides a keywords field
    to list, because we want to serialize it to json() when error in parsing
    occurs: OTD-131.
    """

    keywords = fields.Function(lambda dataset: [tag.name for tag in getattr(dataset, f"tags_{get_language()}")])


class DatasetResourcesCSVSerializer(CSVSerializer):
    """
    Serializer for Datasets to CSV as they are included in the Public-facing
    CSV catalogue
    """

    dataset_url = fields.Url(attribute="frontend_absolute_url", data_key=_("Dataset URL"))
    dataset_title = TranslatedStr(attribute="title", data_key=_("Title"))
    dataset_description = TranslatedStr(attribute="notes", data_key=_("Notes"))
    dataset_keywords = fields.Function(
        lambda obj: ", ".join((tag.name for tag in getattr(obj, f"tags_{get_language()}"))),
        data_key=_("Tag"),
    )
    dataset_categories = fields.Function(
        lambda obj: ", ".join((category.title_i18n for category in obj.categories.all())),
        data_key=_("Category"),
    )
    dataset_update_frequency = fields.Str(attribute="frequency_display", data_key=_("Update frequency"))
    dataset_created = fields.DateTime(attribute="created", data_key=_("Dataset created"), format="iso8601")
    dataset_verified = fields.DateTime(attribute="verified", data_key=_("Dataset verified"), format="iso8601")
    views_count = fields.Int(attribute="computed_views_count", data_key=_("Dataset views count"))
    downloads_count = fields.Int(attribute="computed_downloads_count", data_key=_("Dataset downloads count"))
    dataset_resources_count = fields.Int(attribute="published_resources__count", data_key=_("Number of data"))
    dataset_conditions = fields.Str(attribute="formatted_condition_descriptions", data_key=_("Terms of use"))
    dataset_license = fields.Str(attribute="license_name", data_key=_("License"))
    dataset_source = fields.Nested(SourceXMLSchema, attribute="source", data_key=_("source"))
    has_high_value_data = fields.MetaDataNullBoolean(data_key=_("Dataset has high value data"))
    has_high_value_data_from_ec_list = fields.MetaDataNullBoolean(data_key=_("Dataset has high value data from the EC list"))
    has_dynamic_data = fields.MetaDataNullBoolean(data_key=_("Dataset has dynamic data"))
    has_research_data = fields.MetaDataNullBoolean(data_key=_("Dataset has research data"))
    regions = fields.Str(data_key=_("Dataset regions"), attribute="regions_str")
    supplements = fields.Str(
        attribute="supplements_str",
        data_key=_("Dataset supplements (name, language, url, file size)"),
    )
    organization = fields.Method("get_organization")
    resources = fields.Nested(ResourceCSVMetadataSerializer, many=True, attribute="published_resources")

    @ma.post_dump(pass_many=True)
    def unpack_nested_data(self, data, many, **kwargs):
        new_result_data = []
        for record in data:
            resources = record.pop("resources")
            organization = record.pop("organization")
            record.update(**organization)
            for resource in resources:
                tmp_record = record.copy()
                tmp_record.update(**resource)
                new_result_data.append(tmp_record)
        return new_result_data

    @ma.post_dump(pass_many=False)
    def prepare_nested_data(self, data, **kwargs):
        source = data.get(_("source"))
        if source:
            source_str = (
                "{title_label}: {title}, {url_label}: {url},"
                " {last_import_label}: {last_import}, {frequency_label}: {frequency}".format(
                    title=source["title"],
                    title_label=_("name"),
                    url=source["url"],
                    url_label=_("url"),
                    last_import=source["last_import_timestamp"],
                    last_import_label=_("last import timestamp"),
                    frequency=source["update_frequency"],
                    frequency_label=_("Update frequency"),
                )
            )
            data[_("source")] = source_str
        data[_("Notes")] = strip_tags(data[_("Notes")])
        return data

    def get_organization(self, dataset):
        context = {
            "published_datasets_count": dataset.organization_published_datasets__count,
            "published_resources_count": dataset.organization_published_resources__count,
        }
        return InstitutionCSVMetadataSerializer(many=False, context=context).dump(dataset.organization)

    def get_csv_headers(self):
        result = []
        for field_name, field in self.fields.items():
            if field_name == "organization":
                org_headers = [
                    org_field.data_key for org_field_name, org_field in InstitutionCSVMetadataSerializer().fields.items()
                ]
                result.extend(org_headers)
            elif field_name == "resources":
                res_headers = [res_field.data_key for res_field_name, res_field in field.schema.fields.items()]
                result.extend(res_headers)
            else:
                header = field.data_key or field_name
                result.append(header)
        return result

    class Meta:
        ordered = True


class DescriptionSchema(ExtSchema):
    name = fields.Str()
    description = fields.Str()

    class Meta:
        ordered = True


class LicenseApiAttrs(ObjectAttrs):
    link = fields.String()
    secondLink = fields.String()
    description = fields.Nested(DescriptionSchema())
    allowed = fields.Nested(DescriptionSchema(), many=True)
    conditions = fields.Nested(DescriptionSchema(), many=True)

    class Meta:
        object_type = "license"
        ordered = True


class LicenseApiResponse(TopLevel):
    class Meta:
        attrs_schema = LicenseApiAttrs
