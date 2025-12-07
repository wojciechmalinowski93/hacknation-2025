from modelcluster.models import get_all_child_relations
from wagtail.api.v2.serializers import BaseSerializer, TagsField

from mcod.cms.api.fields import (
    CharField,
    ChildRelationField,
    DetailUrlField,
    IntegerField,
    PageChildrenField,
    PageHtmlUrlField,
    PageParentField,
    PageTypeField,
)


class CmsPageSerializer(BaseSerializer):
    type = PageTypeField(read_only=True)
    title = CharField(source="title_i18n", fallback_source="title")
    html_url = PageHtmlUrlField(read_only=True)
    parent = PageParentField(read_only=True)
    children = PageChildrenField(read_only=True)
    children_count = IntegerField(read_only=True)
    detail_url = DetailUrlField(read_only=True)

    def build_relational_field(self, field_name, relation_info):
        # Find all relation fields that point to child class and make them use
        # the ChildRelationField class.
        if relation_info.to_many:
            model = getattr(self.Meta, "model")
            child_relations = {
                child_relation.field.remote_field.related_name: child_relation.related_model
                for child_relation in get_all_child_relations(model)
            }

            if field_name in child_relations and field_name in self.child_serializer_classes:
                return ChildRelationField, {"serializer_class": self.child_serializer_classes[field_name]}

        return super().build_relational_field(field_name, relation_info)


class NewsPageSerializer(CmsPageSerializer):
    body = CharField(source="body_i18n", fallback_source="body")
    author = CharField(source="author_i18n", fallback_source="author")
    tags = TagsField(source="tags_i18n")


def get_serializer_class(
    model,
    field_names,
    meta_fields,
    field_serializer_overrides=None,
    child_serializer_classes=None,
    base=BaseSerializer,
):
    model_ = model

    class Meta:
        model = model_
        fields = list(field_names)

    attrs = {
        "Meta": Meta,
        "meta_fields": list(meta_fields),
        "child_serializer_classes": child_serializer_classes or {},
    }

    if field_serializer_overrides:
        attrs.update(field_serializer_overrides)

    return type(str(model_.__name__ + "Serializer"), (base,), attrs)
