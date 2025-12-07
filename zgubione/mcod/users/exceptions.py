class SAMLArtException(Exception):
    """Exception raised when a SAML Art fails validation"""

    ...


class NotEnoughUserLoginGOVPLDataException(Exception):
    """Exception raised when there is not enough user data for login.gov.pl integration."""

    ...
