import requests_mock
from django.test.client import Client as DjangoClient
from django.urls import reverse

from mcod.harvester.tasks import validate_xml_url_task


def test_validate_xml_url_task(admin):
    # This test actually only checks the correctness of the structure returned by the get_progress view.
    url = "http://example.xml"
    md5_url = "http://example.md5"
    with requests_mock.Mocker() as m:
        m.get(url, text="resp")
        m.head(url, text="resp", headers={"Content-Type": "text/xml"})
        m.get(md5_url, text="md5 hash url resp")
        result = validate_xml_url_task.delay(url)
        progress_url = reverse("admin:validate-xml-task-status", args=[result.task_id])
        client = DjangoClient()
        client.force_login(admin)
        resp = client.get(progress_url)
        assert resp.status_code == 200
        resp_json = resp.json()
        assert "complete" in resp_json
        assert "success" in resp_json
        assert "progress" in resp_json
