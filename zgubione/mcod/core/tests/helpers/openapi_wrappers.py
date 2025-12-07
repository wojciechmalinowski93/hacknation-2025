from falcon.testing import simulate_request
from openapi_core.wrappers.base import BaseOpenAPIRequest, BaseOpenAPIResponse

from mcod import settings


class FalconOpenAPIWrapper(BaseOpenAPIResponse, BaseOpenAPIRequest):
    def __init__(
        self,
        app,
        method="GET",
        path="/",
        path_pattern=None,
        path_params=None,
        headers=None,
        body=None,
        json=None,
        file_wrapper=None,
        wsgierrors=None,
        query=None,
        params_csv=True,
        protocol="http",
    ):
        self.request = simulate_request(
            app,
            method=method,
            path=path,
            query_string=None,
            headers=headers,
            body=body,
            json=json,
            file_wrapper=file_wrapper,
            wsgierrors=wsgierrors,
            params=query,
            params_csv=params_csv,
            protocol=protocol,
        )
        self.path = path
        self.method = method.lower()
        self.host_url = settings.BASE_URL
        self.path_pattern = path_pattern or path
        self.body = self.request.json
        self.data = self.request.json
        self.status_code = self.request.status_code
        self._query = query or {}
        self._params = path_params or {}
        self.mimetype = self.request.headers["content-type"]

    @property
    def parameters(self):
        return {
            "path": self._params,
            "query": self._query,
            "header": self.request.headers,
            "cookie": self.request.cookies,
        }
