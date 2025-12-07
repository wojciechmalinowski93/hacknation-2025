from marshmallow.schema import BaseSchema, SchemaMeta, SchemaOpts

from mcod.core.api import fields
from mcod.core.registries import csv_serializers_registry


class ModelSchemaOpts(SchemaOpts):
    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.model_name = getattr(meta, "model", None)


class CSVSchemaRegistrator(SchemaMeta):
    def __new__(mcs, name, bases, attrs):
        klass = super().__new__(mcs, name, bases, attrs)
        csv_serializers_registry.register(klass)
        return klass


class CSVSerializer(BaseSchema):
    __doc__ = BaseSchema.__doc__
    OPTIONS_CLASS = ModelSchemaOpts

    def get_csv_headers(self):
        result = []
        for field_name, field in self.fields.items():
            header = field.data_key or field_name
            result.append(header)
        return result


class RDFSchema(BaseSchema, metaclass=SchemaMeta):
    __doc__ = BaseSchema.__doc__
    OPTIONS_CLASS = ModelSchemaOpts


class ListWithoutNoneStrElement(fields.List):
    @fields.after_serialize
    def remove_none(self, value=None):
        if isinstance(value, list) and "none" in value:
            return []
        return value
