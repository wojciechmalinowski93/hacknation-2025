from typing import List, Optional, Tuple, Union

from django.test import Client
from falcon.testing import TestClient
from requests import Response
from rest_framework.test import APIClient


class MethodsNotAllowedTestMixin:
    """Test mixin for not allowed methods."""

    client: Optional[Union[Client, APIClient, TestClient]] = None
    url: str = ""
    NOT_ALLOWED_METHODS: Union[List[str], Tuple[str]] = []
    headers: dict = {}

    def test_request_methods_not_allowed(self):
        for method in self.NOT_ALLOWED_METHODS:
            getattr(self, f"{method.lower()}_not_allowed")()

    def get_not_allowed(self):
        res: Response = self.client.get(self.url, **self.headers)  # noqa
        assert res.status_code == 405, f"Actual response status code is: {res.status_code}, method: GET"

    def post_not_allowed(self):
        res: Response = self.client.post(self.url, **self.headers)  # noqa
        assert res.status_code == 405, f"Actual response status code is: {res.status_code}, method: POST"

    def put_not_allowed(self):
        res: Response = self.client.put(self.url, **self.headers)  # noqa
        assert res.status_code == 405, f"Actual response status code is: {res.status_code}, method: PUT"

    def patch_not_allowed(self):
        res: Response = self.client.patch(self.url, **self.headers)  # noqa
        assert res.status_code == 405, f"Actual response status code is: {res.status_code}, method: patch"

    def delete_not_allowed(self):
        res: Response = self.client.delete(self.url, **self.headers)  # noqa
        assert res.status_code == 405, f"Actual response status code is: {res.status_code}, method: delete"
