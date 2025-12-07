import os
import uuid
from collections import OrderedDict, namedtuple
from datetime import datetime, time

import shapefile
from constance import config as constance_config
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_elasticsearch_dsl import Index
from elasticsearch import exceptions as es_exceptions
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Document, field as dsl_field
from elasticsearch_dsl.connections import Connections
from goodtables import validate as validate_table
from tableschema import config

from mcod import settings
from mcod.core.api import fields as api_fields
from mcod.core.api.search.analyzers import polish_analyzer
from mcod.resources.archives import ArchiveReader
from mcod.resources.geo import (
    ShapeTransformer,
    clean_house_number,
    extract_coords_from_uaddress,
    geocode,
    median_point,
)
from mcod.resources.goodtables_checks import ZERO_DATA_ROWS
from mcod.resources.type_guess import Table

es_connections = Connections()
es_connections.configure(**settings.ELASTICSEARCH_DSL)


class FileEncodingValidationError(Exception):
    pass


class ResourceDataValidationError(Exception):
    pass


def get_float_or_none(value):
    try:
        val = float(value)
    except ValueError:
        val = None
    return val


class IndexedData:
    _type = None

    def __init__(self, resource):
        self.resource = resource
        idx_prefix = getattr(settings, "ELASTICSEARCH_INDEX_PREFIX", None)
        self.idx_name = "resource-{}".format(self.resource.id)
        if idx_prefix:
            worker = os.environ.get("PYTEST_XDIST_WORKER", "")
            idx_prefix = f"{idx_prefix}-{worker}"
            self.idx_name = "{}-{}".format(idx_prefix, self.idx_name)
        self._idx_cache = None
        self._doc_cache = None
        self._reversed_headers_map_cache = None
        self._headers_map_cache = None

    @property
    def data_schema(self):
        return self.get_schema(use_aliases=True)

    @property
    def data_type(self):
        return self._type

    @property
    def id(self):
        return self.resource.id

    @property
    def available(self):
        if not self.idx.exists():
            return False
        return self.resource.data_is_valid

    def prepare_doc(self):
        raise NotImplementedError

    @property
    def doc(self):
        if not self._doc_cache:
            self._doc_cache = self.prepare_doc()
        return self._doc_cache

    def get_api_fields(self):
        raise NotImplementedError

    def get_sort_map(self):
        sort_map = {}
        for k, v in self.get_api_fields().items():
            f = f"{k}.val"
            if isinstance(v, api_fields.String):
                f = f"{f}.keyword"
            elif isinstance(v, api_fields.Date):
                f = f"{f}.date"
            elif isinstance(v, api_fields.Time):
                f = f"{f}.time"
            elif isinstance(v, api_fields.DateTime):
                f = f"{f}.datetime"
            sort_map[k] = f
        return sort_map

    @property
    def idx(self):
        if not self._idx_cache:
            self._idx_cache = Index(self.idx_name)
        return self._idx_cache

    @property
    def missing_values(self):
        return list(set(config.DEFAULT_MISSING_VALUES + self.resource.special_signs_symbols_list))

    @property
    def qs(self):
        return self.doc.search()

    def validate(self):
        pass

    @property
    def reversed_headers_map(self):
        if not self._reversed_headers_map_cache:
            try:
                headers = self.idx.get_mapping()[self.idx_name]["mappings"]["doc"]["_meta"]["headers"]
            except (es_exceptions.NotFoundError, KeyError):
                headers = self.doc._doc_type.mapping._meta["_meta"]["headers"]
            headers = {item: key for key, item in headers.items()}
            self._reversed_headers_map_cache = OrderedDict(
                sorted(
                    headers.items(),
                    key=lambda x: int(x[1].strip("col").strip("_origin")),
                )
            )
        return self._reversed_headers_map_cache

    @property
    def headers_map(self):
        if not self._headers_map_cache:
            self._headers_map_cache = {v: k for k, v in self.reversed_headers_map.items()}
        return self._headers_map_cache

    def iter(self, qs=None, from_=0, size=25, sort=None):
        _search = qs or self.qs
        kwargs = {"from_": from_, "size": size}
        if sort:
            kwargs["sort"] = sort
        _search = _search.extra(**kwargs)
        results = _search.execute()
        for result in results.hits:
            yield result

    def get_schema(self, **kwargs):
        raise NotImplementedError

    @property
    def schema(self):
        return self.doc.search()

    def _docs_iter(self, doc):
        raise NotImplementedError

    def index(self, force=False, chunk_size=500):
        doc = self.doc
        if force:
            self.idx.delete(ignore_unavailable=True)

        self.idx.settings(**settings.ELASTICSEARCH_DSL_INDEX_SETTINGS)
        self.idx.mapping(doc._doc_type.mapping)
        if not self.idx.exists():
            self.idx.create()

        es = es_connections.get_connection()

        success, failed = bulk(
            es,
            (d.to_dict(True) for d in self._docs_iter(doc)),
            index=self.idx_name,
            doc_type=doc._doc_type.name,
            chunk_size=chunk_size,
            stats_only=True,
        )

        if success:
            self.idx.flush()

        return success, failed

    @property
    def has_geo_data(self):
        return False

    @property
    def is_chartable(self):
        return False


