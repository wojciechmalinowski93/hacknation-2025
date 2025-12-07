import typing

from marshmallow import post_dump
from marshmallow.decorators import POST_DUMP, PRE_DUMP
from pyshacl import validate as shacl_validate

from mcod import settings
from mcod.core.serializers import RDFSchema as Schema

_T = typing.TypeVar("_T")


class ResponseSchema(Schema):
    include_nested_triples = True

    @property
    def _fields(self):
        return getattr(self, "fields", getattr(self, "_declared_fields", None))

    def dump(self, obj: typing.Any, *, many: typing.Optional[bool] = None):
        """Serialize an object to native Python data types according to this
        Schema's fields.

        :param obj: The object to serialize.
        :param many: Whether to serialize `obj` as a collection. If `None`, the value
            for `self.many` is used.
        :return: A dict of serialized data
        :rtype: dict

        .. versionadded:: 1.0.0
        .. versionchanged:: 3.0.0b7
            This method returns the serialized data rather than a ``(data, errors)`` duple.
            A :exc:`ValidationError <marshmallow.exceptions.ValidationError>` is raised
            if ``obj`` is invalid.
        .. versionchanged:: 3.0.0rc9
            Validation no longer occurs upon serialization.
        """
        many = self.many if many is None else bool(many)
        # This method is overridden because we don't want to flatten original object into simple list,
        # we might need other attributes if obj is a more complex structure, for example with aggregation data from ES
        if self._has_processors(PRE_DUMP):
            processed_obj = self._invoke_dump_processors(PRE_DUMP, obj, many=many, original_data=obj)
        else:
            processed_obj = obj

        result = self._serialize(processed_obj, many=many)

        if self._has_processors(POST_DUMP):
            result = self._invoke_dump_processors(POST_DUMP, result, many=many, original_data=obj)

        return result

    @post_dump(pass_many=True)
    def validate_shape(self, data, many, **kwargs):
        shape = self.context["request"].params.get("shacl", False) if "request" in self.context else False
        if not shape:
            return data

        shape_path = settings.SHACL_SHAPES[shape]
        conforms, results_graph, results_text = shacl_validate(
            data_graph=data,
            shacl_graph=shape_path,
            ont_graph=None,
            inference="rdfs",
            abort_on_error=False,
            meta_shacl=False,
            advanced=False,
            debug=False,
            allow_warnings=True,
        )
        return results_graph
