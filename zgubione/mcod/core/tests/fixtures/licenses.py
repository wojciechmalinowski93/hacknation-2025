import pytest

from mcod.licenses.factories import LicenseFactory


@pytest.fixture
def license():
    return LicenseFactory()


@pytest.fixture
def ten_licenses():
    return LicenseFactory.create_batch(10)


@pytest.fixture
def cc_4_license():
    from mcod.licenses.models import License

    return License.objects.create(
        name="CC-BY-NC-4.0",
        title="Creative Commons Attribution-NonCommercial 4.0",
        url="https://creativecommons.org/licenses/by-nc/4.0/",
    )
