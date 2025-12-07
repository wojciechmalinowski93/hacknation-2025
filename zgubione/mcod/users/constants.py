from enum import Enum


class LOGINGOVPL_PROCESS(Enum):
    """The type of process related to linking/logging by the login.gov.pl service.
    The process can be `UNKNOWN` due to the problem with serializing data obtained
    from the login.gov.pl service.
    """

    LOGIN = "LOGIN"
    LINK = "LINK"
    UNLINK = "UNLINK"
    SWITCH = "SWITCH"
    UNKNOWN = "UNKNOWN"


class LOGINGOVPL_PROCESS_RESULT(Enum):
    """The result of the login.gov.pl process (success/error). The result can be `UNKNOWN`
    due to the problem with serializing data obtained from the login.gov.pl service.
    """

    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class PORTAL_TYPE(Enum):
    """The type of portal (main or admin panel)."""

    MAIN = "MAIN"
    ADMIN = "ADMIN"
    UNKNOWN = "UNKNOWN"


LOGINGOVPL_REQUEST_ID_SEPARATOR = "-"
LOGINGOVPL_UNKNOWN_USER_IDENTIFIER = "UNKNOWN"
EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"  # https://emailregex.com/
