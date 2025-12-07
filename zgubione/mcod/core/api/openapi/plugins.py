import copy
import re
from collections import OrderedDict

import falcon
import yaml
from apispec import BasePlugin
from apispec.exceptions import APISpecError
from apispec.utils import dedent, trim_docstring
from django.template import loader

from mcod.core.utils import resolve_schema_cls


class MCODPlugin(BasePlugin):
    def __init__(self, version):
        self.version = version

    def load_yaml_from_docstring(self, docstring):
        """Loads YAML from docstring."""
        split_lines = trim_docstring(docstring).split("\n")

        # Cut YAML from rest of docstring
        for index, line in enumerate(split_lines):
            line = line.strip()
            if line.startswith("---"):
                cut_from = index
                break
        else:
            return {}
        split_lines = split_lines[cut_from:]
        if len(split_lines) > 1 and split_lines[cut_from + 1].startswith("doc_template"):
            _, template_file = split_lines[cut_from + 1].split(":")
            template_file = template_file.strip()
            template = loader.get_template(template_file)
            yaml_string = template.render({})
        else:
            yaml_string = "\n".join(split_lines)

        yaml_string = dedent(yaml_string)
        return yaml.safe_load(yaml_string) or {}

    def schema_helper(self, name, definition, schema=None, many=False, **kwargs):
        schema_cls = resolve_schema_cls(schema)
        if schema_cls:
            definition.update(schema_cls(many=many).doc_schema)
        return definition

    def operation_helper(self, path=None, operations=None, **kwargs):
        for operation, data in operations.items():
            if "parameters" in data:
                schema_cls = resolve_schema_cls(data["parameters"]["schema"])
                params = []
                for field_name, field_obj in schema_cls()._fields.items():
                    params.append(field_obj.make_doc_param(field_obj._name))
                data["parameters"] = params

    @staticmethod
    def _generate_resource_uri_mapping():
        from mcod.api import app

        routes_to_check = copy.copy(app._router._roots)

        mapping = {}
        for route in routes_to_check:
            uri = route.uri_template
            if uri:
                params = re.findall(r"{(.[^}]*)", uri)
                for param in params:
                    _p = param.split(":")[0]
                    uri = uri.replace(param, _p)
            resource = route.resource
            if resource.__class__ not in mapping:  # prevents overriding by uri with /{api_version}/ prefix.
                mapping[resource.__class__] = uri
            routes_to_check.extend(route.children)

        return mapping

    @staticmethod
    def _prepare_openapi_path(path):

        return

    def path_helper(self, path=None, operations=None, resource=None, **kwargs):
        resource_uri_mapping = self._generate_resource_uri_mapping()
        if resource not in resource_uri_mapping:
            raise APISpecError("Could not find endpoint for resource {0}".format(resource))

        operations = OrderedDict() if not isinstance(operations, OrderedDict) else operations
        path = resource_uri_mapping[resource]

        for method in falcon.constants.HTTP_METHODS:
            http_verb = method.lower()
            method_name = "on_" + http_verb
            if hasattr(resource, method_name):
                _method = getattr(resource, method_name).get_version(str(self.version))
                docstring_yaml = self.load_yaml_from_docstring(_method.__doc__)
                operations[http_verb] = docstring_yaml or dict()
        return path


class TabularDataPlugin(MCODPlugin):
    def path_helper(self, path=None, operations=None, resource=None, **kwargs):
        operations = OrderedDict() if not isinstance(operations, OrderedDict) else operations
        for method in falcon.constants.HTTP_METHODS:
            http_verb = method.lower()
            method_name = "on_" + http_verb
            if hasattr(resource, method_name):
                _method = getattr(resource, method_name).get_version(str(self.version))
                docstring_yaml = self.load_yaml_from_docstring(_method.__doc__)
                operations[http_verb] = docstring_yaml or dict()
        return path

    def schema_helper(self, name, definition, schema_cls=None, many=False, **kwargs):
        if not schema_cls:
            return definition

        definition.update(schema_cls(many=many).doc_schema)
        return definition
