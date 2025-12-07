from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import (
    DataRelationship,
    ObjectAttrs,
    Relationship,
    Relationships,
    TopLevel,
)
from mcod.lib.serializers import TranslatedStr


class GuideApiRelationships(Relationships):
    items = fields.Nested(
        DataRelationship,
        many=False,
        _type="item",
        path="items",
        show_data=True,
        required=True,
        default=[],
    )


class GuideItemApiRelationships(Relationships):
    guide = fields.Nested(
        Relationship,
        required=True,
        _type="guide",
        url_template="{api_url}/guides/{ident}",
    )


class GuideApiAttrs(ObjectAttrs):
    title = TranslatedStr(data_key="name")

    class Meta:
        relationships_schema = GuideApiRelationships
        object_type = "guide"
        url_template = "{api_url}/guides/{ident}"
        ordered = True
        model = "guides.Guide"


class GuideItemApiAttrs(ObjectAttrs):
    title = TranslatedStr(data_key="name")
    content = TranslatedStr()
    route = fields.Str()
    css_selector = fields.Str()
    position = fields.Str()
    order = fields.Int()
    is_optional = fields.Bool()
    is_clickable = fields.Bool()
    is_expandable = fields.Bool()

    class Meta:
        relationships_schema = GuideItemApiRelationships
        object_type = "item"
        url_template = "{api_url}/guides/{ident}"
        ordered = True
        model = "guides.GuideItem"


class GuideApiResponse(TopLevel):
    class Meta:
        attrs_schema = GuideApiAttrs
