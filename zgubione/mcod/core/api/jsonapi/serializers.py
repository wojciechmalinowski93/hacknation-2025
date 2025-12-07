from collections.abc import Sequence
from typing import Any, Optional, Union

from django.apps import apps
from django.core import paginator
from django.db.models import Manager, Q, QuerySet
from django.utils.timezone import now
from django.utils.translation import get_language
from elasticsearch_dsl import AttrDict, AttrList, response as es_response, utils as es_utils
from marshmallow import pre_dump
from marshmallow.schema import SchemaOpts
from modeltrans.manager import MultilingualQuerySet
from querystring_parser import builder

from mcod import settings
from mcod.core.api import fields, schemas
from mcod.core.registries import object_attrs_registry
from mcod.core.utils import complete_invalid_xml, setpathattr
from mcod.unleash import is_enabled


class ErrorSource(schemas.ExtSchema):
    pointer = fields.String()
    parameter = fields.String()


class ErrorMeta(schemas.ExtSchema):
    traceback = fields.String()


class ErrorSchema(schemas.ExtSchema):
    id = fields.String()
    status = fields.String()
    code = fields.String()
    title = fields.String()
    detail = fields.String()
    meta = fields.Nested(ErrorMeta, many=False)
    source = fields.Nested(ErrorSource)

    class Meta:
        strict = True
        ordered = True


class ErrorsSchema(schemas.ExtSchema):
    jsonapi = fields.Raw(default={"version": "1.0"})
    errors = fields.Nested(ErrorSchema, many=True)

    class Meta:
        strict = True
        ordered = True


class RelationshipData(schemas.ExtSchema):
    id = fields.String(required=True)
    _type = fields.String(required=True, data_key="type")


class RelationshipLinks(schemas.ExtSchema):
    related = fields.String(required=True)


class RelationshipMeta(schemas.ExtSchema):
    count = fields.Integer()


class Relationship(schemas.ExtSchema):
    data = fields.Nested(RelationshipData)
    links = fields.Nested(RelationshipLinks, required=True, many=False)
    meta = fields.Nested(RelationshipMeta, many=False)

    @pre_dump
    def prepare_data(self, data, **kwargs):
        object_url = self.context.get("object_url", None) or self.api_url
        url_template = self.context.get("url_template") or None
        res = {}
        if isinstance(data, (Sequence, AttrList)):
            if url_template:
                related_url = url_template.format(api_url=self.api_url, object_url=object_url)
                res["links"] = {"related": related_url}
            res["meta"] = {"count": len(data)}
        elif isinstance(data, QuerySet):
            if url_template:
                related_url = url_template.format(api_url=self.api_url, object_url=object_url)
                res["links"] = {"related": related_url}
            res["meta"] = {"count": data.count()}
        else:
            id = getattr(data, "id", None) or getattr(data.meta, "id")
            slug = getattr(data, "slug", None)
            if isinstance(slug, AttrDict):
                lang = get_language()
                slug = slug[lang]
            ident = "{},{}".format(id, slug) if slug else id

            if url_template:
                related_url = url_template.format(api_url=self.api_url, object_url=object_url, ident=ident)
                res["links"] = {"related": related_url}
            res["data"] = {"id": id, "_type": self.context["_type"]}

        return res


class DataRelationship(Relationship):
    data = fields.Nested(RelationshipData, many=True)

    @pre_dump
    def prepare_data(self, data, **kwargs):
        res = super().prepare_data(data, **kwargs)
        show_data = self.context.get("show_data", False)
        if show_data:
            _type = self.context["_type"]
            for item in data:
                if isinstance(item, dict):
                    item.update({"_type": _type})
                else:
                    setattr(item, "_type", _type)
            res["data"] = data
        return res


class Relationships(schemas.ExtSchema):
    def __init__(
        self,
        only=None,
        exclude=(),
        many=False,
        context=None,
        load_only=(),
        dump_only=(),
        partial=False,
        unknown=None,
    ):
        super().__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

        for field_name, field in self.fields.items():
            field.schema.context = dict(self.context)
            field.schema.context.update(field.metadata)
            field.many = False

    def prepare_object_url(self, data):
        object_url = data.pop("object_url", None)
        if object_url:
            for _name, field in self._fields.items():
                url_template = field.metadata.get("url_template")
                if url_template and "object_url" in url_template:
                    field.schema.context.update(object_url=object_url)

    def filter_data(self, data, **kwargs):
        return data

    @pre_dump
    def prepare_data(self, data, **kwargs):
        self.prepare_object_url(data)
        return self.filter_data(data, **kwargs)


