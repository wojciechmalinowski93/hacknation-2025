from marshmallow.schema import BaseSchema
from querystring_parser import parser as qs_parser
from webargs import core
from webargs.core import dict2schema, get_value, json
from webargs.falconparser import FalconParser


class Parser(FalconParser):
    def parse(
        self,
        argmap,
        req=None,
        locations=None,
        validate=None,
        error_status_code=None,
        error_headers=None,
    ):

        qs = "&".join(part for part in req.query_string.split("&") if ("=" in part and part[-1] != "="))
        req._params = qs_parser.parse(qs)
        return super().parse(
            argmap,
            req=req,
            locations=locations,
            validate=validate,
            error_status_code=error_status_code,
            error_headers=error_headers,
        )

    def parse_querystring(self, req, name, field):
        data = field.prepare_data(name, req.params) if hasattr(field, "prepare_data") else req.params
        return core.get_value(data, name, field)

    def parse_json(self, req, name, field):
        json_data = self._cache.get("json_data")
        if json_data is None:
            try:
                self._cache["json_data"] = json_data = req.media
            except json.JSONDecodeError as e:
                return self.handle_invalid_json_error(e, req)
        return get_value(json_data, name, field, allow_many_nested=True)

    def _get_schema(self, argmap, req):
        if isinstance(argmap, BaseSchema):
            schema = argmap
        elif isinstance(argmap, type) and issubclass(argmap, BaseSchema):
            schema = argmap()
        elif callable(argmap):
            schema = argmap(req)
        else:
            schema = dict2schema(argmap, self.schema_class)()
        return schema