DBSchemaField = namedtuple("DBFSchemaField", ["name", "type", "length", "decimal_length"])


class ShpData(IndexedData):
    _type = "geo"

    _schema2doc_map = {
        "C": dsl_field.Text(
            analyzer=polish_analyzer,
            fields={
                "raw": dsl_field.Text(),
                "keyword": dsl_field.Keyword(),
            },
        ),
        "D": dsl_field.Date(),
        "N": dsl_field.ScaledFloat(scaling_factor=100),
        "L": dsl_field.Boolean(),
        "@": dsl_field.Date(),
        "I": dsl_field.Long(),
        "+": dsl_field.Long(),
        "F": dsl_field.Float(),
        "O": dsl_field.Double(),
    }

    _schema_to_api_field = {
        "C": api_fields.String,
        "D": api_fields.DateTime,
        "N": api_fields.Number,
        "L": api_fields.Boolean,
        "@": api_fields.DateTime,
        "I": api_fields.Number,
        "+": api_fields.Number,
        "F": api_fields.Number,
        "O": api_fields.Number,
    }

    _schema_long_names = {
        "C": "string",
        "D": "datetime",
        "N": "number",
        "L": "boolean",
        "@": "datetime",
        "I": "integer",
        "+": "integer",
        "F": "number",
        "O": "number",
    }

    _source = None
    _schema = None
    _transformer = None

    def __init__(self, resource, from_table_index=False):
        super().__init__(resource)
        self.from_table_index = from_table_index

    @property
    def has_geo_data(self):
        return True

    @property
    def is_chartable(self):
        fields = self.schema
        return len(fields) > 1 and any((field.type in ("N", "I", "+", "F", "O") for field in fields))

    @property
    def source(self):
        if not self._source:
            with ArchiveReader(self.resource.main_file.path) as extracted:
                shp_path = next(extracted.get_by_extension("shp"))
                self._source = shapefile.Reader(shp_path)
                prj_path = next(extracted.get_by_extension("prj"))
                self._transformer = ShapeTransformer(prj_path)
        return self._source

    def get_schema(self, **kwargs):
        use_aliases = kwargs.get("use_aliases", False)
        headers = self.reversed_headers_map
        return {
            "fields": [
                {
                    "name": headers[item.name] if use_aliases else item.name,
                    "type": self._schema_long_names[item.type],
                    "format": "default",
                }
                for item in self.schema
            ]
        }

    @property
    def schema(self):
        if not self._schema:
            self._schema = [DBSchemaField(*_f) for _f in self.source.fields[1:]]
        return self._schema

    def prepare_doc(self):
        _fields = {
            "shape": dsl_field.GeoShape(),
            "point": dsl_field.GeoPoint(),
            "shape_type": dsl_field.Integer(),
            "label": dsl_field.Text(),
            "resource": dsl_field.Nested(
                properties={
                    "id": dsl_field.Integer(),
                    "title": dsl_field.Text(analyzer=polish_analyzer, fields={"raw": dsl_field.Keyword()}),
                }
            ),
            "updated_at": dsl_field.Date(),
            "row_no": dsl_field.Long(),
        }
        _map = {}

        for idx, _f in enumerate(self.schema, 1):
            if _f.type not in self._schema2doc_map:
                continue
            alias_name = _f.name
            field_name = f"col{idx}"
            _field = self._schema2doc_map[_f.type]
            _map[field_name] = alias_name
            _fields[field_name] = _field
            _fields["Index"] = type("Index", (type,), {"name": self.idx_name})

        doc = type(self.idx_name, (Document,), _fields)
        doc._doc_type.mapping._meta["_meta"] = {"headers": _map}
        return doc

    def get_api_fields(self):
        record_fields = {}
        for f in self.schema:
            field_name = self.reversed_headers_map[f.name]
            field_cls = self._schema_to_api_field[f.type]
            record_fields[field_name] = field_cls(is_tabular_data_field=True)
        return record_fields

    @staticmethod
    def _get_row_id(row):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, "+|+".join(str(i)[:10000] for i in row)))

    def _docs_iter(self, doc):
        for row_no, sr in enumerate(self.source.shapeRecords(), 1):
            geojson = self._transformer.transform(sr.shape)
            v = {
                "shape": geojson,
                "updated_at": datetime.now(),
                "row_no": row_no,
                "resource": {"id": self.resource.id, "title": self.resource.title},
            }
            for i, val in enumerate(sr.record, 1):
                v[f"col{i}"] = val if val != b"" else None

            v["shape_type"] = sr.shape.shapeType
            v["point"] = median_point(geojson)
            tds = self.resource.tabular_data_schema
            if tds is not None and "geo" in tds and "label" in tds["geo"]:
                v["label"] = sr.record[tds["geo"]["label"].get("col_name")]
            d = doc(**v)
            d.meta.id = self._get_row_id(sr.record)
            yield d


