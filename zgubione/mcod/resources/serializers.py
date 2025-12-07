import json

import marshmallow as ma
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

import mcod.core.api.rdf.namespaces as ns
from mcod.core.api import fields, schemas
from mcod.core.api.jsonapi.serializers import (
    Aggregation,
    HighlightObjectMixin,
    Object,
    ObjectAttrs,
    ObjectAttrsMeta,
    Relationship,
    Relationships,
    TopLevel,
    TopLevelMeta,
)
from mcod.core.api.rdf.schema_mixins import ProfilesMixin
from mcod.core.api.rdf.schemas import ResponseSchema as RDFResponseSchema
from mcod.core.api.rdf.vocabs.common import VocabSKOSConcept, VocabSKOSConceptScheme
from mcod.core.api.schemas import ExtSchema
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer, ListWithoutNoneStrElement
from mcod.lib.extended_graph import ExtendedGraph
from mcod.lib.serializers import TranslatedStr
from mcod.regions.serializers import RegionBaseSchema, RegionSchema
from mcod.resources.models import Resource
from mcod.watchers.serializers import SubscriptionMixin


class LanguageAggregation(ExtSchema):
    id = fields.String(attribute="key")
    title = fields.String()
    doc_count = fields.Integer()

    @ma.pre_dump
    def prepare_data(self, data, **kwargs):
        request = self.context.get("request")
        title = Resource.LANGUAGE_NAMES.get(data.key)
        data["title"] = title.capitalize() if request.language == "en" else title
        return data


class ResourceApiRelationships(Relationships):
    dataset = fields.Nested(
        Relationship,
        many=False,
        _type="dataset",
        path="datasets",
        url_template="{api_url}/datasets/{ident}",
    )
    institution = fields.Nested(
        Relationship,
        many=False,
        _type="institution",
        attribute="institution",
        url_template="{api_url}/institutions/{ident}",
    )

    subscription = fields.Nested(
        Relationship,
        many=False,
        _type="subscription",
        url_template="{api_url}/auth/subscriptions/{ident}",
    )

    tabular_data = fields.Nested(
        Relationship,
        many=False,
        _type="tabular_data",
        url_template="{api_url}/resources/{ident}/data",
    )

    geo_data = fields.Nested(
        Relationship,
        many=False,
        _type="geo_data",
        url_template="{api_url}/resources/{ident}/geo",
    )

    chart = fields.Nested(
        Relationship,
        many=False,
        _type="chart",
        attribute="chartable",
        url_template="{api_url}/resources/{ident}/chart",
    )
    related_resource = fields.Nested(
        Relationship,
        many=False,
        _type="resource",
        url_template="{api_url}/resources/{ident}",
        attribute="related_resource_published",
    )


class SpecialSignSchema(ExtSchema):
    symbol = fields.Str()
    name = TranslatedStr()
    description = TranslatedStr()


class SupplementSchema(ExtSchema):
    name = TranslatedStr()
    file_url = fields.Url(attribute="api_file_url")
    file_size = fields.Str(attribute="file_size_human_readable_or_empty_str")
    language = fields.Str()

    class Meta:
        ordered = True


class ResourceFileSchema(ExtSchema):
    file_size = fields.Integer()
    download_url = fields.Str()
    format = fields.Str()
    compressed_file_format = fields.Str()
    openness_score = fields.Integer()


