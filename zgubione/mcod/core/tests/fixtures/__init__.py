import os

import pytest
import requests_mock
from django.conf import settings
from falcon.util.structures import Context

from mcod.core.tests.fixtures.api_fixtures import *  # noqa
from mcod.core.tests.fixtures.bdd import *  # noqa
from mcod.core.tests.fixtures.beat_schedule import *  # noqa
from mcod.core.tests.fixtures.categories import *  # noqa
from mcod.core.tests.fixtures.datasets_fixtures import *  # noqa
from mcod.core.tests.fixtures.dga import *  # noqa
from mcod.core.tests.fixtures.elasticsearch import *  # noqa
from mcod.core.tests.fixtures.harvester import *  # noqa
from mcod.core.tests.fixtures.legacy import *  # noqa
from mcod.core.tests.fixtures.licenses import *  # noqa
from mcod.core.tests.fixtures.newsletter import *  # noqa
from mcod.core.tests.fixtures.rdf import *  # noqa
from mcod.core.tests.fixtures.suggestions import *  # noqa
from mcod.core.tests.fixtures.tags import *  # noqa
from mcod.core.tests.fixtures.users import *  # noqa
from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.lib.triggers import session_store

adapter = requests_mock.Adapter()


def hack_pytest_bdd():
    from pytest_bdd.parser import STEP_PARAM_RE, Step

    def render(self, context):
        def replacer(m):
            varname = m.group(1)
            return str(context[varname])

        if not context:
            return self.name

        return STEP_PARAM_RE.sub(replacer, self.name)

    # There's a bug in pytest-bdd 5.0.0 that disallows usage of < and > sings together in Scenario steps
    # since they are treated as context varnames.
    # https://github.com/pytest-dev/pytest-bdd/issues/447
    # Simple hack for backwards compability is to only treat <tag> as context varnames inside Scenario Outlines that is
    # when context is provided
    Step.render = render


def pytest_configure(config):
    hack_pytest_bdd()
    config.addinivalue_line("markers", "elasticsearch: mark test to run with new empty set of indices")


def pytest_sessionstart(session):
    from mcod.resources.link_validation import session

    session.mount("http://test.mcod", adapter)


def pytest_sessionfinish(session):
    pass


def pytest_runtest_setup(item):
    import random
    import string

    from django_elasticsearch_dsl.registries import registry

    from mcod.core.api.rdf.registry import registry as rdf_registry

    es_marker = item.get_closest_marker("elasticsearch")

    if es_marker:
        for index in registry.get_indices():
            index.delete(ignore=404)
            index.settings(**settings.ELASTICSEARCH_DSL_INDEX_SETTINGS)
            index.create()

    sparql_marker = item.get_closest_marker("sparql")
    if sparql_marker:
        chars = string.ascii_uppercase + string.ascii_lowercase
        graph_name = "".join(random.choice(chars) for _ in range(18))
        graph_uri = f"<http://test.mcod/{graph_name}>"
        rdf_registry.create_named_graph(graph_uri)


def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    run_on_commit_events()


def pytest_runtest_teardown(item, nextitem):
    import shutil

    from django_celery_beat.models import PeriodicTask
    from django_elasticsearch_dsl.registries import registry

    from mcod.core.api.rdf.registry import registry as rdf_registry
    from mcod.resources.indexed_data import es_connections

    worker = os.environ.get("PYTEST_XDIST_WORKER", "")
    archives_path = os.path.join(settings.DATASETS_MEDIA_ROOT, "archives", worker)
    if os.path.exists(archives_path):
        shutil.rmtree(archives_path)

    es_marker = item.get_closest_marker("elasticsearch")
    if es_marker:
        worker = os.environ.get("PYTEST_XDIST_WORKER", "")
        idx_prefix = getattr(settings, "ELASTICSEARCH_INDEX_PREFIX", None)
        es = es_connections.get_connection()
        for res_index in es.indices.get_alias(f"{idx_prefix}-{worker}-*"):
            es.indices.delete(index=res_index, ignore=[404])
        for index in registry.get_indices():
            index.delete(ignore=404)

    sparql_marker = item.get_closest_marker("sparql")
    if sparql_marker:
        rdf_registry.delete_named_graph()
    periodic_task_marker = item.get_closest_marker("periodic_task")
    if periodic_task_marker:
        PeriodicTask.objects.all().delete()


@pytest.fixture(autouse=True)
def enable_db_access(db):
    pass


@pytest.fixture
def ctx():
    return {}


@pytest.fixture
def context():
    _context = Context()
    _context.obj = {}
    _context.api = Context()
    _context.api.headers = {
        "Accept-Language": "pl",
        "Content-Type": "application/vnd.api+json",
    }
    _context.api.cookies = {}

    _context.api.method = "GET"
    _context.api.path = "/"
    _context.api.params = {}
    _context.api.body = {}
    _context.user = None
    _context.session = session_store()
    return _context


@pytest.fixture
def admin_context(admin: "User") -> Context:  # noqa: F405
    _context = Context()
    _context.obj = {}
    _context.admin = Context()
    _context.admin.headers = {
        "Accept-Language": "pl",
    }

    _context.admin.method = "GET"
    _context.admin.path = "/"
    _context.admin.user = admin
    _context.admin.params = {}
    _context.admin.body = {}
    _context.user = None
    _context.session = session_store()
    _context.form_class = None
    _context.form_data = {}
    _context.form_files = None
    _context.form_instance = None
    _context.form = None
    return _context


@pytest.fixture(autouse=True)
def archive_storage_mocker(mocker):
    worker = os.environ.get("PYTEST_XDIST_WORKER", "")
    archives_path = os.path.join(settings.DATASETS_MEDIA_ROOT, "archives", worker)
    mocker.patch(
        "mcod.core.storages.DatasetsArchivesStorage.location",
        return_value=archives_path,
        new_callable=mocker.PropertyMock,
    )
