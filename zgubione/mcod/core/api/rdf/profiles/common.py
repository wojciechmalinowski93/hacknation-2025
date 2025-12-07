import abc

from rdflib import RDF, BNode

import mcod.core.api.rdf.namespaces as ns
from mcod import settings
from mcod.lib.rdf.rdf_field import RDFField

RDF_CLASSES = {}

CATALOG_URL = f"{settings.BASE_URL}/dataset"


class RDFNestedField:
    def __init__(
        self,
        class_name,
        predicate=None,
        many=False,
        required=True,
        nested_non_bnode=True,
    ):
        self.class_name = class_name
        self.predicate = predicate
        self.many = many
        self.required = required
        self.nested_non_bnode = nested_non_bnode

    def make_instance(self, subject):
        rdf_class = RDF_CLASSES[self.class_name]
        return rdf_class(subject=subject)


class RDFMeta(abc.ABCMeta):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        cls.fields = {}
        for base in bases:
            cls.fields.update(base.fields)
        for key, value in attrs.items():
            if isinstance(value, (RDFField, RDFNestedField)):
                cls.fields[key] = value

        RDF_CLASSES[name] = cls
        return cls


class RDFClass(metaclass=RDFMeta):
    def __init__(self, subject=None, predicate=None, many=False, singleton=False):
        self.subject = subject
        self.predicate = predicate
        self.many = many
        self.singleton = singleton

    def get_subject(self, data):
        return self.subject or BNode()

    def get_data(self, data):
        return data

    def make_triple(self, subject, *, field_name, object=None, object_value=None):
        field = self.fields[field_name]

        if not field:
            raise ValueError(f"Could not find field '{field_name}' in context.")

        object_value = object_value or field.object_value
        if field.object_value_to_uppercase and isinstance(object_value, str):
            object_value = object_value.upper()

        object = object or field.object

        if not field.allow_null and object is None and object_value is None:
            object_value = ""

        kwargs = {}
        if field.base_uri:
            try:
                kwargs["base"] = self.VOCABULARIES[field.base_uri]
            except KeyError:
                pass

        if object_value is None:
            object_value = field.value_on_null

        object = object or field.object_type(object_value, **kwargs)
        if field.swap_subject_and_object:
            subject, object = object, subject

        return (
            subject,
            field.predicate,
            object,
        )

    def to_triples(self, data, include_nested_triples=True):  # noqa
        subject = self.get_subject(data)
        data = self.get_data(data)
        triples = []
        for name, field in self.fields.items():
            if isinstance(field, RDFField):
                if field.object_value:
                    object_value = field.object_value
                elif field.object is None:
                    try:
                        object_value = data[name]
                        if not field.required and not object_value:
                            continue
                    except Exception:
                        if not field.required:
                            continue
                        raise
                else:
                    object_value = None

                try:
                    if field.many:
                        for element in object_value:
                            triples.append(
                                self.make_triple(
                                    subject=subject,
                                    object_value=element,
                                    field_name=name,
                                )
                            )
                    else:
                        triples.append(
                            self.make_triple(
                                subject=subject,
                                object_value=object_value,
                                field_name=name,
                            )
                        )
                except Exception:
                    raise
            elif isinstance(field, RDFNestedField):
                get_subject = getattr(self, f"get_{name}_subject", None)
                inner_data_func = getattr(self, f"get_{name}_data", None)
                if inner_data_func:
                    inner_data = inner_data_func(data)
                else:
                    try:
                        inner_data = data[name]
                    except KeyError:
                        if not field.required:
                            continue
                        raise

                if not field.many:
                    inner_data = [inner_data]

                for row in inner_data:
                    if get_subject:
                        inner_subject = get_subject(data=row)
                    else:
                        if row is None and not field.required:
                            continue
                        inner_subject = row["subject"]

                    if inner_subject is None:
                        continue

                    triples.append((subject, field.predicate, inner_subject))
                    if (include_nested_triples and field.nested_non_bnode) or isinstance(inner_subject, BNode):
                        instance = field.make_instance(subject=inner_subject)
                        triples.extend(instance.to_triples(row))

        return triples

    def from_triples(self, triple_store):
        _fields = self.fields.copy()
        rdf_type = _fields.pop("rdf_type")
        store_data = []
        for subject in triple_store.subjects(predicate=rdf_type.predicate, object=rdf_type.object):
            store_data.append(self.get_subject_data(subject, _fields, triple_store))
        return store_data

    def get_subject_data(self, subject, _fields, triple_store):
        subject_data = {}
        for field_name, field in _fields.items():
            if isinstance(field, RDFNestedField):
                rdf_instance = field.make_instance(subject=subject)
                nested_values = rdf_instance.from_triples(triple_store)
                subject_data[field_name] = nested_values
            else:
                get_object_func = getattr(self, f"get_{field_name}_object", None)
                if get_object_func:
                    object_values = get_object_func(triple_store, subject, field)
                else:
                    object_values = []
                    for value in triple_store.objects(subject=subject, predicate=field.predicate):
                        result_val = field.parse_value(value)
                        if result_val is not None:
                            object_values.append(result_val)
                try:
                    subject_data[field_name] = object_values if field.many else object_values[0]
                except IndexError:
                    subject_data[field_name] = [] if field.many else None
        return subject_data


class HYDRAPagedCollection(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.HYDRA.PagedCollection)

    count = RDFField(predicate=ns.HYDRA.totalItems)
    per_page = RDFField(predicate=ns.HYDRA.itemsPerPage)
    next_page = RDFField(predicate=ns.HYDRA.nextPage, required=False)
    last_page = RDFField(predicate=ns.HYDRA.lastPage, required=False)
    prev_page = RDFField(predicate=ns.HYDRA.previousPage, required=False)
    first_page = RDFField(predicate=ns.HYDRA.firstPage, required=False)

    def get_subject(self, data):
        return BNode("PagedCollection")
