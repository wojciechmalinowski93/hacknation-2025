import json
from collections import OrderedDict

import jsonschema

from mcod import settings


class JsonStatException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class JsonStatMalformedJson(JsonStatException):
    pass


def validate_v1(json_data):  # noqa: C901
    """Parse a JSON-stat version 1."""
    for dataset_name, dataset_json in json_data.items():
        if "value" not in dataset_json:
            msg = "dataset '{}': missing 'value' key".format(dataset_name)
            raise JsonStatMalformedJson(msg)
        _value = dataset_json["value"]
        if len(_value) == 0:
            msg = "dataset '{}': field 'value' is empty".format(dataset_name)
            raise JsonStatMalformedJson(msg)
        if "status" in dataset_json:
            _status = dataset_json["status"]
            if isinstance(_status, list):
                if len(_status) != 1 and len(_status) != len(_value):
                    msg = "dataset '{}': incorrect size of status fields"
                    raise JsonStatMalformedJson(msg)
            if isinstance(_status, dict):
                # convert key into int
                # eurostat data has incorrect status { "":"" }
                nd = {}
                for k, v in _status.items():
                    try:
                        nd[int(k)] = v
                    except ValueError:
                        pass
                _status = nd
        if "dimension" not in dataset_json:
            msg = "dataset '{}': missing 'dimension' key".format(dataset_name)
            raise JsonStatMalformedJson(msg)

        dimension = dataset_json["dimension"]
        if "id" not in dimension:
            msg = "dataset '{}': missing 'dimension.id' key".format(dataset_name)
            raise JsonStatMalformedJson(msg)

        if "size" not in dimension:
            msg = "dataset '{}': missing 'dimension.size' key".format(dataset_name)
            raise JsonStatMalformedJson(msg)

        pos2iid = dimension["id"]

        _pos2size = dimension["size"]
        for i, e in enumerate(_pos2size):
            _pos2size[i] = int(e)

        if len(pos2iid) != len(_pos2size):
            msg = "dataset '{}': dataset_id is different of dataset_size".format(dataset_name)
            raise JsonStatMalformedJson(msg)
    return bool(json_data)


def validate(spec):
    """
    Function highly inspired by *validate()* from jsonstat.py package.
    Rewritten here due some package dependency problems during installation.
    """
    try:
        import strict_rfc3339  # noqa: F401 validate date-time format in jsonschema
    except ImportError:
        JsonStatException("To validate install jsonschema and strict_rfc3339")

    if not isinstance(spec, dict):
        json_data = json.loads(spec, object_pairs_hook=OrderedDict)
    else:
        json_data = spec

    if "version" not in json_data:
        # if version is not present assuming version 1.x of JSON-stat format.
        if not settings.JSONSTAT_V1_ALLOWED:
            raise JsonStatException("Cannot validate JSON-stat version < 2.0")
        return validate_v1(json_data)

    with open(settings.JSONSTAT_SCHEMA_PATH) as schema_file:
        schema = json.load(schema_file)
        validator = jsonschema.Draft4Validator(schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(json_data), key=lambda e: e.path)
        return len(errors) == 0
