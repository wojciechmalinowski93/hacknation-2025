import functools

from mcod.core.api.versions import VERSIONS, get_latest_version


def versioned(method):
    """
    Request handler is versioned.
    The one with @versioned decorator is the newest one.

    Example:

    from service.tools import versioning, RequestHandler

    class MyHandler:
        @versioned
        def on_get(self, req, resp):
            self.finish('newest version')

        @on_get.version('1.0')
        def get(self):
            self.finish('older version')

    You can also use versioning for other functions in handler and version only part of code:

    class SomeRequestHandler(RequestHandler):
        def get(self):
            self.finish(self.format_response())

        @versioned
        def format_response(self):
            return 'new version'

        @format_response.version('1.2')
        def format_response(self):
            return 'old version'
    """
    # dict of version: function pairs
    # method is at newest version

    method.VERSIONS = {str(get_latest_version()): method}

    def _get_version(version=None):
        latest_version = str(get_latest_version())
        version = version or latest_version
        m = method.VERSIONS.get(version)

        if m is None:
            if len(method.VERSIONS.keys()) == 1:
                return method.VERSIONS[latest_version]

            sk = sorted(method.VERSIONS.keys())
            versions = [v for v in VERSIONS if v <= version and v in sk]
            min_version = max(versions)

            m = method.VERSIONS[str(min_version)]
        return m

    method.get_version = _get_version

    def _version(v):
        def decor(m):
            method.VERSIONS[v] = m

            @functools.wraps(m)
            def w(self, req, resp, *args, **kwargs):
                _m = method.get_version(req.api_version)
                return _m(self, req, resp, *args, **kwargs)

            w.get_version = _get_version
            w.version = _version
            return w

        return decor

    method.version = _version

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        latest_version = str(get_latest_version())
        version = getattr(self, "api_version", latest_version)
        m = method.get_version(version)
        return m(self, *args, **kwargs)

    wrapper.get_version = method.get_version
    wrapper.version = method.version
    wrapper.__doc__ = method.__doc__
    return wrapper
