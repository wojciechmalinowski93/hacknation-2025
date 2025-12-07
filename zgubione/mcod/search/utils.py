import logging

logger = logging.getLogger("mcod")


def get_sparql_limiter_key(req, resp, resource, params):
    """Custom function used to generate limiter key for SparqlView."""
    key = f"{req.path}_{req.access_route[-2] if len(req.access_route) > 1 else req.remote_addr}"
    try:
        page = req.media["data"]["attributes"]["page"] if req.media else None
    except KeyError:
        page = None
    try:
        per_page = req.media["data"]["attributes"]["per_page"] if req.media else None
    except KeyError:
        per_page = None
    if per_page:
        key = f"{key}_{per_page}"
    if page:
        key = f"{key}_{page}"
    logger.debug("Falcon-Limiter key: %s", key)
    return key