class ObjectAttrsMeta(schemas.ExtSchema):
    pass


class ObjectAttrsOpts(SchemaOpts):
    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.relationships_schema = getattr(meta, "relationships_schema", None)

        if self.relationships_schema and not issubclass(self.relationships_schema, Relationships):
            raise Exception("{} must be a subclass of Relationships".format(self.relationships_schema))

        self.meta_schema = getattr(meta, "meta_schema", None)

        if self.meta_schema and not issubclass(self.meta_schema, ObjectAttrsMeta):
            raise Exception("{} must be a subclass of ObjectAttrsMeta".format(self.meta_schema))

        self.object_type = getattr(meta, "object_type", None) or "undefined"
        self.model_name = getattr(meta, "model", None) or None
        self.url_template = getattr(meta, "url_template", None) or "{api_url}"


class ObjectAttrs(schemas.ExtSchema):
    OPTIONS_CLASS = ObjectAttrsOpts

    @classmethod
    def prepare(cls):
        object_attrs_registry.register(cls)


class ObjectLinks(schemas.ExtSchema):
    self = fields.String(required=True)


class ObjectOpts(SchemaOpts):
    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.attrs_schema = getattr(meta, "attrs_schema", None)
        if self.attrs_schema and not issubclass(self.attrs_schema, ObjectAttrs):
            raise Exception("{} must be a subclass of ObjectAttrs".format(self.attrs_schema))


class Object(schemas.ExtSchema):
    OPTIONS_CLASS = ObjectOpts
    id = fields.Str(required=True)
    links = fields.Nested(ObjectLinks, name="links")
    _type = fields.String(required=True, data_key="type")

    def __init__(
        self,
        only=None,
        exclude=(),
        many=False,
        context=None,
        load_only=(),
        dump_only=(),
        partial=False,
        unknown=None,
    ):

        self._declared_fields["attributes"] = fields.Nested(self.opts.attrs_schema, name="attributes", many=False)

        relationships_schema = getattr(self.opts.attrs_schema.opts, "relationships_schema", None)

        if relationships_schema:
            self._declared_fields["relationships"] = fields.Nested(relationships_schema, many=False, name="relationships")

        meta_schema = getattr(self.opts.attrs_schema.opts, "meta_schema", None)

        if meta_schema:
            self._declared_fields["meta"] = fields.Nested(meta_schema, many=False, name="meta")

        super().__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

    def _get_data_id_or_none(self, data: Any) -> Optional[int]:
        return getattr(data, "id", None) or getattr(data.meta, "id")

    def _get_slug_or_none(self, data: Any) -> Optional[str]:
        slug = getattr(data, "slug", None)
        if isinstance(slug, AttrDict):
            lang = get_language()
            slug = slug[lang]
        return slug

    def _get_object_url(self, data: Any) -> str:
        if hasattr(self.opts.attrs_schema, "self_api_url"):
            return self.opts.attrs_schema.self_api_url(data)
        else:
            data_id = self._get_data_id_or_none(data)
            slug = self._get_slug_or_none(data)
            ident = "{},{}".format(data_id, slug) if slug else str(data_id)
            return self.opts.attrs_schema.opts.url_template.format(api_url=self.api_url, ident=ident, data=data)

    def _get_relationships(self, data: Any) -> dict:
        relationships = {}
        object_url = self._get_object_url(data)
        if "relationships" in self.fields:
            for name, field in self.fields["relationships"].schema.fields.items():
                _name = field.attribute or name
                field.schema.context.update(object_url=object_url)
                value = getattr(data, _name, None)
                if is_enabled("S65_fix_long_api_response.be"):
                    if isinstance(value, Manager) or isinstance(value, MultilingualQuerySet):
                        value = value.values()
                else:
                    if isinstance(value, Manager):
                        value = value.values()
                if value or field.required:
                    relationships[_name] = value
                    relationships["object_url"] = object_url
        return relationships

    @pre_dump(pass_many=False)
    def prepare_data(self, data: Any, **kwargs) -> dict:
        data_id = self._get_data_id_or_none(data)
        res = dict(attributes=data, id=str(data_id), _type=self.opts.attrs_schema.opts.object_type)

        object_url = self._get_object_url(data)
        if object_url:
            res["links"] = {"self": object_url}

        if "meta" in self._declared_fields:
            res["meta"] = data

        relationships = self._get_relationships(data)
        if relationships:
            res["relationships"] = relationships
        return res


