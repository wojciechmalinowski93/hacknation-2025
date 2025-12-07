import os
import time

import magic
import requests
from pydiscourse import DiscourseClient as BaseDiscourseClient
from pydiscourse.client import POST, log
from pydiscourse.exceptions import (
    DiscourseClientError,
    DiscourseError,
    DiscourseRateLimitedError,
    DiscourseServerError,
)

from mcod import settings


class DiscourseClient(BaseDiscourseClient):
    def list_api_keys(self):
        return self._get("/admin/api/keys")

    def create_api_key(self, username, scopes=None):
        kwargs = {
            "key": {
                "username": username,
                "description": f"Access key for user {username}",
            },
        }
        return self._post("/admin/api/keys", json=True, **kwargs)

    def upload_theme(self, theme_path):
        with open(theme_path, "rb") as f:
            mime = magic.Magic(mime=True)
            files = {"theme": (os.path.basename(theme_path), f, mime.from_file(theme_path))}
            return self._post("/admin/themes/import", files=files)

    def set_default_theme(self, theme_id):
        return self._put("/admin/themes/{0}".format(theme_id), json=True, theme={"default": True})

    def revoke_api_key(self, keyid):
        return self._post("/admin/api/keys/{0}/revoke".format(keyid))

    def undo_revoke_api_key(self, keyid):
        return self._post("/admin/api/keys/{0}/undo-revoke".format(keyid))

    def delete_api_key(self, keyid):
        return self._delete("/admin/api/keys/{0}".format(keyid))

    def get_site_settings(self, **kwargs):
        return self._get("/admin/site_settings")


def get_client():
    return DiscourseClient(
        settings.DISCOURSE_HOST,
        api_username=settings.DISCOURSE_API_USER,
        api_key=settings.DISCOURSE_API_KEY,
    )


class DiscourseClientPasswordAuth(DiscourseClient):

    def __init__(self, host, username, password, timeout=None):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()

    def _request(  # noqa: C901
        self,
        verb,
        path,
        params=None,
        files=None,
        data=None,
        json=None,
        override_request_kwargs=None,
    ):
        """
        Executes HTTP request to API and handles response

        Args:
            verb: HTTP verb as string: GET, DELETE, PUT, POST
            path: the path on the Discourse API
            params: dictionary of parameters to include to the API
            override_request_kwargs: dictionary of requests.request keyword arguments to override defaults

        Returns:
            dictionary of response body data or None

        """
        override_request_kwargs = override_request_kwargs or {}

        url = self.host + path

        headers = {
            "Accept": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": self.get_csrf() if verb == POST else "",
        }

        # How many times should we retry if rate limited
        retry_count = 4
        # Extra time (on top of that required by API) to wait on a retry.
        retry_backoff = 1

        while retry_count > 0:
            request_kwargs = dict(
                allow_redirects=False,
                params=params,
                files=files,
                data=data,
                json=json,
                headers=headers,
                timeout=self.timeout,
            )
            request_kwargs.update(override_request_kwargs)

            response = self.session.request(verb, url, **request_kwargs)

            log.debug("response %s: %s", response.status_code, repr(response.text))
            if response.ok:
                break
            if not response.ok:
                try:
                    msg = ",".join(response.json()["errors"])
                except (ValueError, TypeError, KeyError):
                    if response.reason:
                        msg = response.reason
                    else:
                        msg = "{0}: {1}".format(response.status_code, response.text)

                if 400 <= response.status_code < 500:
                    if 429 == response.status_code:
                        # This codepath relies on wait_seconds from Discourse v2.0.0.beta3 / v1.9.3 or higher.
                        rj = response.json()
                        wait_delay = retry_backoff + rj["extras"]["wait_seconds"]  # how long to back off for.

                        if retry_count > 1:
                            time.sleep(wait_delay)
                        retry_count -= 1
                        log.info(
                            "We have been rate limited and waited {0} seconds ({1} retries left)".format(wait_delay, retry_count)
                        )
                        log.debug("API returned {0}".format(rj))
                        continue
                    else:
                        raise DiscourseClientError(msg, response=response)

                # Any other response.ok resulting in False
                raise DiscourseServerError(msg, response=response)

        if retry_count == 0:
            raise DiscourseRateLimitedError(
                "Number of rate limit retries exceeded. Increase retry_backoff or retry_count",
                response=response,
            )

        if response.status_code == 302:
            raise DiscourseError("Unexpected Redirect, invalid api key or host?", response=response)

        json_content = "application/json; charset=utf-8"
        content_type = response.headers["content-type"]
        if content_type != json_content:
            # some calls return empty html documents
            if not response.content.strip():
                return None

            raise DiscourseError(
                'Invalid Response, expecting "{0}" got "{1}"'.format(json_content, content_type),
                response=response,
            )

        try:
            decoded = response.json()
        except ValueError:
            raise DiscourseError("failed to decode response", response=response)

        if "errors" in decoded:
            message = decoded.get("message")
            if not message:
                message = ",".join(decoded["errors"])
            raise DiscourseError(message, response=response)

        return decoded

    def get_csrf(self):
        res = self._get("/session/csrf")
        return res["csrf"]

    def login(self):
        data = {"login": self.username, "password": self.password}
        return self._post("/session", **data)