class ResourceApiAttrs(ObjectAttrs, HighlightObjectMixin):
    title = TranslatedStr()
    description = TranslatedStr()
    category = fields.Str()
    format = fields.Str()
    media_type = fields.Str(attribute="type")  # https://jsonapi.org/format/#document-resource-object-fields
    visualization_types = ListWithoutNoneStrElement(fields.Str())
    openness_score = fields.Integer()
    views_count = fields.Int(attribute="computed_views_count")
    downloads_count = fields.Int(attribute="computed_downloads_count")
    modified = fields.DateTime()
    created = fields.DateTime()
    verified = fields.DateTime()
    data_date = fields.Date()
    file_url = fields.Str()
    file_size = fields.Integer()
    csv_file_url = fields.Str()
    csv_file_size = fields.Integer()
    jsonld_file_url = fields.Str()
    jsonld_file_size = fields.Integer()
    jsonld_download_url = fields.Str()
    download_url = fields.Str()
    csv_download_url = fields.Str()
    link = fields.Str()
    data_special_signs = fields.Nested(SpecialSignSchema, data_key="special_signs", many=True)
    is_chart_creation_blocked = fields.Bool()
    has_dynamic_data = fields.Boolean()
    has_high_value_data = fields.Boolean()
    has_high_value_data_from_ec_list = fields.Boolean()
    has_research_data = fields.Boolean()
    contains_protected_data = fields.Boolean()
    regions = fields.Method("get_regions")
    files = fields.Method("get_files")
    supplement_docs = fields.Nested(SupplementSchema, data_key="supplements", many=True)
    language = fields.Str()

    class Meta:
        relationships_schema = ResourceApiRelationships
        object_type = "resource"
        api_path = "resources"
        url_template = "{api_url}/resources/{ident}"
        model = "resources.Resource"

    def get_regions(self, res):
        return RegionSchema(many=True).dump(getattr(res, "all_regions", res.regions))

    def get_files(self, res):
        return ResourceFileSchema(many=True).dump(getattr(res, "all_files", res.files))


class ResourceApiAggregations(ExtSchema):
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
    by_verified = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_verified.by_verified.buckets",
    )
    by_format = fields.Nested(Aggregation, many=True, attribute="_filter_by_format.by_format.buckets")
    by_type = fields.Nested(Aggregation, many=True, attribute="_filter_by_type.by_type.buckets")
    by_openness_score = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_openness_score.by_openness_score.buckets",
    )
    by_visualization_type = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_visualization_type.by_visualization_type.buckets",
    )
    by_language = fields.Nested(
        LanguageAggregation,
        many=True,
        attribute="_filter_by_language.by_language.buckets",
    )


class ResourceApiResponse(SubscriptionMixin, TopLevel):
    class Meta:
        attrs_schema = ResourceApiAttrs
        aggs_schema = ResourceApiAggregations


class SpecialSignRDFNestedSchema(ProfilesMixin, ma.Schema):
    id = ma.fields.Int()
    title_pl = ma.fields.Str(attribute="name_pl")
    title_en = ma.fields.Str(attribute="name_en")


def special_signs_dump(resource, context):
    return SpecialSignRDFNestedSchema(many=True, context=context).dump(resource.special_signs.all())


class SupplementRDFNestedSchema(ma.Schema):
    file_url = ma.fields.Str()


def supplements_dump(object, context):
    return SupplementRDFNestedSchema(many=True, context=context).dump(object.supplement_docs)


class ResourceRDFMixin(ProfilesMixin):
    dataset_frontend_absolute_url = ma.fields.Function(lambda r: r.dataset.frontend_absolute_url)
    id = ma.fields.Str(attribute="id")
    dataset_id = ma.fields.Str(attribute="dataset_id")
    title_pl = ma.fields.Str(attribute="title_translated.pl")
    title_en = ma.fields.Str(attribute="title_translated.en")
    description_pl = ma.fields.Str(attribute="description_translated.pl")
    description_en = ma.fields.Str(attribute="description_translated.en")
    status = ma.fields.Str()
    created = ma.fields.DateTime()
    modified = ma.fields.DateTime()
    access_url = ma.fields.Str(attribute="frontend_absolute_url")
    download_url = ma.fields.Str()
    format = ma.fields.Str()
    file_mimetype = ma.fields.Str(attribute="main_file_mimetype")
    file_size = ma.fields.Int()
    license = ma.fields.Function(lambda r: r.dataset.license_link)
    validity_date = ma.fields.Str(attribute="data_date")
    openness_score = ma.fields.Int()
    special_signs = ma.fields.Function(special_signs_dump)
    supplements = ma.fields.Function(supplements_dump)


