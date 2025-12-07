import warnings
from collections import OrderedDict

from django.utils.translation import gettext_lazy as _
from marshmallow import validate
from marshmallow.schema import BaseSchema, SchemaMeta
from marshmallow.utils import is_collection

from mcod import settings
from mcod.core.api.search import fields


class ExtSchemaMeta(SchemaMeta):
    def __new__(mcs, name, bases, attrs):
        klass = super().__new__(mcs, name, bases, attrs)
        klass.prepare()
        return klass


class ExtSchema(BaseSchema, metaclass=ExtSchemaMeta):
    __doc__ = BaseSchema.__doc__

    @property
    def api_url(self):
        url = getattr(settings, "API_URL", "https://api.dane.gov.pl")
        api_version = self.context.get("api_version")
        if not api_version:
            request = self.context.get("request")
            api_version = getattr(request, "api_version", None) if request else None
        return f"{url}/{api_version}" if api_version else url

    @property
    def _many(self):
        return getattr(self, "many", False)

    @property
    def _fields(self):
        return getattr(self, "fields", getattr(self, "_declared_fields", None))

    @property
    def doc_schema(self):  # noqa:C901
        _meta_cls = getattr(self, "Meta", None)
        _declared_fields = getattr(self, "_declared_fields", dict())
        if getattr(_meta_cls, "fields", None) or getattr(_meta_cls, "additional", None):
            declared_fields = set(_declared_fields.keys())
            if (
                set(getattr(_meta_cls, "fields", set())) > declared_fields
                or set(getattr(_meta_cls, "additional", set())) > declared_fields
            ):
                warnings.warn(
                    "Only explicitly-declared fields will be included in the Schema Object. "
                    "Fields defined in Meta.fields or Meta.additional are ignored.",
                )
        jsonschema = {
            "type": "object",
            "properties": OrderedDict(),
        }
        if hasattr(_meta_cls, "nullable"):
            jsonschema["nullable"] = True

        exclude = set(getattr(_meta_cls, "exclude", []))

        for field_name, field_obj in self._fields.items():
            if field_name in exclude or field_obj.dump_only or field_obj.load_only:
                continue

            _field_name = field_obj.data_key or field_name
            jsonschema["properties"][_field_name] = field_obj.openapi_property

            partial = getattr(self, "partial", None)
            if field_obj.required:
                if not partial or (is_collection(partial) and field_name not in partial):
                    jsonschema.setdefault("required", []).append(_field_name)

        if "required" in jsonschema:
            jsonschema["required"].sort()

        if _meta_cls is not None:
            if hasattr(_meta_cls, "title"):
                jsonschema["title"] = _meta_cls.title
            if hasattr(_meta_cls, "description"):
                jsonschema["description"] = _meta_cls.description

        if self._many:
            jsonschema = {
                "type": "array",
                "items": jsonschema,
            }

        return jsonschema

    def get_queryset(self, queryset, data):
        return queryset

    @classmethod
    def prepare(cls):
        pass


class NumberTermSchema(ExtSchema):
    term = fields.TermField(example=10)
    terms = fields.TermsField(example=10)
    gt = fields.RangeGtField(example=10)
    gte = fields.RangeGteField(example=10)
    lt = fields.RangeLtField(example=10)
    lte = fields.RangeLteField(example=10)

    class Meta:
        default_field = "term"


class DateTermSchema(ExtSchema):
    term = fields.TermField(example=10)
    terms = fields.TermsField(example=10)
    gt = fields.RangeGtField(example=10)
    gte = fields.RangeGteField(example=10)
    lt = fields.RangeLtField(example=10)
    lte = fields.RangeLteField(example=10)

    class Meta:
        default_field = "term"


class StringTermSchema(ExtSchema):
    term = fields.TermField(example="Lorem")
    terms = fields.TermsField(example="Lorem,Ipsum")
    startswith = fields.WildcardField(wildcard="*{}", example="Lore")
    endswith = fields.WildcardField(wildcard="{}*", example="rem")
    contains = fields.WildcardField(wildcard="*{}*", example="orem")

    class Meta:
        default_field = "term"


class BooleanTermSchema(ExtSchema):
    term = fields.TermField(example="true")

    class Meta:
        default_field = "term"


class StringMatchSchema(ExtSchema):
    prefix = fields.MatchPhrasePrefixField(example="lorem ipsum")
    phrase = fields.MatchPhraseField(example="lorem ips")
    match = fields.MatchField(example="orem ipsu")
    query = fields.QueryStringField(example="*re* AND ipsum")
    suggest = fields.SuggestField(
        example="lorem ips",
        suggester_type="term",
        suggester_name="dataset-title-suggest",
    )

    class Meta:
        default_field = "match"


class CommonSchema(ExtSchema):
    x_api_version = fields.StringField(
        data_key="X-API-VERSION",
        description="Sets API version.",
        example="1.4",
        _in="header",
        allowEmptyValue=True,
    )
    content_language = fields.StringField(
        data_key="Accept-Language",
        description="Sets language code. Supported languages are english (en) and polish (pl)",
        default="pl",
        _in="header",
        allowEmptyValue=True,
    )


class ListingSchema(CommonSchema):
    page = fields.NumberField(
        data_key="page",
        missing=1,
        default=1,
        example=1,
        description="Page number. Default value is 1.",
        validate=validate.Range(1, error=_("Invalid page number")),
    )

    per_page = fields.NumberField(
        missing=25,
        default=25,
        example=10,
        description="Page size. Default value is 25, max allowed page size is 100.",
        validate=validate.Range(1, 100, error=_("Invalid page size")),
    )

    def get_queryset(self, queryset, data):
        if not data:
            return queryset

        dumped = self.dump(data)
        for field_name, t in dumped.items():
            f, d = t
            queryset = f(queryset, d)
        return queryset

    class Meta:
        strict = True


class ListTermsSchema(ExtSchema):
    terms = fields.ListTermsField(example="Lorem,Ipsum")

    class Meta:
        default_field = "terms"


class GeoShapeSchema(ExtSchema):

    geo_shape = fields.RegionsGeoShapeField()

    class Meta:
        default_field = "geo_shape"


class GeoDistanceSchema(ExtSchema):

    dist = fields.GeoDistanceField()

    class Meta:
        default_field = "dist"


class RegionIdTermsSchema(ExtSchema):

    terms = fields.RegionAggregatedTermsField(example=10)

    class Meta:
        default_field = "terms"
