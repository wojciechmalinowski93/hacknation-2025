from typing import List

import falcon
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from elasticsearch import TransportError
from elasticsearch_dsl import InnerDoc, Q
from marshmallow import ValidationError
from querystring_parser.parser import MalformedQueryStringError

from mcod.core.api.parsers import Parser
from mcod.core.db.models import BaseExtendedModel
from mcod.core.utils import disable_modeltracker
from mcod.lib.rdf.store import get_sparql_store
from mcod.unleash import is_enabled


class BaseHdlr:
    def __init__(self, request, response):
        self.request = request
        self.response = response
        if hasattr(self, "deserializer_schema"):
            self.deserializer = self.deserializer_schema(
                context={
                    "request": self.request,
                }
            )
        if hasattr(self, "serializer_schema"):
            self.serializer = self.serializer_schema(
                context={
                    "request": self.request,
                }
            )

    def run(self, *args, **kwargs):
        self.request.context.cleaned_data = self.clean(*args, **kwargs)
        return self.serialize(*args, **kwargs)

    def clean(self, *args, validators=None, locations=None, **kwargs):
        if hasattr(self, "deserializer"):
            locations = locations or ("query",)
            try:
                result = Parser(
                    locations=locations,
                ).parse(self.deserializer, req=self.request, validate=validators)
                return result
            except MalformedQueryStringError:
                raise falcon.HTTPBadRequest(description=_("malformed query string"))
        return {}

    def prepare_context(self, *args, **kwargs):
        cleaned = getattr(self.request.context, "cleaned_data", {})
        debug_enabled = getattr(self.response.context, "debug", False)
        if debug_enabled:
            self.response.context.query = self._get_debug_query(cleaned, *args, **kwargs)
        result = self._get_data(cleaned, *args, **kwargs)
        self.response.context.meta = {}
        if result:
            self.response.context.data = result
            self.response.context.meta = self._get_meta(result, *args, **kwargs)
            included = [x for x in self._get_included(result, *args, **kwargs) if x]
            if included:
                self.response.context.included = included

    def serialize(self, *args, **kwargs):
        self.prepare_context(*args, **kwargs)
        if is_enabled("S65_fix_long_api_response.be"):
            with disable_modeltracker():
                return self.serializer.dump(self.response.context)
        else:
            return self.serializer.dump(self.response.context)

    def _get_data(self, cleaned, *args, **kwargs):
        return cleaned

    def _get_meta(self, cleaned, *args, **kwargs):
        return {}

    def _get_included(self, result, *args, **kwargs):
        return []

    def _get_debug_query(self, cleaned, *args, **kwargs):
        return {}


class IncludeMixin:
    include_default = []
    _includes = {
        "comment": "schedules.Comment",
        "dataset": "datasets.Dataset",
        "institution": "organizations.Organization",
        "resource": "resources.Resource",
        "schedule": "schedules.Schedule",
        "user": "users.User",
        "user_schedule": "schedules.UserSchedule",
        "user_schedule_item": "schedules.UserScheduleItem",
        "related_resource": "resources.Resource",
    }
    _include_map = {
        "related_resource": "related_resource_published",
    }

    def _get_included_ids(self, result, field):
        if issubclass(result.__class__, (AbstractBaseUser, BaseExtendedModel)):
            related = getattr(result, field, getattr(result, "{}s".format(field), None))
            if related:
                if related.__class__.__name__ in [
                    "ManyRelatedManager",
                    "RelatedManager",
                ] or isinstance(related, QuerySet):
                    return related.values_list("id", flat=True)
                return [related.id]
            return []
        _result = [getattr(x, field, getattr(x, "{}s".format(field), None)) for x in result]
        _result: List[InnerDoc] = [x for x in _result if x]
        included_ids = []
        for item in _result:
            if hasattr(item, "id"):
                included_ids.append(item.id)
            else:
                included_ids.extend([x.id for x in item])
        return included_ids

    def _get_include_params(self, field):
        return {"api_version": getattr(self.request, "api_version", None)}

    def _get_included(self, result, *args, **kwargs):
        include = self.request.get_param("include")
        include = include.split(",") if include else []
        included = []
        include = [(self._include_map.get(x, x), self._includes.get(x)) for x in include if x in self._includes]
        for field, model_name in include:
            params = self._get_include_params(field)
            ids = self._get_included_ids(result, field)
            if ids:
                included += apps.get_model(model_name).get_included(ids, **params)
        return included


class SearchHdlr(IncludeMixin, BaseHdlr):

    def _queryset_extra(self, queryset, *args, **kwargs):
        return queryset

    @property
    def _search_document(self):
        return self.search_document.search()

    def _get_queryset(self, cleaned, *args, **kwargs):
        queryset = self.deserializer.get_queryset(self._search_document, cleaned)
        queryset = self._queryset_extra(queryset, *args, **kwargs)
        page, per_page = cleaned.get("page", 1), cleaned.get("per_page", 20)
        start = (page - 1) * per_page
        return queryset.extra(from_=start, size=per_page)

    def _get_debug_query(self, cleaned, *args, **kwargs):
        qs = self._get_queryset(cleaned, *args, **kwargs)
        return qs.to_dict()

    def _get_data(self, cleaned, *args, **kwargs):
        queryset = self._get_queryset(cleaned, *args, **kwargs)
        try:
            result = queryset.execute()
            return result
        except TransportError as err:
            raise falcon.HTTPBadRequest(description=err.info["error"]["reason"])