class BaseVocabEntryRDFResponseSchema(RDFResponseSchema):
    url = ma.fields.Str()
    name_pl = ma.fields.Str()
    name_en = ma.fields.Str()
    description_pl = ma.fields.Str()
    description_en = ma.fields.Str()
    notation = ma.fields.Str()
    scheme = ma.fields.Method("get_scheme")
    top_concept_of = ma.fields.Method("get_scheme")

    def get_scheme(self, entry):
        return entry.vocab_url


class VocabSchemaMixin:
    @ma.pre_dump()
    def prepare_data(self, data, **kwargs):
        return data.data if hasattr(data, "data") else data

    @ma.post_dump()
    def prepare_graph_triples(self, data, **kwargs):
        return self.rdf_class().to_triples(data, self.include_nested_triples)

    @ma.post_dump(pass_many=True)
    def prepare_graph(self, data, many, **kwargs):
        graph = ExtendedGraph(ordered=True)

        # add bindings
        for prefix, namespace in ns.NAMESPACES.items():
            graph.bind(prefix, namespace)

        for triple in data:
            graph.add(triple)
        return graph


class VocabEntryRDFResponseSchema(BaseVocabEntryRDFResponseSchema, VocabSchemaMixin):
    rdf_class = VocabSKOSConcept


class NestedVocabEntryRDFResponseSchema(BaseVocabEntryRDFResponseSchema):
    pass


def entries_dump(vocab, context):
    return NestedVocabEntryRDFResponseSchema(many=True, context=context).dump(vocab.entries.values())


class VocabRDFResponseSchema(RDFResponseSchema, VocabSchemaMixin):
    rdf_class = VocabSKOSConceptScheme

    url = ma.fields.Str()
    identifier = ma.fields.Method("get_identifier")
    label_pl = ma.fields.Str()
    label_en = ma.fields.Str()
    title_pl = ma.fields.Method("get_label_pl")
    title_en = ma.fields.Method("get_label_en")
    name_pl = ma.fields.Method("get_label_pl")
    name_en = ma.fields.Method("get_label_en")
    version = ma.fields.Str()
    concepts = ma.fields.Function(entries_dump)

    def get_identifier(self, vocab):
        return vocab.url

    def get_label_pl(self, vocab):
        return vocab.label_pl

    def get_label_en(self, vocab):
        return vocab.label_en


class ResourceRDFResponseSchema(ResourceRDFMixin, RDFResponseSchema):
    @ma.pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        # If many, serialize data as catalog - from Elasticsearch
        return data.data if hasattr(data, "data") else data

    @ma.post_dump(pass_many=False)
    def prepare_graph_triples(self, data, **kwargs):
        distribution = self.get_rdf_class_for_model(model=Resource)()
        return distribution.to_triples(data, self.include_nested_triples)

    @ma.post_dump(pass_many=True)
    def prepare_graph(self, data, many, **kwargs):
        graph = ExtendedGraph(ordered=True)
        self.add_bindings(graph=graph)

        for triple in data:
            graph.add(triple)
        return graph

    class Meta:
        ordered = True
        model = "resources.Resource"


class TableApiRelationships(Relationships):
    resource = fields.Nested(
        Relationship,
        many=False,
        _type="resource",
        url_template="{api_url}/resources/{ident}",
    )


class TableApiAttrsMeta(ObjectAttrsMeta):
    updated_at = fields.DateTime()
    row_no = fields.Integer()


class TableApiAttrs(ObjectAttrs):
    class Meta:
        object_type = "row"
        url_template = "{api_url}/resources/{data.resource.id}/data/{ident}"
        relationships_schema = TableApiRelationships
        meta_schema = TableApiAttrsMeta


class MetricAggregation(ExtSchema):
    column = fields.String()
    value = fields.Number()


class TableAggregations(ExtSchema):
    sum = fields.Nested(MetricAggregation, many=True)
    avg = fields.Nested(MetricAggregation, many=True)