def prepare_item(item, col_type=None, special_signs=None):
    """
    Prepare some values to work with ElasticSearch.
    We need this because cast of values is disabled in function:

        def _docs_iter(self, doc):
            for row_no, row in enumerate(self.table.iter(keyed=True, cast=False)):

    you may need to combine this with the column type in the future
    """
    if col_type == "date" and isinstance(item, datetime):
        item = item.strftime("%Y-%m-%d")
    elif col_type == "time" and isinstance(item, time):
        item = item.strftime("%H:%M:%S")
    item = None if item == "" else item
    repr_item = str(item) if item is not None and isinstance(item, (int, float)) else item
    return {
        "repr": item,
        "val": None if special_signs and repr_item in special_signs else item,
    }


class CustomObject(dsl_field.Object):

    def _serialize(self, data):
        """Ensures that both: old (val) and new {'val': val, 'repr': val} tabular data structures works properly."""
        if isinstance(data, dict) and "repr" in data and "val" in data:
            return super()._serialize(data)
        return {"repr": data, "val": data}

    def _deserialize(self, data):
        """Ensures that data from es is returned in new way (as dict with repr and val keys)."""
        if isinstance(data, dict) and "repr" in data and "val" in data:
            pass
        else:
            data = {"repr": data, "val": data}
        return super()._deserialize(data)


