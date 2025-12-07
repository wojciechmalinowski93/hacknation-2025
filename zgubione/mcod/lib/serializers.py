import marshmallow as ma
import marshmallow_jsonapi as ja
from django.apps import apps
from django.db.models.manager import BaseManager
from django.utils.translation import get_language
from elasticsearch_dsl.utils import AttrDict, AttrList

from mcod.core.api import fields


class BucketItem(ma.Schema):
    key = ma.fields.Raw()
    title = ma.fields.String()
    doc_count = ma.fields.Integer()

    def __init__(
        self,
        app=None,
        model=None,
        only=None,
        exclude=(),
        many=False,
        context=None,
        load_only=(),
        dump_only=(),
        partial=False,
        unknown=None,
        with_slug=False,
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

        self.orm_model = apps.get_model(app, model) if app and model else None
        self.with_slug = with_slug

    @ma.pre_dump(pass_many=True)
    def update_item(self, data, many, **kwargs):

        _valid_model = self.orm_model and hasattr(self.orm_model, "title")
        if _valid_model:
            objects = self.orm_model.raw.filter(pk__in=[item["key"] for item in data])
        ret = []
        for item in data:
            if _valid_model:
                try:
                    obj = objects.get(pk=item["key"])
                    item["title"] = getattr(obj, "title_i18n", obj.title)
                    if self.with_slug:
                        item["slug"] = getattr(obj, "slug", None)
                    ret.append(item)
                except self.orm_model.DoesNotExist:
                    pass
            else:
                item["title"] = item["key"]
                ret.append(item)

        return ret


class BasicSchema(ja.Schema):
    def generate_url(self, link, **kwargs):
        url = super().generate_url(link, **kwargs)
        api_version = self.context.get("api_version")
        if url and api_version:
            url = "/{}{}".format(api_version, url)
        return url


class BasicSerializer(BasicSchema):
    document_meta = ja.fields.DocumentMeta()

    def __init__(
        self,
        include_data=None,
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
            include_data=include_data,
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )
        self.links = {}

    def dump(self, data, meta=None, links=None, many=None):
        self.included_data = {}
        self.document_meta = meta if meta else self.document_meta
        self.links = links or {}
        return super().dump(data, many=many)

    def wrap_response(self, data, many):
        return {"data": data, "links": self.links}


class ArgsListToDict(ma.Schema):
    @ma.pre_dump
    def prepare_data(self, obj, **kwargs):
        return obj.to_dict()


class SearchMeta(ma.Schema):
    count = ma.fields.Integer(missing=0, attribute="hits.total")
    took = ma.fields.Integer(missing=0, attribute="took")
    max_score = ma.fields.Float(attribute="hits.max_score")


class TranslatedStr(fields.String):
    def _serialize(self, value, attr, obj, **kwargs):
        lang = get_language()
        if value and isinstance(value, (AttrDict, dict)):
            value = getattr(value, lang) or value.pl
        else:
            attr = "{}_{}".format(attr, lang)
            value = getattr(obj, attr, None) or value
        return super()._serialize(value, attr, obj, **kwargs)


class KeywordsList(fields.List):
    def _serialize(self, value, attr, obj, **kwargs):
        tags_list = []
        if not hasattr(obj, attr):
            return tags_list
        lang = get_language()
        if isinstance(value, BaseManager):  # np. końcówka: /datasets/<dataset_id>/
            tags_list = [tag.name for tag in value.filter(language=lang)]
        elif isinstance(value, AttrList):  # np. końcówka: /datasets/
            tags_list = [tag["name"] for tag in value if tag["language"] == lang]
        return [x for x in tags_list if x]
