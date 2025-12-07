import json
import logging
import os
import re
import ssl
import tempfile
from hashlib import md5
from urllib.parse import unquote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import requests
import xmlschema
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from mcod import settings
from mcod.resources.link_validation import generate_random_user_agent
from mcod.unleash import is_enabled

xmlschema.limits.MAX_XML_DEPTH = 100  # https://xmlschema.readthedocs.io/en/latest/usage.html#limit-on-xml-data-depth

logger = logging.getLogger("mcod")

requests.packages.urllib3.disable_warnings()


class ExtendedList(list):
    pass


# https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error/55320961#55320961


try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


def make_request(url, head_only=False):
    opts = settings.HTTP_REQUEST_DEFAULT_PARAMS
    response = requests.head(url, **opts) if head_only else requests.get(url, **opts)
    if not response.ok:
        msg = _("%(url)s: invalid response code: %(code)s (%(reason)s)")
        raise Exception(msg % {"url": url, "code": response.status_code, "reason": response.reason})
    return response


def fetch_data(url):
    r = make_request(url)
    try:
        data = json.loads(r.content)
    except Exception as exc:
        raise Exception(f"No valid JSON data in response!\n{exc}")
    data = data.get("result")
    return data["results"] if "results" in data else data


def get_xml_schema_version(*, xml_path=None, xml_url=None):
    if xml_url:
        root = ElementTree.fromstring(requests.get(xml_url, **settings.HTTP_REQUEST_DEFAULT_PARAMS).text)
    else:
        root = ElementTree.parse(xml_path).getroot()

    version_match = re.search(r"{urn:otwarte-dane:harvester:(.*)}", root.tag)
    if not version_match:
        raise Exception("Nie znaleziono informacji o wersji użytego schematu XSD")

    version = version_match.group(1)
    try:
        get_xml_schema_path(version)
    except KeyError:
        raise Exception(f"Niepoprawna wersja schematu XSD: {version}")

    return version


def get_xml_schema_path(version):
    versions = {}
    flag = versions.get(version)
    if flag and not is_enabled(flag):
        raise KeyError(version)
    return settings.HARVESTER_XML_VERSION_TO_SCHEMA_PATH[version]


def get_xml_schema(version):
    return xmlschema.XMLSchema(get_xml_schema_path(version))


def get_xml_as_dict(source, version):
    schema = get_xml_schema(version)
    data = schema.to_dict(source)
    data["xsd_schema_version"] = version
    return data


def decode_xml(url):
    version = get_xml_schema_version(xml_url=url)
    return get_xml_as_dict(url, version)


def fetch_xml_data(url):
    try:
        validate_xml_url(url)
        data = decode_xml(url)
    except Exception as exc:
        raise Exception(f"XML Validation error!\n{exc}")

    result = ExtendedList(data["dataset"]) if isinstance(data, dict) and "dataset" in data else None
    result.xsd_schema_version = data["xsd_schema_version"]
    return result


def mock_data(url):
    with open("mcod/harvester/fixtures/mock2.json") as mock_file:
        data = json.loads(mock_file.read())
        data = data.get("result")
        return data["results"] if "results" in data else data


def validate_xml(xml_path, boolean_result=False):
    xml_schema = get_xml_schema(get_xml_schema_version(xml_path=xml_path))
    if boolean_result:
        return xml_schema.is_valid(xml_path)
    try:
        xml_schema.validate(xml_path)
    except Exception as exc:
        raise Exception(str(exc))


def get_remote_xml_hash(url):
    source_url_prefix, ext = os.path.splitext(url)
    xml_hash_url = f"{source_url_prefix}.md5"
    response = make_request(xml_hash_url)
    xml_hash = response.content.decode("utf-8").rstrip().lower() if response.content else None
    matches = re.finditer(r"(?=(\b[A-Fa-f0-9]{32}\b))", xml_hash)
    result = [match.group(1) for match in matches]
    if not result:
        msg = _('"%(value)s" is not valid MD5 hash!')
        value = "{}...".format(xml_hash[:40]) if len(xml_hash) > 32 else xml_hash
        raise Exception(msg % {"value": value})
    return xml_hash_url, xml_hash


def get_xml_headers(url):
    try:
        response = requests.head(url, **settings.HTTP_REQUEST_DEFAULT_PARAMS)
    except Exception:
        raise Exception(_("External resource is not available!"))
    return response.headers


def check_content_type(headers):
    content_type = headers.get("Content-Type", "")
    if all(["text/xml" not in content_type, "application/xml" not in content_type]):  # "text/xml; charset=utf-8".
        raise Exception(
            _("Invalid Content-Type header: '%(content_type)s'. " "Content-Type must contain 'text/xml' or 'application/xml'!")
            % {"content_type": content_type}
        )


def check_xml_filename(url):
    if url.endswith(".xml"):
        filename = os.path.basename(url)
        if " " in unquote(filename):
            raise Exception(_("Invalid file name: %(filename)s!") % {"filename": filename})


def retrieve_to_file(url):
    headers = {"User-Agent": generate_random_user_agent()}
    request = Request(url, headers=headers)
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    with urlopen(request) as response:
        data = response.read()
        tmp_file.write(data)
    tmp_file.close()
    return tmp_file.name, response.headers


def validate_md5(filename, remote_xml_hash):
    m = md5()
    with open(filename, "rb") as fp:
        for chunk in fp:
            m.update(chunk)
    xml_hash = m.hexdigest()
    if xml_hash != remote_xml_hash:
        raise Exception(_("Remote MD5 hash is not valid!"))
    return xml_hash


def validate_xml_url(url):
    try:
        check_xml_filename(url)
        headers = get_xml_headers(url)
        check_content_type(headers)
        xml_hash_url, remote_hash = get_remote_xml_hash(url)
        filename, headers = retrieve_to_file(url)
        xml_hash = validate_md5(filename, remote_hash)
        validate_xml(filename)

    except Exception as exc:
        raise ValidationError({"xml_url": str(exc)})
    return filename, xml_hash


def fetch_dcat_data(api_url, query):
    store = SPARQLStore(query_endpoint=api_url, returnFormat="application/rdf+xml")
    results = store.query(query, DEBUG=True)
    return results.graph if results else {}
