import base64
import csv
import io
import json
import os
import random
from collections import namedtuple
from textwrap import dedent

import elasticsearch_dsl
import factory
import falcon
import pytest
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model
from django.contrib.sessions.backends.base import SessionBase
from django.core.cache import caches
from django.core.files.uploadedfile import SimpleUploadedFile
from falcon import testing

from mcod import settings
from mcod.lib.jwt import get_auth_token
from mcod.lib.triggers import session_store as session_store_create

User = get_user_model()


def random_csv_data(columns=5, rows=100):
    _faker_types = [
        ("text", {"max_nb_chars": 100}),
        ("time", {"pattern": "%H:%M:%S", "end_datetime": None}),
        ("date", {"pattern": "%d-%m-%Y", "end_datetime": None}),
        ("month_name", {}),
        ("catch_phrase", {}),
        ("bs", {}),
        ("company", {}),
        ("country", {}),
        ("city", {}),
        ("street_name", {}),
        ("address", {}),
    ]

    header_types = [random.randint(0, len(_faker_types) - 1) for col in range(columns)]
    _headers = [_faker_types[idx][0].title() for idx in header_types]

    f = io.StringIO()
    _writer = csv.writer(f)
    _writer.writerow(_headers)

    for row in range(rows):
        row = []
        for header_idx in header_types:
            provider, extra_kwargs = _faker_types[header_idx]
            row.append(factory.Faker(provider, locale="pl_PL").generate(extra_kwargs))
        _writer.writerow(row)

    return f.getvalue()


@pytest.fixture
def constance_config():
    from constance import config

    return config


@pytest.fixture
def client(test_api_instance) -> testing.TestClient:
    return testing.TestClient(test_api_instance, headers={"X-API-VERSION": "1.0"})


@pytest.fixture
def client14(test_api_instance) -> testing.TestClient:
    return testing.TestClient(test_api_instance, headers={"X-API-VERSION": "1.4", "Accept-Language": "pl"})