class TableApiMeta(TopLevelMeta):
    data_schema = fields.Raw()
    headers_map = fields.Raw()
    aggregations = fields.Nested(TableAggregations)


class TableApiResponse(TopLevel):
    class Meta:
        attrs_schema = TableApiAttrs
        meta_schema = TableApiMeta


class GeoApiRelationships(Relationships):
    resource = fields.Nested(
        Relationship,
        many=False,
        _type="resource",
        url_template="{api_url}/resources/{ident}",
    )


class GeoApiAttrsMeta(ObjectAttrsMeta):
    updated_at = fields.DateTime()
    row_no = fields.Integer()


class Geometry(ma.Schema):
    type = fields.String(required=True)
    coordinates = fields.Raw(required=True)


class GeoFeatureRecord(ma.Schema):
    pass


class GeoShapeObject(schemas.ExtSchema):
    shape = fields.Nested(Geometry)
    record = fields.Nested(GeoFeatureRecord, many=False)
    label = fields.String()


class GeoApiAttrs(ObjectAttrs, GeoShapeObject):
    class Meta:
        object_type = "geoshape"
        url_template = "{api_url}/resources/{data.resource.id}/geo/{ident}"
        relationships_schema = GeoApiRelationships
        meta_schema = GeoApiAttrsMeta


class BaseGeoAggregation(schemas.ExtSchema):
    doc_count = fields.Integer()
    centroid = fields.List(fields.Float)
    resources_count = fields.Integer()
    datasets_count = fields.Integer()


class GeoTileAggregation(BaseGeoAggregation):
    tile_name = fields.String()


class GeoRegionAggregation(BaseGeoAggregation):
    region_name = TranslatedStr()


class GeoTileShapesAggregation(GeoTileAggregation):
    shapes = fields.Nested(GeoShapeObject, many=True)


class GeoBounds(schemas.ExtSchema):
    top_left = fields.List(fields.Float)
    bottom_right = fields.List(fields.Float)


class GeoAggregations(ma.Schema):
    tiles = fields.Nested(GeoTileShapesAggregation, many=True)
    bounds = fields.Nested(GeoBounds)


class GeoApiMeta(TopLevelMeta):
    data_schema = fields.Raw()
    headers_map = fields.Raw()
    aggregations = fields.Nested(GeoAggregations)


class GeoApiResponse(TopLevel):
    @ma.pre_dump
    def prepare_top_level(self, c, **kwargs):
        try:
            super().prepare_top_level(c, **kwargs)
        except ZeroDivisionError:
            pass
        return c

    class Meta:
        attrs_schema = GeoApiAttrs
        meta_schema = GeoApiMeta


class CommentApiRelationships(Relationships):
    resource = fields.Nested(
        Relationship,
        many=False,
        _type="resource",
        url_template="{api_url}/resources/{ident}",
    )


class CommentAttrs(ObjectAttrs):
    comment = fields.Str(required=True, example="Looks unpretty")

    class Meta:
        object_type = "comment"
        url_template = "{api_url}/resources/{data.resource.id}/comments/{ident}"
        relationships_schema = CommentApiRelationships


class CommentApiResponse(TopLevel):
    class Meta:
        attrs_schema = CommentAttrs
        max_items_num = 20000


