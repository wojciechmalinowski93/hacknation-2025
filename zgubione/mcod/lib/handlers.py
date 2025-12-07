from falcon.util import to_query_str

from mcod.core.api.parsers import Parser
from mcod.watchers.models import Subscription


class BaseHandler:
    def __init__(self, request, response):
        self.request = request
        self.response = response

    def run(self, *args, **kwargs):
        request = self.request
        cleaned = self._clean(request, *args, **kwargs)
        explain = cleaned.get("explain", None) if isinstance(cleaned, dict) else None
        data = self._data(request, cleaned, *args, explain=explain, **kwargs)
        if explain == "1":
            return data
        meta = self._metadata(request, data, *args, **kwargs)
        links = self._links(request, data, *args, **kwargs)
        return self._serialize(data, meta, links, *args, **kwargs)

    def _clean(self, request, *args, locations=None, **kwargs):
        locations = locations or ("headers", "query")
        return Parser(locations=locations).parse(self.deserializer_schema, req=request)

    def _data(self, request, cleaned, *args, **kwargs):
        return cleaned

    def _metadata(self, request, data, *args, **kwargs):
        ms = getattr(self, "meta_serializer", None)
        meta = ms.dump(data) if ms else {}
        usr = getattr(request, "user", None)
        if usr and usr.is_authenticated:
            try:
                subscription = Subscription.objects.get_from_data(
                    usr,
                    {"object_name": "query", "object_ident": request.url},
                    headers=request.headers,
                )
                meta["subscription_url"] = subscription.api_url
            except Subscription.DoesNotExist:
                pass

        meta.update(
            {
                "language": request.language,
                "params": request.params,
                "path": request.path,
                "rel_uri": request.relative_uri,
            }
        )

        return meta

    @staticmethod
    def _link(path, params):
        return "{}{}".format(path, to_query_str(params))

    def _links(self, request, data, *args, **kwargs):
        return {"self": self._link(request.path, request.params)}

    def _serialize(self, data, meta, links=None, *args, **kwargs):
        res = self.serializer_schema.dump(data, meta, links)
        return res