@pytest.fixture
def client14_logged_admin(admin, client14, test_api_instance) -> testing.TestClient:
    """
    session_store is used to create backend session for admin user. During login process a JWT token
    is generated which includes also information about session key. Generated token must be consistent with user session.
    Next token is used in request header.
    """
    session_auth_hash = admin.get_session_auth_hash()
    session_store: SessionBase = session_store_create()
    session_store[SESSION_KEY] = str(admin.id)
    session_store[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session_store[HASH_SESSION_KEY] = session_auth_hash
    session_store.save()
    token: str = get_auth_token(admin, session_key=session_store.session_key)
    return testing.TestClient(
        test_api_instance, headers={"X-API-VERSION": "1.4", "Accept-Language": "pl", "Authorization": f"Bearer {token}"}
    )


@pytest.fixture
def token_exp_delta():
    return 315360000  # 10 years


@pytest.fixture
def sessions_cache():
    return caches[settings.SESSION_CACHE_ALIAS]


@pytest.fixture
def invalid_passwords():
    return [
        "abcd1234",
        "abcdefghi",
        "123456789",
        "alpha101",
        "92541001101",
        "9dragons",
        "@@@@@@@@",
        ".........",
        "!!!!!!!!!!!",
        "12@@@@@@@",
        "!!@#$$@ab@@",
        "admin@mc.gov.pl",
        "1vdsA532A66",
    ]


@pytest.fixture
def invalid_passwords_with_user():
    return [
        "abcd1234",
        "abcdefghi",
        "123456789",
        "aaa@bbb.cc",
        "aaa@bbb.c12",
        "bbb@aaa.cc",
        "TestUser123",
        "Test User",
        "Test.User",
        "User.Test123",
        "alpha101",
        "92541001101",
        "9dragons",
        "@@@@@@@@",
        ".........",
        "!!!!!!!!!!!",
        "12@@@@@@@",
        "!!@#$$@ab@@",
        "admin@mc.gov.pl",
        "1vdsA532A66",
    ]


@pytest.fixture
def valid_passwords():
    passwords = [
        "12@@@@@@Ab@",
        "!!@#$$@aBB1@@",
        "Iron.Man.Is.Th3.Best" "Admin7@mc.gov.pl",
        "1vDsA532A.6!6",
    ]
    passwords.extend(["Abcd%s1234" % v for v in settings.SPECIAL_CHARS])
    return passwords


def prepare_file(name, content):
    os.makedirs("media/resources/test", exist_ok=True)
    f = open(f"media/resources/test/{name}", "w")
    f.write(content)
    f.close()
    return f


@pytest.fixture
def file_csv():
    content = "a;b;c;d;\n" "1;2;3;4;\n" "5;6;7;8;\n" "9;0;1;2;\n" "3;4;5;6;\n" "7;8;9;0;\n" "1;2;;4;\n"
    return prepare_file("test_file.csv", content)


@pytest.fixture
def csv_with_date_and_datetime():
    content = "data;datetime"
    content += dedent(
        """
        2019-12-01;2019-12-01
        2019-12-01;2019-12-01 10:12
        2019-12-01;2019-12-01 10:12:01
        2019-12-01;2019-12-01 10:12:01.123219
        2019-12-01;2019-12-01T10:12:01.123219
        2019-12-01;2019.12.01
        2019-12-01;2019.12.01 10:12
        2019-12-01;2019.12.01 10:12:01
        2019-12-01;2019.12.01 10:12:01.123219
        2019-12-01;2019.12.01T10:12:01.123219
        2019-12-01;2019/12/01
        2019-12-01;2019/12/01 10:12
        2019-12-01;2019/12/01 10:12:01
        2019-12-01;2019/12/01 10:12:01.123219
        2019-12-01;2019/12/01T10:12:01.123219
        01-12-2019;01-12-2019
        01-12-2019;01-12-2019 10:12
        01-12-2019;01-12-2019 10:12:01
        01-12-2019;01-12-2019 10:12:01.123219
        01-12-2019;01-12-2019T10:12:01.123219
        01-12-2019;01.12.2019
        01-12-2019;01.12.2019 10:12
        01-12-2019;01.12.2019 10:12:01
        01-12-2019;01.12.2019 10:12:01.123219
        01-12-2019;01.12.2019T10:12:01.123219
        01-12-2019;01/12/2019
        01-12-2019;01/12/2019 10:12
        01-12-2019;01/12/2019 10:12:01
        01-12-2019;01/12/2019 10:12:01.123219
        01-12-2019;01/12/2019T10:12:01.123219"""
    )
    return prepare_file("dates_and_datetime.csv", content)


xml_sample = """<?xml version="1.0"?>
<note>
    <to>Tove</to>
    <from>Jani</from>
    <heading>Reminder</heading>
    <body>Don't forget me this weekend!</body>
</note>"""


@pytest.fixture
def file_xml():
    return prepare_file("test_file.xml", xml_sample)


@pytest.fixture
def file_html():
    content = """<!Document html>
<html>
    <head>
        <title>Test File</title>
    </head>
    <body>
        <h2>The href Attribute</h2>
        <p>HTML links are defined with the a tag. The link address is specified in the href attribute:</p>
        <a href=\"https://www.w3schools.com\">This is a link</a>
        Some sample text
    </body>
</html>"""
    return prepare_file("test_file.html", content)


@pytest.fixture
def file_rdf():
    content = """<?xml version="1.0"?>
<rdf:RDF
xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:si="https://www.w3schools.com/rdf/">
  <rdf:Description rdf:about="https://www.w3schools.com">
    <si:title>W3Schools</si:title>
    <si:author>Jan Egil Refsnes</si:author>
  </rdf:Description>
</rdf:RDF>"""
    return prepare_file("test_file.rdf", content)


json_sample = """{"menu": {
  "id": "file",
  "value": "File",
  "popup": {
    "menuitem": [
      {"value": "New", "onclick": "CreateNewDoc()"},
      {"value": "Open", "onclick": "OpenDoc()"},
      {"value": "Close", "onclick": "CloseDoc()"}
    ]
  }
}}"""


jsonstat_sample = """{
  "version" : "2.0",
    "class" : "dataset",
    "href" : "https://json-stat.org/samples/order.json",
    "label"  : "Demo of value ordering: what does not change, first",
    "id" : ["A","B","C"],
    "size" : [3,2,4],
    "dimension" : {
        "A" : {
            "label" : "A: 3-categories dimension",
            "category" : {
                "index" : ["1", "2", "3"]
            }
        },
        "B" : {
            "label" : "B: 2-categories dimension",
            "category" : {
                "index" : ["1", "2"]
            }
        } ,
        "C" : {
            "label" : "C: 4-categories dimension",
            "category" : {
                "index" : ["1", "2", "3", "4"]
            }
        }
    },
    "value" : [
        "A1B1C1","A1B1C2","A1B1C3","A1B1C4",
        "A1B2C1","A1B2C2","A1B2C3","A1B2C4",

        "A2B1C1","A2B1C2","A2B1C3","A1B1C4",
        "A2B2C1","A2B2C2","A2B2C3","A2B2C4",

        "A3B1C1","A3B1C2","A3B1C3","A3B1C4",
        "A3B2C1","A3B2C2","A3B2C3","A3B2C4"
    ]
}
"""


@pytest.fixture
def file_json():
    return prepare_file("test_file.json", json_sample)


@pytest.fixture
def file_jsonstat():
    return prepare_file("example_jsonstat.json", jsonstat_sample)


jsonapi_sample = {
    "data": {
        "type": "institutions",
        "attributes": {
            "street": "Test",
            "flat_number": None,
            "email": "test@nowhere.tst",
            "slug": "test",
            "created": "2015-05-18 13:21:00.528480+00:00",
            "website": "http://www.uke.gov.pl/",
            "modified": "2017-12-01 10:05:09.055606+00:00",
        },
        "id": "10",
        "relationships": {
            "datasets": {
                "links": {
                    "related": {
                        "href": "/institutions/10/datasets",
                        "meta": {"count": 0},
                    }
                },
                "data": [],
            }
        },
        "links": {"self": "/institutions/10"},
    },
    "links": {"self": "/institutions/10"},
    "meta": {
        "language": "pl",
        "params": {},
        "path": "/institutions/10",
        "rel_uri": "/institutions/10",
    },
}


@pytest.fixture
def file_jsonapi():
    content = json.dumps(jsonapi_sample)
    return prepare_file("test_jsonapi.json", content)


@pytest.fixture
def file_txt():
    content = (
        'jhshjgfjkhgsdfkjas   123423 sdfasfoipm\n<br/>\n{"fake": "json"}\n'
        "<fake>xml</fake>\nyweqioeruxczvb 12  123\t\n\t76ytgfvbnju8765rtfd"
    )
    return prepare_file("test_noformat.txt", content)


@pytest.fixture
def base64_image():
    image = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAADIEl"
        "EQVR42mKQLz/JyAAF/LlHswXyAGWTA4AcWRCG+2wsY9u2bdu2bdu21dk4WXt3YtvunoxijfHd"
        "G5yrjar68eoMvw8Tx4hzBE28TtCEawQNOUVQv1SC+qTwW5+UIVIg8vSKC+TmjfhJ6pZWp+HKW"
        "3K/XQ/pF/Gcvhuu07frevp3XcfADdcYuO8J/bbcpsm8C/IXjQ7XkYLW/iT9FSL556GnlYlHnm"
        "K2u3EBHx8+42PxMnwqUQbz4+d4QHxzMWXXbULaRypSA1HkT9jezt7ktPvvCYQHgwoFc0HWLOj"
        "O3sSOrwYx53X0XnKB6kMT5EyN5SGSl7OA7ev8r1CeQ8li6MNyIm9IQfPUjscDnz7bSTmvpd3E"
        "FDI32Y/0+7DTosADXG5fg8Dp7wI6UWDPuiRSHttwuEUBs8OTfvEF7cYlkqX+HlFAKNx3x30+W"
        "l38K7RaKFEEQ2h29m9MJuWJHbMTjO/txJxWaTsyjqw1tyMFDUin37a7/y/w4T0Uzsur74PYuz"
        "qeuIc23thBfWfnxCmVNsOiyVZlM1Kw8Lbf5tt8tDgD8nn88CMi+FCjHvdqtSb26GXOvnCit8L"
        "D13aOalRaDzpB9vLrkUJ6JNJ/w82/CzjFtU8PHCHhJA5fwvGEhzw2WjA44JkZrhttHExXaN3/"
        "GDlKr0YK7RzDwHXXcXn8/d1uNy/HTuN2xcYkHz7HqQ9gcIHJA/fNcPWV03P4rI7WfY6Qq9hyU"
        "aBDJANXX8Fs82tgEZdUYZMcdZ97us+8dsMzC9zzJotiZ/R29qWrtOp5iFyFlyCJVTWk+ZR0ed"
        "qmK0SfUjC9s3JZsXgS7n3ijoD75J3DB9vb+YzOzrJ9t+g2LJJazXbIuQou9s/F1xW31glrsFf"
        "pO1tDmuh+6rKO+LNaIk+pQjDFx/nIGR1ymkr3oZHkzL9ICQmfUUf6O6b+JJXfWqdmz6Nyh+HR"
        "dBIWdRwSSTshVBvBtU3vw7TpdYhW3Q9Qq8l2OSR8pkju6h+mfG0O/jXOWSptGpJVeJutwgayl"
        "11LjlKryFl8BbmKLiNXocXkKrCQnPkW/DXORUqv/OIPGXytI4mF5NYAAAAASUVORK5CYII="
    )
    return image, 857  # obraz i pierwotny rozmiar w bajtach