class ResourceCSVSchema(CSVSerializer, metaclass=CSVSchemaRegistrator):
    id = fields.Integer(data_key=_("id"), required=True)
    uuid = fields.Str(data_key=_("uuid"), default="")
    title = fields.Str(data_key=_("title"), default="")
    description = fields.Str(data_key=_("description"), default="")
    link = fields.Str(data_key=_("link"), default="")
    link_is_valid = fields.Str(data_key=_("link_tasks_last_status"), default="")
    file_is_valid = fields.Str(data_key=_("file_tasks_last_status"), default="")
    data_is_valid = fields.Str(data_key=_("data_tasks_last_status"), default="")
    format = fields.Str(data_key=_("format"), default="")
    converted_formats_str = fields.Str(data_key=_("formats after conversion"))
    institution_id = fields.Str(attribute="institution.id", data_key=_("Id Institution"), default="")
    dataset = fields.Str(attribute="dataset.title", data_key=_("dataset"), default="")
    dataset_id = fields.Str(attribute="dataset.id", data_key=_("Id dataset"), default="")
    status = fields.Str(data_key=_("status"), default="")
    created_by = fields.Int(attribute="created_by.id", data_key=_("created_by"), default=None)
    created = fields.DateTime(data_key=_("created"), default=None)
    modified_by = fields.Int(attribute="modified_by.id", data_key=_("modified_by"), default=None)
    modified = fields.DateTime(data_key=_("modified"), default=None)
    resource_type = fields.Str(attribute="type", data_key=_("type"), default="")
    openness_score = fields.Int(data_key=_("Openness score"), default=None)
    method_of_sharing = fields.Str(data_key=_("Method of sharing"))
    views_count = fields.Int(attribute="computed_views_count", data_key=_("views_count"), default=None)
    downloads_count = fields.Int(
        attribute="computed_downloads_count",
        data_key=_("downloads_count"),
        default=None,
    )
    has_high_value_data = fields.MetaDataNullBoolean(data_key=_("Resource has high value data"))
    has_high_value_data_from_ec_list = fields.MetaDataNullBoolean(data_key=_("Resource has high value data from the EC list"))
    has_dynamic_data = fields.MetaDataNullBoolean(data_key=_("Resource has dynamic data"))
    has_research_data = fields.MetaDataNullBoolean(data_key=_("Resource has research data"))
    contains_protected_data = fields.MetaDataNullBoolean(data_key=_("Contains protected data list"))

    class Meta:
        ordered = True
        model = "resources.Resource"


class ChartApiRelationships(Relationships):
    resource = fields.Nested(
        Relationship,
        many=False,
        _type="resource",
        url_template="{api_url}/resources/{ident}",
    )


class ChartApiAttrs(ObjectAttrs):
    chart = fields.Raw()
    is_default = fields.Boolean()
    name = fields.Str()

    def get_chart(self, obj):
        return json.dumps(obj.chart)

    class Meta:
        relationships_schema = ChartApiRelationships
        object_type = "chart"
        api_path = "chart"
        model = "resources.Chart"
        url_template = "{api_url}/resources/{data.resource.ident}/charts/{ident}"


class ChartApiData(Object):

    @ma.pre_dump(pass_many=False)
    def prepare_data(self, data, **kwargs):
        if not data:
            return
        return super().prepare_data(data, **kwargs)


class ChartApiMeta(TopLevelMeta):
    named_charts = fields.Bool()


class ChartApiResponse(TopLevel):
    class Meta:
        data_schema = ChartApiData
        attrs_schema = ChartApiAttrs
        meta_schema = ChartApiMeta

    @ma.pre_dump
    def prepare_top_level(self, c, **kwargs):
        if self.context["is_listing"]:
            c.data = c.data if hasattr(c, "data") else []
            c.meta.setdefault("named_charts", self.context.get("named_charts", False))
        return super().prepare_top_level(c, **kwargs)


class SourceCSVSchema(ExtSchema):
    title = fields.Str()
    url = fields.URL()
    update_frequency = TranslatedStr()
    last_import_timestamp = fields.DateTime()


class ResourceXMLSerializer(schemas.ExtSchema):
    id = fields.Integer()
    access_url = fields.Url(attribute="frontend_absolute_url")
    title = TranslatedStr()
    description = TranslatedStr()
    openness_score = fields.Integer()
    format = fields.Str()
    views_count = fields.Int(attribute="computed_views_count")
    downloads_count = fields.Int(attribute="computed_downloads_count")
    created = fields.DateTime(format="iso8601")
    data_date = fields.Date()
    type = fields.Function(lambda resource: resource.get_type_display())
    file_size = fields.Str(attribute="file_size_human_readable_or_empty_str")

    visualization_types = ListWithoutNoneStrElement(fields.Str())
    download_url = fields.Str()
    data_special_signs = fields.Nested(SpecialSignSchema, data_key="special_signs", many=True)
    has_high_value_data = fields.Bool()
    has_high_value_data_from_ec_list = fields.Bool()
    has_dynamic_data = fields.Bool()
    has_research_data = fields.Bool()
    contains_protected_data = fields.Bool()
    all_regions = fields.Nested(RegionBaseSchema, data_key="regions", many=True)
    supplement_docs = fields.Nested(SupplementSchema, data_key="supplements", many=True)


