import logging
import re
from dataclasses import dataclass
from typing import Optional, Tuple
from uuid import uuid4
from xml.etree.ElementTree import fromstring

from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.cache import KEY_PREFIX
from django.core.cache import caches
from django.urls import reverse
#from logingovpl.mixins import ACSMixin, LogoutMixin
class ACSMixin:
    pass

class LogoutMixin:
    pass
#from logingovpl.objects import LoginGovPlUser
class LoginGovPlUser:
    pass
#from logingovpl.services import decode_cipher_value
#from logingovpl.statuses import SUCCESS
#from logingovpl.utils import get_in_response_to, get_name_id, get_session_id, get_user, xml_ns
# --- ATRAPY DLA HACKATHONU ---

class LoginGovPlService:
    def get_redirect_url(self, *args, **kwargs):
        return "/"

    def check_token(self, *args, **kwargs):
        return None

logingovpl_service = LoginGovPlService()
from mcod import settings
from mcod.lib.triggers import session_store
from mcod.users.constants import (
    EMAIL_REGEX,
    LOGINGOVPL_PROCESS,
    LOGINGOVPL_PROCESS_RESULT,
    LOGINGOVPL_REQUEST_ID_SEPARATOR,
    LOGINGOVPL_UNKNOWN_USER_IDENTIFIER,
    PORTAL_TYPE,
)
from mcod.users.exceptions import SAMLArtException

User = get_user_model()
logger = logging.getLogger("mcod")


@dataclass
class LoginGovPlData:
    """Class representing data obtained from the login.gov.pl service."""

    user: LoginGovPlUser  # login.gov.pl user data
    name_id: str  # login.gov.pl user login
    in_response_to: str  # authn_request_id prepared and sent from the backend
    session_id: str  # login.gov.pl session identifier


class UserService:
    model = User

    def _is_user_active(self, user: User) -> bool:
        """Check if the given user is not deleted and has an active state."""
        return user.is_active is True and user.state == "active"

    def get_active_session_user_or_none(self, user_id: Optional[int], portal: PORTAL_TYPE) -> Optional[User]:
        """Search sessions for active user with the given `user_id`. For admin panel
        (`PORTAL_TYPE.ADMIN`) check additionally if the found user has an access to
        the admin panel.

        If the user cannot be found, then return `None`.
        """
        if isinstance(user_id, int):
            session_caches = caches[settings.SESSION_CACHE_ALIAS]
            for session_cache in session_caches.keys("*"):
                session_key = session_cache[len(KEY_PREFIX) :]
                session_items = list(session_store(session_key).items())
                if session_items:
                    session_user_id = session_items[0][1]
                    if session_user_id == str(user_id):
                        user = self.model.objects.get(pk=user_id)
                        if self._is_user_active(user):
                            if portal == PORTAL_TYPE.ADMIN:
                                return user if user.has_access_to_admin_panel else None
                            return user
        logger.warning(f"Not found active session user for id `{user_id}` and portal `{portal}`.")
        return None

    def get_last_user_by_pesel_or_none(self, pesel: str, portal: PORTAL_TYPE) -> Optional[User]:
        """Get the last created active user (not blocked or permanently blocked) by
        the given PESEL number. For admin panel (`PORTAL_TYPE.ADMIN`) check additionally
        if the found user has access to the admin panel.

        If the user cannot be found, then return `None`.
        """
        users = list(
            self.model.objects.filter(
                pesel=pesel,
                state="active",
                is_active=True,
                is_removed=False,
                is_permanently_removed=False,
            ).order_by("created")
        )
        if portal == PORTAL_TYPE.ADMIN:
            users = [user for user in users if user.has_access_to_admin_panel]

        if not users:
            logger.warning(f"Not found last user for PESEL `{pesel}` and portal `{portal}`.")
            return None
        return users[-1]

    @staticmethod
    def login_by_logingovpl(request, user: User) -> None:
        """Log-in user by the login.gov.pl service."""
        if not hasattr(request, "session"):
            request.session = session_store()
            request.META = {}
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.save()
        user.is_gov_auth = True
        user.save()
        logger.info(f"The user `{user}` has been logged-in by login.gov.pl.")

    @staticmethod
    def link_to_logingovpl(user: User, pesel: str) -> None:
        """Update user fields due to the process of linking to the login.gov.pl service.
        User linked by login.gov.pl is treated as logged-in by the login.gov.pl service.
        """
        user.pesel = pesel
        user._pesel = pesel
        user.is_gov_auth = True
        user.save()
        logger.info(f"Updated PESEL for user `{user.email}`.")

    @staticmethod
    def unlink_from_logingovpl(user: User) -> None:
        """Remove PESEL from the user due to the process of unlinking from the login.gov.pl service.
        User unlinked from login.gov.pl is treated as logged-out by the login.gov.pl service.
        """
        user.pesel = None
        user.is_gov_auth = False
        user.save()
        logger.info(f"PESEL from user `{user}` has been removed.")

    @staticmethod
    def get_user_to_switch_or_none(actual_user: User, email_to_switch: str) -> Optional[User]:
        """Get user object with the given `email_to_switch`, connected with the given `actual_user.`

        If new user cannot be found, then return `None`.
        """
        new_user = [obj for obj in actual_user.connected_gov_users if obj.email == email_to_switch]
        if not new_user:
            logger.warning(f"Not found email to switch `{email_to_switch}` for user `{User}`.")
            return None
        return new_user[0]


