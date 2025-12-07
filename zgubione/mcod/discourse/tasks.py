import logging
from typing import Any, Dict, Optional, TypedDict

from django.conf import settings
from pydiscourse.exceptions import DiscourseClientError
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.discourse.client import DiscourseClient
from mcod.users.models import User

logger = logging.getLogger("mcod")


def get_user_by_id(user_id: int) -> User:
    """Retrieves a user object by ID, raising an error if not found."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        raise
    return user


def get_discourse_client():
    """Returns a configured Discourse client."""
    return DiscourseClient(
        settings.DISCOURSE_SYNC_HOST,
        settings.DISCOURSE_API_USER,
        settings.DISCOURSE_API_KEY,
    )


class UserDetails(TypedDict):
    sso_secret: str
    external_id: Any
    email: str
    username: str
    name: str
    admin: bool
    moderator: bool


def add_access_to_discourse(user: User, discourse_client: DiscourseClient):
    """Synchronizes a user with Discourse and grants them access."""
    logger.debug(
        f"User ({user.email}, {user.id}) is eligible for forum access in the OD application context, "
        f"but may not yet have an account in Discourse."
    )
    username: str = user.email.split("@")[0]
    user_details: UserDetails = {
        "sso_secret": settings.DISCOURSE_SSO_SECRET,
        "external_id": user.id,
        "email": user.email,
        "username": username,
        "name": user.fullname if user.fullname else username,
        "admin": user.is_superuser,
        "moderator": user.is_superuser,
    }
    forum_user: Optional[Dict[str, Any]] = discourse_client.sync_sso(**user_details)
    logger.debug(
        f"Successfully synchronized user ({user.email}, {user.id}) with Discourse database. "
        f"Account created or updated as needed."
    )
    if not user.has_access_to_forum and forum_user:
        logger.debug(
            f"New Discourse user ({user.email}, {user.id}) detected. "
            f"Missing local 'discourse_user_name' and 'discourse_api_key' values. Proceeding to generate API key."
        )
        forum_username: str = forum_user["username"]
        response: Dict[str, Any] = discourse_client.create_api_key(forum_username)
        logger.debug(f"Creating API key for user ({user.email}, {user.id}).")
        if "key" in response:
            user.discourse_user_name = forum_username
            user.discourse_api_key = response["key"]["key"]
            user.save()
            logger.debug("API key and username successfully stored in database.")
            if not forum_user["active"]:
                discourse_client.activate(forum_user["id"])
                logger.debug(f"Discourse account ({forum_username}, {user.id}) activated.")


def remove_access_from_discourse(user, discourse_client):
    """Logs out and deactivates a user in Discourse."""
    try:
        forum_user: Dict[str, Any] = discourse_client.by_external_id(user.id)
        _user_id: int = forum_user["id"]
        if forum_user:
            discourse_client.log_out(_user_id)
            discourse_client.deactivate(_user_id)
            logger.debug(
                f"User ({user.email}, {user.id}) does not have minimum forum access. "
                f"Account has been logged out and deactivated."
            )
    except DiscourseClientError as e:
        logger.error(
            f"User ({user.email}, {user.id}) not found in Discourse database. "
            f"No logout or deactivation required. "
            f"DiscourseClientError: {e}"
        )


@extended_shared_task
def user_sync_task(user_id: int) -> Dict[str, str]:
    """
    Celery asynchronous task for user account synchronization with the Discourse forum.

    This task manages granting and revoking forum access by synchronizing user data
    from the Open Data database to Discourse. The synchronization process is triggered
    under specific conditions:
    1. **User Account Management**: Initiated by administrative actions (creation or
       editing of a user account) exclusively from the Django Admin Panel to prevent
       unnecessary API calls.
    2. **User Logout**: Triggered by the `user_logged_out` Django signal, ensuring
       the user's session is properly terminated in Discourse upon logout.

    The task performs the following operations based on the user's status:
    - If a user is eligible for forum access (e.g., active, not removed, with
      appropriate permissions), it creates or updates their Discourse account via
      SSO synchronization and generates a dedicated API key for further
      interactions.
    - If a user is no longer eligible (e.g., inactive, removed), it deactivates
      their Discourse account and logs them out.
    """
    set_tag("user_id", str(user_id))
    user: User = get_user_by_id(user_id)
    discourse_client: DiscourseClient = get_discourse_client()
    can_access_forum: bool = user.is_active and (user.is_superuser or user.agent) and not user.is_removed

    if can_access_forum:
        add_access_to_discourse(user, discourse_client)
    else:
        remove_access_from_discourse(user, discourse_client)

    return {"result": "ok"}


@extended_shared_task
def user_logout_task(user_id: int) -> Dict[str, str]:
    user: User = get_user_by_id(user_id)
    discourse_client: DiscourseClient = get_discourse_client()

    if not (getattr(user, "discourse_user_name", None) and getattr(user, "discourse_api_key", None)):
        logger.debug(f"User {user_id} does not have Discourse data - skipping logout.")
        return {"result": "ok, but skipping logout, no discourse credentials"}

    try:
        forum_user: Dict[str, Any] = discourse_client.by_external_id(user_id)
        if forum_user:
            discourse_client.log_out(forum_user["id"])
            logger.debug(f"Logout successful for user {user_id}")
        else:
            logger.debug(f"User {user_id} not found in Discourse - no logout needed.")
    except DiscourseClientError as e:
        logger.error(f"Logout skipped for user {user_id}. DiscourseClientError: {e}")

    return {"result": "ok"}