class TopLevelMeta(schemas.ExtSchema):
    language = fields.String()
    params = fields.Raw()
    path = fields.String()
    count = fields.Integer()
    relative_uri = fields.String()
    aggregations = fields.Raw()
    subscription_url = fields.String()
    server_time = fields.DateTime(default=now)
    notifications = fields.Raw()

    @pre_dump
    def do_something(self, data, **kwargs):
        request = self.context["request"]
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            data["notifications"] = user.get_unread_notifications()
        return data


class TopLevelLinks(schemas.ExtSchema):
    self = fields.String()
    first = fields.String()
    last = fields.String()
    prev = fields.String()
    next = fields.String()


class TopLevelOpts(SchemaOpts):
    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.attrs_schema = getattr(meta, "attrs_schema", None)
        self.aggs_schema = getattr(meta, "aggs_schema", None)
        self.data_schema = getattr(meta, "data_schema", None)

        self.meta_schema = getattr(meta, "meta_schema", TopLevelMeta)
        self.links_schema = getattr(meta, "links_schema", TopLevelLinks)

        self.max_items_num = getattr(meta, "max_items_num", 10000)

        if self.attrs_schema and not issubclass(self.attrs_schema, ObjectAttrs):
            raise Exception("{} must be a subclass of ObjectAttrs".format(self.attrs_schema))
        if self.data_schema and not issubclass(self.data_schema, schemas.ExtSchema):
            raise Exception("{} must be a subclass of {}".format(self.data_schema, schemas.ExtSchema.__name__))
        if self.meta_schema and not issubclass(self.meta_schema, TopLevelMeta):
            raise Exception("{} must be a subclass of Meta".format(self.meta_schema))
        if self.aggs_schema:
            if not issubclass(self.aggs_schema, schemas.ExtSchema):
                raise Exception("{} must be a subclass of ExtSchema".format(self.aggs_schema))
            self.meta_schema.aggregations = fields.Nested(self.aggs_schema, many=False)
        if self.links_schema and not issubclass(self.links_schema, TopLevelLinks):
            raise Exception("{} must be a subclass of Links".format(self.links_schema))


class Aggregation(schemas.ExtSchema):
    id = fields.String(attribute="key")
    title = fields.String(attribute="key_as_string")
    doc_count = fields.Integer()

    @pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        if many:
            for item in data:
                item["title"] = str(item.key).upper()
            return data


class ExtAggregation(schemas.ExtSchema):
    id = fields.String()
    title = fields.String()
    doc_count = fields.Integer()

    @pre_dump(pass_many=True)
    def prepare_data(self, data, **kwargs):
        _meta_cls = getattr(self, "Meta")
        if _meta_cls:
            model_str = getattr(_meta_cls, "model")
            field_name = getattr(_meta_cls, "title_field", "name")
            additional_attributes = getattr(_meta_cls, "additional_attributes", [])
            if model_str:
                filter_field = getattr(_meta_cls, "filter_field", "pk")
                id_field = getattr(_meta_cls, "id_field", "id")
                model = apps.get_model(model_str)
                _data = {item["key"]: item["doc_count"] for item in data}
                data = []
                q = Q(**{f"{filter_field}__in": _data.keys()})
                for item in model.objects.filter(q).values(id_field, field_name, *additional_attributes):
                    item_data = self._get_item_data(item, _data, id_field, field_name, additional_attributes)
                    data.append(item_data)

        return data

    def _get_item_data(self, item, data, id_field, field_name, additional_attributes):
        item_data = {
            id_field: item[id_field],
            "title": item[field_name],
            "doc_count": data[item[id_field]],
        }
        for attr in additional_attributes:
            item_data[attr] = item[attr]
        return item_data