class LoginGovPlService(ACSMixin, LogoutMixin):
    """Logingovpl service."""

    email_pattern = re.compile(EMAIL_REGEX)

    @staticmethod
    def _get_status_code_from_saml(content: str) -> Tuple[str, str]:
        """Parse SAML content and get status code and message from it."""
        tree = fromstring(content)
        try:
            elem_status_code = tree.find(".//saml2p:ArtifactResponse/saml2p:Status/saml2p:StatusCode", xml_ns)
            status_code = elem_status_code.attrib.get("Value")
        except AttributeError:
            elem_status_code = tree.find(".//saml2p:Status/saml2p:StatusCode", xml_ns)
            status_code = elem_status_code.attrib.get("Value")

        elem_status_message = tree.find(".//saml2p:Status/saml2p:StatusMessage", xml_ns)
        status_message = elem_status_message.text if elem_status_message is not None else None
        return status_code, status_message

    def prepare_authn_request_id(self, user_id: Optional[int], is_admin_panel: bool) -> str:
        """Prepare the authorization request identifier to the login.gov.pl service, needed later to process
        the answer from the login.gov.pl service.

        If the frontend requests with the user set in session and apiauthtoken cookies (`user_id` is not `None`),
        we assume that it is a process of a linking to the login.gov.pl service from the logged user account.
        Otherwise, it is the logging process. The parameter `is_admin_panel` helps to distinct if the logging/linking
        process started from the admin panel or from the main portal.

        Example of the identifier: "ID-971bc12f-972d-4648-995d-3254b12ddd47-MAIN-LINK-50765"
        """
        portal_type = PORTAL_TYPE.ADMIN.value if is_admin_panel else PORTAL_TYPE.MAIN.value
        logingovpl_process = LOGINGOVPL_PROCESS.LOGIN.value if user_id is None else LOGINGOVPL_PROCESS.LINK.value
        user_identifier = LOGINGOVPL_UNKNOWN_USER_IDENTIFIER if user_id is None else str(user_id)

        return (
            "ID"
            + LOGINGOVPL_REQUEST_ID_SEPARATOR
            + str(uuid4())
            + LOGINGOVPL_REQUEST_ID_SEPARATOR
            + portal_type
            + LOGINGOVPL_REQUEST_ID_SEPARATOR
            + logingovpl_process
            + LOGINGOVPL_REQUEST_ID_SEPARATOR
            + user_identifier
        )

    @staticmethod
    def get_user_id_or_none_from_authn_request_id(
        authn_request_id: str,
    ) -> Optional[int]:
        """Get the user ID from the `InResponseTo` field of the SAML artifact response,
        which is previously prepared during preparing SAML artifact to the login.gov.pl service.

        If user ID was not found, than return `None`.
        """
        user_id_text = authn_request_id.split(LOGINGOVPL_REQUEST_ID_SEPARATOR)[-1]
        if user_id_text == LOGINGOVPL_UNKNOWN_USER_IDENTIFIER:
            return None

        try:
            return int(user_id_text)
        except ValueError:
            logger.error(f"Wrong User ID found in authn_request_id `{authn_request_id}`.")
            return None

    @staticmethod
    def get_process_or_none_from_authn_request_id(
        authn_request_id: str,
    ) -> Optional[LOGINGOVPL_PROCESS]:
        """Get the logingovpl process type from the `InResponseTo` field of the SAML artifact
        response (LOGIN/LINK), which is previously prepared during preparing SAML artifact to
        the login.gov.pl service.

        If found process text not exists in the `LOGINGOVPL_PROCESS` constant, return `None`.
        """
        process_text = authn_request_id.split(LOGINGOVPL_REQUEST_ID_SEPARATOR)[-2]
        try:
            process = LOGINGOVPL_PROCESS(process_text)
        except ValueError:
            logger.error(f"Logingovpl process not found in authn_request_id `{authn_request_id}`.")
            return None
        return process

    @staticmethod
    def get_portal_or_none_from_authn_request_id(
        authn_request_id: str,
    ) -> Optional[PORTAL_TYPE]:
        """Get the portal type from the `InResponseTo` field of the SAML artifact response (MAIN/ADMIN),
        which is previously prepared during preparing SAML artifact to the login.gov.pl service.

        If found portal text not exists in the `PORTAL_TYPE` constant, then return `None`.
        """

        portal_text = authn_request_id.split(LOGINGOVPL_REQUEST_ID_SEPARATOR)[-3]
        try:
            portal = PORTAL_TYPE(portal_text)
        except ValueError:
            logger.error(f"Portal type not found in authn_request_id `{authn_request_id}`.")
            return None
        return portal

    def get_saml_assertion_status(self, content: str) -> Tuple[str, str]:
        """SAML assertion method. Gets status code and message from logingovpl response."""
        status_code: str
        message: str
        status_code, message = self._get_status_code_from_saml(content)

        return status_code, message

    @staticmethod
    def get_data_from_saml_art(saml_art: bytes) -> LoginGovPlData:
        """Get decoded data from the SAML Artifact Response of the login.gov.pl serviece."""
        decoded_content = decode_cipher_value(saml_art)

        return LoginGovPlData(
            user=get_user(decoded_content),
            name_id=get_name_id(decoded_content),
            in_response_to=get_in_response_to(decoded_content),
            session_id=get_session_id(decoded_content),
        )

    def logout_session(self, session_id: str, name_id: str) -> None:
        self.login_gov_logout(session_id, name_id)

    def get_logingovpl_data_and_logout(self, request_data: dict, is_logingovpl_mocked: bool) -> LoginGovPlData:
        """Get data from the login.gov.pl POST request to the endpoint /idp,
        and logout from the login.gov.pl service.

        If `is_logingovpl_mocked` is `True`,
        then request data are from the template mocking the login.gov.pl service.

        Raises `SAMLArtException` in case of not obtaining user data from
        the ArtifactResolve response.
        """
        if is_logingovpl_mocked:

            return LoginGovPlData(
                user=LoginGovPlUser(
                    request_data["first_name"],
                    request_data["last_name"],
                    request_data["dob"],
                    request_data["pesel"],
                ),
                name_id=request_data["in_response_to"],
                in_response_to=request_data["in_response_to"],
                session_id="test_logingovpl_ID_session",
            )

        response = self.resolve_artifact(request_data["SAMLart"])
        status_code, message = self._get_status_code_from_saml(response.content)

        if status_code != SUCCESS:
            logger.error(f"SAML Artifact not resolved: `{status_code}` `{message}`")
            raise SAMLArtException(message)

        decoded_content = decode_cipher_value(response.content)
        logingovpl_user = get_user(decoded_content)
        name_id = get_name_id(decoded_content)
        in_response_to = get_in_response_to(decoded_content)
        session_id = get_session_id(decoded_content)

        self.logout_session(session_id, name_id)
        return LoginGovPlData(user=logingovpl_user, name_id=name_id, in_response_to=in_response_to, session_id=session_id)

    @staticmethod
    def get_redirect_url(portal: PORTAL_TYPE, process: LOGINGOVPL_PROCESS, process_result: LOGINGOVPL_PROCESS_RESULT) -> str:
        """Prepare and return a dedicated URL for the frontend or the admin panel needs."""

        redirect_urls = {
            # URLs for the main portal (frontend)
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.SUCCESS): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=login-success",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.ERROR): settings.FRONTEND_BASE_URL
            + "/user/logingovpl-error"
            + "?logingovpl=login-error",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LINK, LOGINGOVPL_PROCESS_RESULT.SUCCESS): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=link-success",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LINK, LOGINGOVPL_PROCESS_RESULT.ERROR): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=link-error",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.UNLINK, LOGINGOVPL_PROCESS_RESULT.SUCCESS): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=unlink-success",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.UNLINK, LOGINGOVPL_PROCESS_RESULT.ERROR): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=unlink-error",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.SUCCESS): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=switch-success",
            (PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR): settings.FRONTEND_BASE_URL
            + "/user/dashboard/desktop"
            + "?logingovpl=switch-error",
            # URLs for the admin panel
            (PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.SUCCESS): reverse("admin:index"),
            (PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.ERROR): reverse("admin:login")
            + "?logingovpl=login-error",
            (PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.SUCCESS): reverse("admin:index"),
            (PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR): reverse("admin:login")
            + "?logingovpl=switch-error",
            # URL for the unknown process/portal/result
            (PORTAL_TYPE.UNKNOWN, LOGINGOVPL_PROCESS.UNKNOWN, LOGINGOVPL_PROCESS_RESULT.UNKNOWN): settings.FRONTEND_BASE_URL
            + "/idp-unknown-error",
        }
        return redirect_urls[(portal, process, process_result)]

    @staticmethod
    def check_attr_portal(portal: Optional[str]) -> Optional[PORTAL_TYPE]:
        """Validate the URL attribute `portal` and return the value from the constant `PORTAL_TYPE`.

        If portal attribute not exists (is `None`), then return `None`,
        """
        if portal is None:
            return PORTAL_TYPE.MAIN
        if portal == "admin":
            return PORTAL_TYPE.ADMIN
        logger.warning(f"Wrong URL attribute portal in logingovpl process: {portal}.")

    def check_attr_email(self, email: Optional[str]) -> Optional[str]:
        """Validate the URL attribute `email` and return it if is ok.

        If email attribute not exists (is `None`) or is not valid, then return `None`,
        """
        if email is None:
            logger.warning("Not found URL attribute email in logingovpl process.")
            return
        if not self.email_pattern.match(email):
            logger.warning(f"Not valid URL attribute email `{email}` in logingovpl process.")
            return
        return email


logingovpl_service: LoginGovPlService = LoginGovPlService()
user_service: UserService = UserService()
