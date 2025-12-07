import pytest
from django.test import Client

from mcod.core.caches import flush_sessions
from mcod.core.tests.fixtures import create_user_with_params
from mcod.users.constants import LOGINGOVPL_PROCESS, PORTAL_TYPE
from mcod.users.services import logingovpl_service, user_service


class TestLoginGovPlService:

    @property
    def _saml(self):
        """Return saml example content."""
        with open("mcod/users/tests/data/saml.xml", "r") as f:
            return f.read()

    def test__get_status_code_from_saml(self):
        """Test if _get_status_code_from_saml method returns variables with specified types."""
        res = logingovpl_service._get_status_code_from_saml(self._saml)
        assert isinstance(res, tuple)
        assert isinstance(res[0], str)
        assert isinstance(res[1], str)

    def test_saml_assertion(self, mocker):
        """Test if method saml_assertion returns variables with specified types."""

        class TestRequest:
            content = self._saml

        mocker.patch(
            "mcod.users.services.LoginGovPlService.resolve_artifact",
            return_value=TestRequest(),
        )
        test_response = TestRequest()
        res = logingovpl_service.get_saml_assertion_status(test_response.content)
        assert len(res) == 2

        status_code, message = res
        assert isinstance(status_code, str)
        assert isinstance(message, str)

    @pytest.mark.parametrize(
        "test_user_id, test_is_admin_panel, expected_data_in_request_id",
        [
            (None, False, "-MAIN-LOGIN-UNKNOWN"),  # logging from main portal
            (1234, False, "-MAIN-LINK-1234"),  # linking from main portal
            (None, True, "-ADMIN-LOGIN-UNKNOWN"),  # logging from admin panel
            (1234, True, "-ADMIN-LINK-1234"),  # linking from admin panel
        ],
    )
    def test_prepare_authn_request_id(self, test_user_id, test_is_admin_panel, expected_data_in_request_id):
        """Test all cases of preparing authorization identifier (for logging/linking process,
        for panel admin or main portal, with given user or not).
        """
        authn_request_id = logingovpl_service.prepare_authn_request_id(test_user_id, test_is_admin_panel)
        assert expected_data_in_request_id in authn_request_id

    @pytest.mark.parametrize(
        "test_authn_request_id, expected_process",
        [
            ("ID-uuid4-portal_type-LOGIN-user_id", LOGINGOVPL_PROCESS.LOGIN),
            ("ID-uuid4-portal_type-LINK-user_id", LOGINGOVPL_PROCESS.LINK),
            ("ID-uuid4-portal_type-OTHER-user_id", None),
            ("ID-uuid4-portal_type--user_id", None),
        ],
    )
    def test_get_process_or_none_from_authn_request_id(self, test_authn_request_id, expected_process):
        """
        Given authorization request identifier as `test_authn_request_id`
        When run the service `get_process_or_none_from_authn_request_id()`
        Then the resulted process type is equal to the `expected_process`
        """
        process = logingovpl_service.get_process_or_none_from_authn_request_id(test_authn_request_id)
        assert process == expected_process

    @pytest.mark.parametrize(
        "test_email, expected_result",
        [
            ("correct_email@example.com", "correct_email@example.com"),
            ("_correct@example.com", "_correct@example.com"),
            ("wrong@email@format@example.com", None),
            ("wrong_letter_]@example.com", None),
            ("wrong@format", None),
            ("drop database;", None),
            ("select * from users;", None),
        ],
    )
    def test_check_attr_email(self, test_email, expected_result):
        """
        Given the `test email`
        When run the service `check_attr_email()`
        Then obtain the `expected result` value
        """
        assert logingovpl_service.check_attr_email(test_email) == expected_result


class TestUserService:

    @pytest.mark.parametrize(
        "portal, user, is_logged, is_expected_user",
        [
            (PORTAL_TYPE.MAIN, "active_user", True, True),
            (PORTAL_TYPE.MAIN, "active_user", False, False),
            (PORTAL_TYPE.ADMIN, "active_user", True, False),
            (PORTAL_TYPE.ADMIN, "active_editor", True, True),
            (PORTAL_TYPE.ADMIN, "active_editor", False, False),
            (PORTAL_TYPE.ADMIN, "admin", True, True),
            (PORTAL_TYPE.ADMIN, "admin", False, False),
            (PORTAL_TYPE.ADMIN, "pending_editor", True, False),
            (PORTAL_TYPE.ADMIN, "inactive_admin", True, False),
        ],
    )
    def test_get_active_session_user_or_none(self, portal, user, is_logged, is_expected_user, request):
        """
        Given the user (logged if `is_logged` is `True`) and portal (MAIN or ADMIN)
        And having that user identifier
        And having flushed sessions
        When try to get active session user with that identifier and given portal
        Then obtain that user if `is_expected_user` is `True`, otherwise obtain `None`
        """
        flush_sessions()
        test_user = request.getfixturevalue(user)
        if is_logged:
            Client().force_login(test_user)
        expected_result = test_user if is_expected_user else None

        result = user_service.get_active_session_user_or_none(test_user.id, portal)
        assert result == expected_result

    def test_get_last_user_by_pesel_or_none(self):
        """
        Given the set of users linked to the login.gov.pl service by the same PESEL,
        And having different roles, states and datetimes of account creation
        When run the service `get_last_user_by_pesel_or_none()` for main portal or admin portal
        Then obtain correct user or `None` if user not found
        """
        assert user_service.get_last_user_by_pesel_or_none("11111111111", PORTAL_TYPE.MAIN) is None
        assert user_service.get_last_user_by_pesel_or_none("11111111111", PORTAL_TYPE.ADMIN) is None

        created_users = {
            "user_1": create_user_with_params(
                "admin user",
                params='{"created": "2024-08-01T10:00:01", "pesel": "11111111111"}',
            ),
            # last active user for admin portal
            "user_2": create_user_with_params(
                "editor user",
                params='{"created": "2024-08-01T10:00:02", "pesel": "11111111111"}',
            ),
            # last active user for main portal
            "user_3": create_user_with_params(
                "active user",
                params='{"created": "2024-08-01T10:00:03", "pesel": "11111111111"}',
            ),
            "user_4": create_user_with_params(
                "pending user",
                params='{"created": "2024-08-01T10:00:04", "pesel": "11111111111"}',
            ),
            "user_5": create_user_with_params(
                "blocked user",
                params='{"created": "2024-08-01T10:00:05", "pesel": "11111111111"}',
            ),
            "user_6": create_user_with_params(
                "pending editor user",
                params='{"created": "2024-08-01T10:00:06", "pesel": "11111111111"}',
            ),
            "user_7": create_user_with_params(
                "unconfirmed user",
                params='{"created": "2024-08-01T10:00:07", "pesel": "11111111111"}',
            ),
        }

        assert user_service.get_last_user_by_pesel_or_none("11111111111", PORTAL_TYPE.MAIN) == created_users["user_3"]
        assert user_service.get_last_user_by_pesel_or_none("11111111111", PORTAL_TYPE.ADMIN) == created_users["user_2"]