class ResourceCSVMetadataSerializer(schemas.ExtSchema):
    """
    Serializer for Resources to CSV as they are included in the Public-facing
    CSV catalogue
    """

    frontend_absolute_url = fields.Url(data_key=_("Resource URL"))
    title = TranslatedStr(data_key=_("Resource title"), default="")
    description = TranslatedStr(data_key=_("Resource description"))
    created = fields.DateTime(data_key=_("Resource created"), format="iso8601")
    data_date = fields.Date(data_key=_("Data date"))
    openness_score = fields.Int(data_key=_("Openness score"))
    resource_type = fields.Function(lambda obj: obj.get_type_display(), data_key=_("Type"))
    format = fields.Str(data_key=_("File format"), default="")
    file_size = fields.Str(attribute="file_size_human_readable_or_empty_str", data_key=_("File size"))
    views_count = fields.Int(attribute="computed_views_count", data_key=_("Resource views count"))
    downloads_count = fields.Int(attribute="computed_downloads_count", data_key=_("Resource downloads count"))
    has_table = fields.Function(lambda obj: _("YES") if obj.has_table else _("NO"), data_key=_("Table"))
    has_chart = fields.Function(lambda obj: _("YES") if obj.has_chart else _("NO"), data_key=_("Map"))
    has_map = fields.Function(lambda obj: _("YES") if obj.has_map else _("NO"), data_key=_("Chart"))
    has_high_value_data = fields.MetaDataNullBoolean(data_key=_("Resource has high value data"))
    has_high_value_data_from_ec_list = fields.MetaDataNullBoolean(data_key=_("Resource has high value data from the EC list"))
    has_dynamic_data = fields.MetaDataNullBoolean(data_key=_("Resource has dynamic data"))
    has_research_data = fields.MetaDataNullBoolean(data_key=_("Resource has research data"))
    contains_protected_data = fields.MetaDataNullBoolean(data_key=_("Contains protected data list"))
    regions = fields.Str(data_key=_("Resource regions"), attribute="all_regions_str")
    download_url = fields.Url(data_key=_("Download URL"))
    data_special_signs = fields.Nested(SpecialSignSchema, data_key=_("special signs"), many=True)
    supplements = fields.Str(
        attribute="supplements_str",
        data_key=_("Resource supplements (name, language, url, file size)"),
    )

    @ma.post_dump(pass_many=False)
    def prepare_nested_data(self, data, **kwargs):
        special_signs = data.get(_("special signs"))
        signs_str = "\n".join(
            [
                '{name_label}: {name}, {symbol_label}: "{symbol}", {desc_label}: {desc}'.format(
                    name=sign["name"],
                    name_label=_("name"),
                    symbol=sign["symbol"],
                    symbol_label=_("symbol"),
                    desc=sign["description"],
                    desc_label=_("description"),
                )
                for sign in special_signs
            ]
        )
        data[_("special signs")] = signs_str
        values_with_html = [_("Resource title"), _("Resource description")]
        for attribute in values_with_html:
            data[attribute] = strip_tags(data[attribute])
        return data

    class Meta:
        ordered = True


class AggregatedDGAInfoApiResponse(ExtSchema):
    dataset_id = fields.Int(attribute="resource.dataset.id", data_key="dataset_id")
    dataset_slug = fields.Str(attribute="resource.dataset.slug", data_key="dataset_slug")
    resource_id = fields.Int(attribute="resource.id", data_key="resource_id")
    resource_slug = fields.Str(attribute="resource.slug", data_key="resource_slug")
