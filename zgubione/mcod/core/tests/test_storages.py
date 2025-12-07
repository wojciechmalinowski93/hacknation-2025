import os
import shutil
import typing
from uuid import uuid4

import pytest

if typing.TYPE_CHECKING:
    from falcon.testing import TestClient

from mcod.core.storages import ApplicationImagesStorage, OrganizationImagesStorage, ResourcesStorage


class TestStorages:
    def _test_storage(self, client: "TestClient", storage):
        tmp_name = str(uuid4())
        tmp_path = os.path.join("/", "tmp", str(uuid4()))
        tmp_content = str(uuid4())
        tmp = open(tmp_path, "w")
        tmp.write(tmp_content)
        tmp.close()
        tmp_file = open(tmp_path, "r")

        filename1 = storage.save("%s.txt" % tmp_name, tmp_file)
        filename2 = storage.save("%s.txt" % tmp_name, tmp_file)

        tmp_file.close()

        base_location = storage.base_location
        base_url = storage.base_url

        file1 = os.path.join(base_location, filename1)
        file2 = os.path.join(base_location, filename2)

        url1 = "%s%s" % (base_url, filename1)
        url2 = "%s%s" % (base_url, filename2)

        assert os.path.exists(base_location) is True
        assert os.path.exists(file1) is True
        assert os.path.exists(file2) is True
        with open(file1, "rt") as f:
            assert f.readline() == tmp_content

        result = client.simulate_get(url1)
        assert result.status_code == 200

        result = client.simulate_get(url2)
        assert result.status_code == 200

        os.remove(file1)
        result = client.simulate_get(url1)
        assert result.status_code == 404

        result = client.simulate_get(url2)
        assert result.status_code == 200

        shutil.rmtree(base_location)

        result = client.simulate_get(url1)
        assert result.status_code == 404

        result = client.simulate_get(url2)
        assert result.status_code == 404

    @pytest.mark.run(order=0)
    def test_resources_storage(self, client):
        self._test_storage(client, ResourcesStorage())

    @pytest.mark.run(order=0)
    def test_application_storage(self, client):
        self._test_storage(client, ApplicationImagesStorage())

    @pytest.mark.run(order=0)
    def test_organization_storage(self, client):
        self._test_storage(client, OrganizationImagesStorage())