@pytest.fixture
def small_image(base64_image):
    decoded_img = base64.b64decode(base64_image[0].split(";base64,")[-1].encode())
    os.makedirs("media/images/applications/test/", exist_ok=True)
    with open("media/images/applications/test/clock.png", "wb") as outfile:
        outfile.write(decoded_img)
    image = SimpleUploadedFile("clock.png", decoded_img)
    return image


@pytest.fixture
def es_dsl_queryset():
    return elasticsearch_dsl.Search()


@pytest.fixture()
def fake_user():
    return namedtuple("User", "email state fullname")


@pytest.fixture()
def fake_session():
    return namedtuple("Session", "session_key")


@pytest.fixture
def fake_client():
    class XmlResource:
        def on_get(self, request, response):
            response.status = falcon.HTTP_200
            response.content_type = falcon.MEDIA_XML
            response.text = xml_sample

    class JsonResource:
        def on_get(self, request, response):
            response.status = falcon.HTTP_200
            response.content_type = falcon.MEDIA_JSON
            response.text = json_sample

    class JsonapiResource:
        def on_get(self, request, response):
            response.status = falcon.HTTP_200
            response.content_type = "application/vnd.api+json; charset=UTF-8"
            response.text = json.dumps(jsonapi_sample)

    fake_api = falcon.API()
    fake_api.add_route("/xml", XmlResource())
    fake_api.add_route("/json", JsonResource())
    fake_api.add_route("/jsonapi", JsonapiResource())
    return testing.TestClient(fake_api)