class TabularData(IndexedData):
    _type = "table"

    @property
    def _schema2doc_map(self):
        _map = {
            "integer": dsl_field.Long(),
            "number": dsl_field.ScaledFloat(scaling_factor=100),
            "string": dsl_field.Text(
                analyzer=polish_analyzer,
                fields={
                    "raw": dsl_field.Text(),
                    "keyword": dsl_field.Keyword(),
                },
            ),
            "any": dsl_field.Text(
                analyzer=polish_analyzer,
                fields={
                    "raw": dsl_field.Text(),
                    "keyword": dsl_field.Keyword(),
                },
            ),
            "boolean": dsl_field.Boolean(),
            "time": dsl_field.Text(
                fields={
                    "text": dsl_field.Text(),
                    "time": dsl_field.Date(format=constance_config.TIME_FORMATS),
                }
            ),
            "duration": dsl_field.DateRange(),
            "default": dsl_field.Text(),
            "date": dsl_field.Text(
                fields={
                    "text": dsl_field.Text(),
                    "date": dsl_field.Date(format=constance_config.DATE_FORMATS),
                }
            ),
            "datetime": dsl_field.Text(
                fields={
                    "text": dsl_field.Text(),
                    "datetime": dsl_field.Date(format=constance_config.DATE_FORMATS),
                }
            ),
        }
        for key, val in _map.items():
            _map[key] = CustomObject(
                properties={
                    "val": val,
                    "repr": dsl_field.Keyword(),
                }
            )
        return _map

    _schema_to_api_field = {
        "integer": api_fields.Number,
        "number": api_fields.Number,
        "string": api_fields.String,
        "any": api_fields.String,
        "boolean": api_fields.Boolean,
        "date": api_fields.Date,
        "datetime": api_fields.DateTime,
        "time": api_fields.Time,
    }

    def __init__(self, resource):
        super().__init__(resource)
        self._table_cache = None
        self._schema_cache = None
        self._reversed_headers_map_cache = None

    @property
    def has_geo_data(self):
        return (
            "geo" in self.schema
            and "label" in self.schema["geo"]
            and any(
                (
                    "uaddress" in self.schema["geo"],
                    all(k in self.schema["geo"] for k in ("b", "l")),
                    all(k in self.schema["geo"] for k in ("place", "postal_code")),
                )
            )
        )

    @property
    def is_chartable(self):
        fields = self.schema["fields"]
        return len(fields) > 1 and any((field["type"] in ("number", "integer") for field in fields))

    @property
    def resource_format(self):
        compressed_format = self.resource.main_file_compressed_format
        return compressed_format if compressed_format else self.resource.format

    @property
    def resource_encoding(self):
        compressed_encoding = self.resource.main_file_compressed_encoding
        return compressed_encoding if compressed_encoding else self.resource.main_file_encoding

    def prepare_doc(self):
        _fields, _map = {}, {}
        for idx, _f in enumerate(self.schema["fields"], 1):
            alias_name = _f["name"]
            field_name = "col{}".format(idx)
            _field = self._schema2doc_map[_f["type"]]
            _map[field_name] = alias_name
            _fields[field_name] = _field

        if self.has_geo_data:
            _fields["shape"] = dsl_field.GeoShape()
            _fields["point"] = dsl_field.GeoPoint()
            _fields["label"] = dsl_field.Text()
            _fields["shape_type"] = dsl_field.Integer()

        _fields["resource"] = dsl_field.Nested(
            properties={
                "id": dsl_field.Integer(),
                "title": dsl_field.Text(analyzer=polish_analyzer, fields={"raw": dsl_field.Keyword()}),
            }
        )

        _fields["updated_at"] = dsl_field.Date()
        _fields["row_no"] = dsl_field.Long()
        _fields["Index"] = type("Index", (type,), {"name": self.idx_name})

        doc = type(self.idx_name, (Document,), _fields)
        doc._doc_type.mapping._meta["_meta"] = {"headers": _map}
        return doc

    def get_api_fields(self):
        _fields = {}
        for _f in self.schema["fields"]:
            field_name = self.reversed_headers_map[_f["name"]]
            field_cls = self._schema_to_api_field[_f["type"]]
            _fields[field_name] = field_cls(
                description="Value of *{}* column".format(_f["name"]),
                is_tabular_data_field=True,
            )
        return _fields

    @staticmethod
    def _row_2_dict(row):
        return {"col{}".format(idx): value for idx, value in enumerate(row, 1)}

    @staticmethod
    def _get_row_id(row):
        if isinstance(row, dict):
            row = row.values()
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, "+|+".join(str(i)[:10000] for i in row)))

    def get_schema(self, **kwargs):
        use_aliases = kwargs.get("use_aliases", False)
        revalidate = kwargs.get("revalidate", False)
        _schema = self.infer_schema() if revalidate else self.schema
        if use_aliases:
            _schema = dict(_schema)
            headers = self.reversed_headers_map
            _fields = [
                {
                    "name": headers[item["name"]],
                    "type": item["type"] if item["type"] != "any" else "string",
                    "format": item["format"],
                }
                for item in _schema["fields"]
            ]
            _schema["fields"] = _fields

        return _schema

    def infer_schema(self):
        if not self.resource.main_file:
            raise ValidationError(_("File does not exist"))

        if not self.resource.has_tabular_format():
            raise ValidationError(_("Invalid file type"))

        _table = Table(
            self.resource.file_data_path,
            ignore_blank_headers=True,
            format=self.resource_format,
            encoding=self.resource_encoding or "utf-8",
            skip_rows={"type": "preset", "value": "blank"},
        )
        _schema = _table.infer(limit=5000, missing_values=self.missing_values)
        [x.update({"type": "string"}) for x in _schema["fields"] if x["type"] in ["geopoint", "missing"]]

        return _schema

    @property
    def schema(self):
        if not self.resource.main_file:
            raise ValidationError(_("File does not exist"))

        if not self.resource.has_tabular_format():
            raise ValidationError(_("Invalid file type"))

        if not self._schema_cache:
            _schema = self.resource.tabular_data_schema or None
            if not _schema:
                _schema = self.infer_schema()
            self._schema_cache = _schema

        return self._schema_cache

    def validate(self):
        kwargs = dict(
            checks=["structure", "schema", ZERO_DATA_ROWS],
            skip_checks=["extra-header", "blank-header", "blank-row", "duplicate-row"],
            error_limit=10,
            format=self.resource_format,
            preset="table",
            encoding=self.resource_encoding,
            skip_rows={"type": "preset", "value": "blank"},
        )
        if self.resource.tabular_data_schema:
            kwargs["schema"] = self.get_schema()
            try:
                # set separator to semicolon to enable detection of CSV validation error
                # when in a CSV file semicolon is used for separation - OTD-1282
                if (
                    self.resource_format == "csv"
                    and len(kwargs["schema"]["fields"]) == 1
                    and ";" in kwargs["schema"]["fields"][0]["name"]
                ):
                    kwargs["delimiter"] = ";"
            except (KeyError, TypeError):
                pass
        else:
            kwargs["infer_schema"] = True

        report = validate_table(self.resource.file_data_path, **kwargs)
        if not report["valid"]:
            raise ResourceDataValidationError(report["tables"][0]["errors"])

        return report

    @property
    def headers(self):
        return [header[0] for header in self.reversed_headers_map]

    @property
    def table(self):
        if not self._table_cache:
            self._table_cache = Table(
                self.resource.file_data_path,
                ignore_blank_headers=True,
                schema=self.schema or None,
                format=self.resource_format,
                encoding=self.resource_encoding or "utf-8",
            )
        return self._table_cache

    @staticmethod
    def _get_point(row, gd):
        def get_col(col):
            return row[gd[col]["col_name"]] or ""

        point = None
        if all(co in gd for co in ("l", "b")):
            l, b = get_float_or_none(get_col("l")), get_float_or_none(get_col("b"))
            if l and b:
                point = [l, b]
        elif "uaddress" in gd:
            point = extract_coords_from_uaddress(get_col("uaddress"))
        elif all(co in gd for co in ("place", "postal_code")):
            kwargs = dict(postalcode=get_col("postal_code"), locality=get_col("place"))
            if "street" in gd:
                kwargs["address"] = get_col("street")
                if "house_number" in gd:
                    kwargs["address"] += f" {clean_house_number(get_col('house_number'))}"
            point = geocode(**kwargs)
            if point:
                point = point["coordinates"]
        return point

    def _docs_iter(self, doc):

        for row_no, row in enumerate(self.table.iter(keyed=True, cast=False)):
            if not row:
                continue

            if isinstance(row, (list, tuple)):
                row = self._row_2_dict(row)
            if isinstance(row, dict) and all(x is None for x in row.values()):
                # do not generate document for empty row.
                continue
            r = dict()

            for i, item_ in enumerate(row.items()):
                field_name, item = item_
                col_type = self.schema["fields"][i].get("type")
                r[self.reversed_headers_map.get(field_name, field_name)] = prepare_item(
                    item, col_type, special_signs=self.missing_values
                )

            row_id = self._get_row_id(r)
            r.update(
                {
                    "updated_at": datetime.now(),
                    "row_no": row_no + 1,
                    "resource": {"id": self.resource.id, "title": self.resource.title},
                }
            )

            if self.schema:
                gd = self.schema.get("geo", {})
                if gd:
                    point = self._get_point(row, gd)
                    if point is not None:
                        r.update(
                            {
                                "shape": {"type": "Point", "coordinates": point},
                                "point": point,
                                "label": row[gd["label"]["col_name"]],
                                "shape_type": 1,
                            }
                        )
            d = doc(**r)
            d.meta.id = row_id
            yield d