class TopLevel(schemas.ExtSchema):
    included = fields.Raw()
    jsonapi = fields.Raw(default={"version": "1.0"})
    errors = fields.Raw()

    OPTIONS_CLASS = TopLevelOpts

    def __init__(
        self,
        only=None,
        exclude=(),
        many=False,
        context=None,
        load_only=(),
        dump_only=(),
        partial=False,
        unknown=None,
    ):
        data_cls = self.opts.data_schema or type("{}Data".format(self.__class__.__name__), (Object,), {})
        if self.opts.attrs_schema:
            setattr(data_cls.opts, "attrs_schema", self.opts.attrs_schema)

        self._declared_fields["data"] = fields.Nested(data_cls, name="data", many=many, allow_none=True)

        if self.opts.meta_schema:
            if self.opts.aggs_schema:
                self.opts.meta_schema._declared_fields["aggregations"] = fields.Nested(self.opts.aggs_schema, many=False)
            self._declared_fields["meta"] = fields.Nested(self.opts.meta_schema, name="meta", many=False)

        if self.opts.links_schema:
            self._declared_fields["links"] = fields.Nested(self.opts.links_schema, name="links", many=False)
        context = context or {}
        context["is_listing"] = many

        super().__init__(
            only=only,
            exclude=exclude,
            many=False,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

    @pre_dump
    def prepare_top_level(self, c, **kwargs):

        def _get_page_link(page_number):
            cleaned_data["page"] = page_number
            return "{}{}?{}".format(settings.API_URL, request.path, builder.build(cleaned_data))

        c.data = c.data if hasattr(c, "data") else None
        if not c.data and self.context["is_listing"]:
            if isinstance(c.data, es_response.Response):
                c.data.hits = []
            else:
                c.data = []
        request = self.context["request"]
        c.meta = getattr(c, "meta", {})
        c.links = getattr(c, "links", {})
        cleaned_data = dict(getattr(request.context, "cleaned_data", {}))

        c.meta.update(
            {
                "language": request.language,
                "params": request.params,
                "path": request.path,
                "relative_uri": request.relative_uri,
            }
        )

        c.links["self"] = request.uri.replace(request.forwarded_prefix, settings.API_URL)

        if self.context["is_listing"]:
            data = getattr(c, "data", {})
            c.meta["aggregations"] = self.get_aggregations(data)
            items_count = self._get_items_count(data)
            c.meta["count"] = items_count
            page, per_page = cleaned_data.get("page", 1), cleaned_data.get("per_page", 20)
            c.links["self"] = _get_page_link(page)
            if page > 1:
                c.links["first"] = _get_page_link(1)
                c.links["prev"] = _get_page_link(page - 1)
            if items_count:
                max_count = min(items_count, self.opts.max_items_num)
                off = 1 if max_count % per_page else 0
                last_page = max_count // per_page + off
                if last_page > 1:
                    c.links["last"] = _get_page_link(last_page)
                if page * per_page < max_count:
                    c.links["next"] = _get_page_link(page + 1)
        return c

    @staticmethod
    def _get_items_count(data: Union[paginator.Page, list, es_response.Response]) -> int:
        if isinstance(data, paginator.Page):
            return data.paginator.count
        elif isinstance(data, list):
            return len(data)
        hits: "es_utils.AttrList" = getattr(data, "hits", None)
        if isinstance(hits.total, dict):
            return hits.total.get("value", 0)
        elif isinstance(hits.total, int):
            return hits.total
        return 0

    def get_aggregations(self, data):
        return getattr(data, "aggregations", {}) or {}


class SubscriptionQueryAttrs(ObjectAttrs):
    title = fields.String()

    class Meta:
        object_type = "query"


class SubscriptionQueryLinks(RelationshipLinks):
    related = fields.String(required=True, data_key="self")


class SubscriptionQuerySchema(Object):
    links = fields.Nested(SubscriptionQueryLinks, required=True, many=False)

    class Meta:
        attrs_schema = SubscriptionQueryAttrs

    @pre_dump
    def prepare_data(self, data, **kwargs):
        return {
            "attributes": {
                "title": data.name,
            },
            "id": str(data.watcher.object_ident),
            "_type": "query",
            "links": {"related": data.watcher.object_ident},
        }


class HighlightObjectMixin:
    @staticmethod
    def remove_cut_tags(phrase):
        begin, end = None, None

        open_tag_pos, close_tag_pos = phrase.find("<"), phrase.find(">")
        if open_tag_pos > close_tag_pos:
            begin = close_tag_pos + 1

        open_tag_pos, close_tag_pos = phrase.rfind("<"), phrase.rfind(">")
        if open_tag_pos > close_tag_pos:
            end = open_tag_pos

        return phrase[begin:end]

    @pre_dump
    def replace_highlighted(self, data, **kwargs):
        if hasattr(data, "meta") and hasattr(data.meta, "highlight"):
            hl = data.meta.highlight
            for _field, hits in hl._d_.items():
                field = _field.replace("_exact", "").replace("_synonyms", "")
                setpathattr(
                    data,
                    field,
                    "…".join(complete_invalid_xml(self.remove_cut_tags(hit)) for hit in hits),
                )
        return data
