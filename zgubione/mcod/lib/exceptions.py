class DangerousContentError(Exception):
    pass


class EmptyDocument(Exception):
    pass


class InvalidUrl(Exception):
    pass


class InvalidResponseCode(Exception):
    pass


class InvalidSchema(Exception):
    pass


class InvalidContentType(Exception):
    pass


class MissingContentType(Exception):
    pass


class UnsupportedContentType(Exception):
    pass


class ResourceFormatValidation(Exception):
    """
    This exception is typically used when:
      - The file format cannot be determined from a response.
      - The detected format is not in the list of supported formats (settings.SUPPORTED_FORMATS).
    """

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class NoResponseException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