class RetrieveManyHdlr(BaseHdlr):
    def _get_data(self, cleaned, *args, **kwargs):
        return self._get_queryset(cleaned, *args, **kwargs)

    def _get_queryset(self, cleaned, *args, **kwargs):
        return self.database_model.objects.all()

    def _get_debug_query(self, cleaned, *args, **kwargs):
        queryset = self._get_queryset(cleaned, *args, **kwargs)
        return queryset.query


class RetrieveOneHdlr(IncludeMixin, BaseHdlr):

    def _get_instance(self, id, *args, **kwargs):
        instance = getattr(self, "_cached_instance", None)
        if not instance:
            model = self.database_model
            try:
                self._cached_instance = model.objects.get(pk=id, status=model.STATUS.published)
            except model.DoesNotExist:
                raise falcon.HTTPNotFound
        return self._cached_instance

    def clean(self, id, *args, **kwargs):
        self._get_instance(id, *args, **kwargs)
        return {}

    def _get_data(self, cleaned, id, *args, **kwargs):
        return self._get_instance(id, *args, **kwargs)


class CreateOneHdlr(BaseHdlr):
    def clean(self, *args, **kwargs):
        return super().clean(*args, locations=("headers", "json"), **kwargs)

    def _get_data(self, cleaned, *args, **kwargs):
        model = self.database_model
        data = cleaned["data"]["attributes"]
        self.response.context.data = model.objects.create(**data)


class UpdateManyHdlr(BaseHdlr):
    def clean(self, *args, **kwargs):
        return super().clean(*args, locations=("headers", "json"), **kwargs)

    def _async_run(self, cleaned, *args, **kwargs):
        raise NotImplementedError

    def run(self, *args, **kwargs):
        cleaned = self.clean(*args, **kwargs)
        self._async_run(cleaned, *args, **kwargs)
        return {}


class UpdateOneHdlr(BaseHdlr):
    def clean(self, id, *args, **kwargs):
        def validate_id(data):
            if data["data"]["id"] != str(id):
                raise ValidationError({"data": {"id": ["Invalid value"]}})
            data["data"].pop("id")
            return True

        validators = kwargs.pop(
            "validators",
            [
                validate_id,
            ],
        )
        return super().clean(*args, locations=("headers", "json"), validators=validators, **kwargs)

    def _get_data(self, cleaned, id, *args, **kwargs):
        data = cleaned["data"]["attributes"]
        model = self.database_model
        try:
            instance = model.objects.get(pk=id)
        except model.DoesNotExist:
            raise falcon.HTTPNotFound

        for key, val in data:
            setattr(instance, key, val)
        instance.save(update_fields=list(data.keys()))
        instance.refresh_from_db()
        return instance


class RemoveOneHdlr(BaseHdlr):
    def clean(self, id, *args, **kwargs):
        model = self.database_model
        try:
            return model.objects.get(pk=id)
        except model.DoesNotExist:
            raise falcon.HTTPNotFound

    def run(self, id, *args, **kwargs):
        instance = self.clean(id, *args, **kwargs)
        instance.delete()
        return {}


class RemoveManyHdlr(BaseHdlr):
    def clean(self, *args, **kwargs):
        res = super().clean(*args, locations=("headers", "json"), **kwargs)
        return res

    def _async_run(self, cleaned, *args, **kwargs):
        raise NotImplementedError

    def run(self, *args, **kwargs):
        cleaned = self.clean(*args, **kwargs)
        self._async_run(cleaned, *args, **kwargs)
        return {}


class SubscriptionSearchHdlr(SearchHdlr):
    def _queryset_extra(self, queryset, **kwargs):
        usr = self.request.user if hasattr(self.request, "user") and self.request.user.is_authenticated else None
        queryset = queryset.source(exclude=["subscription*"])
        if usr:
            queryset = queryset.filter(
                Q(
                    "bool",
                    should=[
                        Q(
                            "nested",
                            path="subscriptions",
                            query=Q("match", **{"subscriptions.user_id": usr.id}),
                            inner_hits={},
                        ),
                        Q("match_all"),
                    ],
                )
            )
        return queryset.filter("term", status="published")


class ShaclMixin:
    def clean(self, *args, **kwargs):
        if "shacl" in self.request.params:
            if self.request.params["shacl"] not in settings.SHACL_SHAPES:
                raise falcon.HTTPBadRequest(
                    description="Invalid shape to validation, accepted values: {allowed_shapes}".format(
                        allowed_shapes=", ".join(settings.SHACL_SHAPES)
                    )
                )

            unsupported_mimetypes = settings.SHACL_UNSUPPORTED_MIMETYPES
            found_unsupported_mimetypes = [mimetype for mimetype in unsupported_mimetypes if mimetype in self.request.accept]
            rdf_format = kwargs.get("rdf_format")
            is_unsupported_response_format = settings.RDF_FORMAT_TO_MIMETYPE.get(rdf_format) in unsupported_mimetypes
            if is_unsupported_response_format or (rdf_format is None and found_unsupported_mimetypes):
                unsupported_type = rdf_format or ", ".join(found_unsupported_mimetypes)
                raise falcon.HTTPBadRequest(title="%s serialization only makes sense for context-aware stores" % unsupported_type)
        return super().clean(*args, **kwargs)

    def use_rdf_db(self):
        return self.request.params.get("use_rdf_db", str(settings.USE_RDF_DB)).lower() in ["1", "true", "yes"]

    @staticmethod
    def get_sparql_store():
        return get_sparql_store()
