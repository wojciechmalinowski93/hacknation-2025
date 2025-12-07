import logging
import typing

from discourse_django_sso.utils import SSOProducerUtils, SSOProviderService
from django.conf import settings


class ForumProviderService(SSOProviderService):
    def get_signed_url(self, user: settings.AUTH_USER_MODEL, sso: str, signature: str, redirect_to: str) -> typing.Optional[str]:
        gen = ForumProducerUtils(
            sso_key=self.sso_key,
            consumer_url=redirect_to,
            user=user,
            sso=sso,
            sig=signature,
        )
        try:
            gen.validate()
        except ValueError:
            logging.exception("Invalid sso")
            return None
        if not gen.verify_signature():
            return None
        payload = gen.get_signed_payload()

        return gen.get_sso_redirect(payload)


class ForumProducerUtils(SSOProducerUtils):
    def get_response_params(self) -> typing.Sequence[typing.Tuple[str, str]]:
        username = self.user.email.split("@")[0]
        return (
            ("nonce", self.get_nonce()),
            ("email", self.user.email),
            ("username", username),
            ("external_id", self.user.id),
            ("name", self.user.fullname if self.user.fullname else username),
            ("admin", True if self.user.is_superuser else False),
            ("moderator", True if self.user.is_superuser else False),
        )
