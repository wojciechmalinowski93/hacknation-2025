import json
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from pydiscourse.exceptions import DiscourseClientError

from mcod.discourse.client import DiscourseClient, DiscourseClientPasswordAuth

logger = logging.getLogger("mcod")


class DiscourseManager:

    def __init__(
        self,
        host=settings.DISCOURSE_HOST,
        sync_host=settings.DISCOURSE_SYNC_HOST,
        api_key=settings.DISCOURSE_API_KEY,
        api_user=settings.DISCOURSE_API_USER,
    ):
        self.host = host
        self.sync_host = sync_host
        self.api_user = api_user
        self.api_key = api_key
        self.api_client = self._get_api_client(host, api_user, api_key)

    def _get_api_client(self, host, api_user, api_key):
        return DiscourseClient(host, api_user, api_key)

    def create_admin_api_key(self, **kwargs):
        logger.debug("Creating api key for system user")
        if not (kwargs.get("password") and kwargs.get("username")):
            logger.debug("No login credentials supplied, skipping key creation.")
            return
        client = DiscourseClientPasswordAuth(self.host, username=kwargs["username"], password=kwargs["password"])
        client.login()
        api_keys = client.list_api_keys()
        for key in api_keys["keys"]:
            if key["user"]["username"] == self.api_user and key["revoked_at"] is None:
                logger.debug(
                    f"Api key for user {self.api_user} already exists, skipping creation" f" and reading from env variable."
                )
                return
        api_key_details = client.create_api_key(self.api_user)
        key = api_key_details["key"]["key"]
        api_key_fpath = os.path.join(settings.APPS_DIR, "api_key.txt")
        with open(api_key_fpath, "w") as outfile:
            outfile.write(key)
            logger.debug(f"Api key saved to {api_key_fpath}. Copy it to DISCOURSE_API_KEY environmental variable.")
            self.api_key = key
            self.api_client = self._get_api_client(self.host, self.api_user, key)

    def setup_settings(self, **kwargs):
        logger.info("Setting up forum settings.")
        current_site_settings = self.get_current_site_settings()
        new_settings = {}
        for key, value in self.get_settings_to_update(**kwargs):
            value_old = current_site_settings.get(key)
            if value == value_old:
                if kwargs["show_all"]:
                    logger.info(f"[==] {key}: {value_old} == {value}")
            else:
                logger.info(f"[!=] {key}: {value_old} != {value}")
                new_settings[key] = value
                logger.info(f"{key} will be updated")
        if new_settings:
            try:
                self.api_client.site_settings(**new_settings)
                logger.info("Settings updated.")
            except DiscourseClientError as e:
                logger.error(f"{e}")
        else:
            logger.debug("No new settings supplied! Skipping settings setup.")

    def get_current_site_settings(self):
        result = self.api_client.get_site_settings()
        return {item["setting"]: item["value"] for item in result["site_settings"]} if "site_settings" in result else {}

    def get_settings_to_update(self, **kwargs):
        if kwargs["file"] is not None:
            env_settings = [
                {
                    "setting": "discourse_connect_url",
                    "value": settings.DISCOURSE_CONNECT_URL,
                },
                {
                    "setting": "discourse_connect_secret",
                    "value": settings.DISCOURSE_SSO_SECRET,
                },
                {
                    "setting": "logout_redirect",
                    "value": settings.DISCOURSE_LOGOUT_REDIRECT,
                },
            ]
            site_settings = self.read_file(kwargs["file"])
            site_settings = env_settings + site_settings
            for item in site_settings:
                yield item["setting"], item["value"]
        if kwargs["keyval"]:
            for item in kwargs["keyval"]:
                key, val = item.split("=", 1)
                yield key.strip(), val.strip()

    def read_file(self, file):
        result = json.load(file)
        return result["site_settings"] if "site_settings" in result else result

    def sync_users(self, **kwargs):
        logger.debug("Attempting to synchronize mcod and forum users.")
        api_client = self._get_api_client(self.sync_host, self.api_user, self.api_key)
        sso_secret = settings.DISCOURSE_SSO_SECRET
        users_to_sync = (
            get_user_model()
            .objects.filter(is_active=True, state="active")
            .filter(Q(is_superuser=True) | Q(is_agent=True) | Q(extra_agent_of__isnull=False))
        )
        logger.debug(f"Found {users_to_sync.count()} users to synchronize")
        for user in users_to_sync:
            logger.debug(f"Synchronized user {user.email}, api_key {user.discourse_api_key}")
            username = user.email.split("@")[0]
            user_details = {
                "sso_secret": sso_secret,
                "external_id": user.pk,
                "email": user.email,
                "username": username,
                "name": user.fullname if user.fullname else username,
                "admin": True if user.is_superuser else False,
                "moderator": True if user.is_superuser else False,
            }
            response = api_client.sync_sso(**user_details)
            if response:
                username = response["username"]
                response = api_client.create_api_key(username)
                if "key" in response:
                    user.discourse_user_name = username
                    user.discourse_api_key = response["key"]["key"]
                    user.save()
            else:
                logger.debug(f"Skipping {user.email}, no response from discourse.")
        logger.debug("User synchronization completed.")

    def setup_default_theme(self, **kwargs):
        theme_path = kwargs.get("theme_path")
        if theme_path:
            logger.debug(f"Uploading {theme_path} and setting up as default theme.")
            resp = self.api_client.upload_theme(theme_path)
            if resp and resp.get("theme"):
                self.api_client.set_default_theme(resp["theme"]["id"])
                logger.debug("Default theme setup completed.")
        else:
            logger.debug("No path to theme supplied, skipping theme setup.")
