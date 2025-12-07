from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import pytest
from django.conf import settings
from falcon.testing import Result, TestClient as FalconTestClient

from mcod.core.exceptions import ElasticsearchIndexError
from mcod.core.utils import FileMeta
from mcod.reports import views as reports_views
from mcod.reports.broken_links.constants import (
    BROKENLINKS_ES_INDEX_NAME,
    ReportFormat,
    ReportLanguage,
)


@pytest.fixture
def mocked_file_meta() -> FileMeta:
    """Mocked FileMeta object as a result of the `get_file_metadata()` function."""
    return FileMeta(
        created=datetime(2025, 9, 23, 12, 0, 0, tzinfo=timezone.utc),
        modified=datetime(2025, 9, 23, 13, 0, 0, tzinfo=timezone.utc),
        accessed=datetime(2025, 9, 23, 14, 0, 0, tzinfo=timezone.utc),
        size=999,
    )


@pytest.mark.parametrize("language", [ReportLanguage.PL, ReportLanguage.EN, ""])
def test_endpoint_reports_brokenlinks_success(
    monkeypatch,
    client14,
    sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    mocked_file_meta,
    language,
):
    # GIVEN
    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)
    mocked_rows_count = 123
    monkeypatch.setattr(reports_views, "get_index_total", lambda index: mocked_rows_count)
    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks", headers={"Accept-Language": language})
    # THEN
    assert resp.status_code == 200
    assert "meta" in resp.json
    assert "data" in resp.json
    assert "links" in resp.json
    assert "jsonapi" in resp.json
    assert resp.json["meta"]["language"] == language if language else "pl"  # "pl" is set as a default
    data_attrs = resp.json["data"]["attributes"]
    assert data_attrs["rows_count"] == mocked_rows_count
    assert data_attrs["update_date"] == mocked_file_meta.created.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    assert data_attrs["files"] == [
        {"file_size": mocked_file_meta.size, "format": "csv", "download_url": settings.API_URL + "/reports/brokenlinks/csv"},
        {"file_size": mocked_file_meta.size, "format": "xlsx", "download_url": settings.API_URL + "/reports/brokenlinks/xlsx"},
    ]


@pytest.mark.parametrize("wrong_lang", ["de", "abc", "true", " ", 1])
def test_endpoint_reports_brokenlinks_failure_wrong_language(client14, wrong_lang):
    # GIVEN/WHEN
    resp = client14.simulate_get(f"/reports/brokenlinks?lang={wrong_lang}")
    # THEN
    assert resp.status_code == 400
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "400_bad_request"
    assert data_error["title"] == "400 Bad Request"
    assert data_error["detail"] == f"Wrong language '{wrong_lang}'; acceptable languages: 'pl','en'"


def test_endpoint_reports_brokenlinks_failure_report_file_not_found(monkeypatch, client14):
    # GIVEN
    monkeypatch.setattr(reports_views, "get_public_broken_links_root_path", lambda lang, format_: None)
    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks")
    # THEN
    assert resp.status_code == 404
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "404_not_found"
    assert data_error["title"] == "404 Not Found"
    assert data_error["detail"] == "Report file not found"


def test_endpoint_reports_brokenlinks_failure_report_data_not_found(
    monkeypatch,
    client14,
    sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    mocked_file_meta,
):
    # GIVEN
    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)

    def raise_es_index_error(index):
        raise ElasticsearchIndexError("Elasticsearch index error")

    monkeypatch.setattr(reports_views, "get_index_total", raise_es_index_error)
    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks")
    # THEN
    assert resp.status_code == 404
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "404_not_found"
    assert data_error["title"] == "404 Not Found"
    assert data_error["detail"] == "Report data not found"


@pytest.mark.parametrize("language", [ReportLanguage.PL, ReportLanguage.EN, ""])
def test_endpoint_reports_brokenlinks_data_success(
    monkeypatch, client14, es_hit_factory, sample_public_broken_links_files, mocked_file_meta, language
):
    # GIVEN
    mocked_rows_count = 2
    mocked_es_hits = es_hit_factory.create_many(count=mocked_rows_count)
    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)
    monkeypatch.setattr(reports_views, "get_index_hits", lambda *args, **kwargs: mocked_es_hits)
    monkeypatch.setattr(reports_views, "get_index_total", lambda *args, **kwargs: mocked_rows_count)

    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks/data", headers={"Accept-Language": language})

    # THEN
    assert resp.status_code == 200
    assert "meta" in resp.json
    assert "data" in resp.json
    assert "links" in resp.json
    assert "jsonapi" in resp.json

    resp_meta = resp.json["meta"]
    assert "language" in resp_meta
    assert resp_meta["language"] == language if language else "pl"
    assert "count" in resp_meta
    assert resp_meta["count"] == mocked_rows_count
    assert "headers_map" in resp_meta
    assert "institution" in resp_meta["headers_map"]
    assert "dataset" in resp_meta["headers_map"]
    assert "portal_data_link" in resp_meta["headers_map"]
    assert "link" in resp_meta["headers_map"]
    assert "data_schema" in resp_meta
    assert "fields" in resp_meta["data_schema"]
    data_schema_fields = (el["name"] for el in resp_meta["data_schema"]["fields"])
    assert set(data_schema_fields) == {"institution", "dataset", "portal_data_link", "link"}

    resp_data = resp.json["data"]
    assert len(resp_data) == mocked_rows_count
    data_row = resp_data[0]
    assert data_row["type"] == "row"
    assert "id" in data_row
    assert "attributes" in data_row
    assert "meta" in data_row
    assert "links" in data_row
    data_row_attrs_fields = data_row["attributes"].keys()
    assert set(data_row_attrs_fields) == {"institution", "dataset", "portal_data_link", "link"}
    dt = data_row["meta"]["updated_at"]
    assert dt.endswith("Z")


@pytest.mark.parametrize("wrong_lang", ["de", "abc", "true", " ", 1])
def test_endpoint_reports_brokenlinks_data_failure_wrong_language(client14, wrong_lang):
    # GIVEN/WHEN
    resp = client14.simulate_get(f"/reports/brokenlinks/data?lang={wrong_lang}")
    # THEN
    assert resp.status_code == 400
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "400_bad_request"
    assert data_error["title"] == "400 Bad Request"
    assert data_error["detail"] == f"Wrong language '{wrong_lang}'; acceptable languages: 'pl','en'"


def test_endpoint_reports_brokenlinks_data_failure_report_file_not_found(monkeypatch, client14):
    # GIVEN
    monkeypatch.setattr(reports_views, "get_public_broken_links_root_path", lambda lang, format_: None)
    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks/data")
    # THEN
    assert resp.status_code == 404
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "404_not_found"
    assert data_error["title"] == "404 Not Found"
    assert data_error["detail"] == "Report file not found"


def test_endpoint_reports_brokenlinks_data_failure_report_data_not_found(
    monkeypatch, client14, sample_public_broken_links_files, mocked_file_meta
):
    # GIVEN
    def raise_es_index_error(*args, **kwargs):
        raise ElasticsearchIndexError("Elasticsearch index error")

    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)
    monkeypatch.setattr(reports_views, "get_index_hits", raise_es_index_error)

    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks/data")

    # THEN
    assert resp.status_code == 404
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "404_not_found"
    assert data_error["title"] == "404 Not Found"
    assert data_error["detail"] == "Report data not found"


@pytest.mark.parametrize(
    "page, per_page, expected_from, expected_size",
    [
        (1, 2, 0, 2),
        (2, 2, 2, 2),
        (3, 2, 4, 2),
        (10, 50, 450, 50),
    ],
)
def test_endpoint_brokenlinks_data_pagination_params(
    monkeypatch,
    client14,
    es_hit_factory,
    sample_public_broken_links_files,
    mocked_file_meta,
    page,
    per_page,
    expected_from,
    expected_size,
):
    """
    Test if proper pagination parameters are used during searching in Elasticsearch index.
    """
    # GIVEN
    captured_kwargs = {}

    def fake_get_index_hits(*args, **kwargs):
        captured_kwargs.update(kwargs)
        hit = es_hit_factory.create()
        return [hit]

    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)
    monkeypatch.setattr(reports_views, "get_index_hits", fake_get_index_hits)
    monkeypatch.setattr(reports_views, "get_index_total", lambda *args, **kwargs: 1)
    # WHEN
    resp = client14.simulate_get(f"/reports/brokenlinks/data?page={page}&per_page={per_page}")
    # THEN
    assert resp.status_code == 200
    assert captured_kwargs["index"] == BROKENLINKS_ES_INDEX_NAME
    assert captured_kwargs["from_"] == expected_from
    assert captured_kwargs["size"] == expected_size


@pytest.mark.parametrize(
    "sort_param, expected_order",
    [
        ("dataset", ["A", "B", "C", "D", "E"]),
        ("-dataset", ["E", "D", "C", "B", "A"]),
    ],
)
def test_endpoint_brokenlinks_data_sorting(
    monkeypatch, client14, es_hit_factory, sample_public_broken_links_files, mocked_file_meta, sort_param, expected_order
):
    # GIVEN
    captured_kwargs = {}

    def fake_get_index_hits(*args, **kwargs):
        captured_kwargs.update(kwargs)
        hits = es_hit_factory.create_many(count=5)
        for hit, val in zip(hits, expected_order):
            hit.source["dataset"] = val
        key_field = sort_param.lstrip("-")
        reverse = sort_param.startswith("-")
        hits.sort(key=lambda h: h.source[key_field], reverse=reverse)
        return hits

    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)
    monkeypatch.setattr(reports_views, "get_index_hits", fake_get_index_hits)
    monkeypatch.setattr(reports_views, "get_index_total", lambda *args, **kwargs: 5)

    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks/data", params={"sort": sort_param})

    # THEN
    assert resp.status_code == 200
    assert "sort" in captured_kwargs
    key_field = sort_param.lstrip("-")
    es_sort_field = list(captured_kwargs["sort"][0].keys())[0]
    assert es_sort_field.startswith(key_field)
    es_sort_order = captured_kwargs["sort"][0][es_sort_field]["order"]
    assert es_sort_order == ("desc" if sort_param.startswith("-") else "asc")
    data = resp.json["data"]
    dataset_values = [row["attributes"]["dataset"]["val"] for row in data]
    assert dataset_values == expected_order


@pytest.mark.parametrize(
    "search_q, expected_dataset, expected_institution",
    [
        ("Wzgórze poetów", "Dataset A", "Inst1"),  # standard text
        ("institution:Inst1", "Dataset A", "Inst1"),  # fixed column 'institution'
        ("/Inst[12]/", "Dataset B", "Inst2"),  # regex
        ("Ceny mieszkań~1", "Dataset C", "Inst3"),  # fuzzy search
        ('"Exact phrase"', "Dataset D", "Inst4"),  # phrase search
    ],
)
def test_endpoint_brokenlinks_data_search(
    monkeypatch,
    client14,
    es_hit_factory,
    sample_public_broken_links_files,
    mocked_file_meta,
    search_q,
    expected_dataset,
    expected_institution,
):
    # GIVEN
    def fake_get_index_hits(*args, **kwargs):
        hit = es_hit_factory.create(dataset=expected_dataset, institution=expected_institution)
        return [hit]

    monkeypatch.setattr(
        reports_views, "get_public_broken_links_root_path", lambda lang, format_: sample_public_broken_links_files[lang, format_]
    )
    monkeypatch.setattr(reports_views, "get_file_metadata", lambda path: mocked_file_meta)
    monkeypatch.setattr(reports_views, "get_index_hits", fake_get_index_hits)
    monkeypatch.setattr(reports_views, "get_index_total", lambda *args, **kwargs: 1)

    # WHEN
    resp = client14.simulate_get("/reports/brokenlinks/data", params={"q": search_q})

    # THEN
    assert resp.status_code == 200
    data = resp.json["data"]
    assert len(data) == 1
    hit_data = data[0]["attributes"]
    assert hit_data["dataset"]["val"] == expected_dataset
    assert hit_data["institution"]["val"] == expected_institution


@pytest.mark.parametrize(
    ("language", "extension"),
    [
        (ReportLanguage.PL, ReportFormat.CSV),
        (ReportLanguage.PL, ReportFormat.XLSX),
        (ReportLanguage.EN, ReportFormat.CSV),
        (ReportLanguage.EN, ReportFormat.XLSX),
    ],
)
def test_public_broken_links_report_download(
    client14: FalconTestClient,
    sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    language: ReportLanguage,
    extension: ReportFormat,
):
    # GIVEN
    download_endpoint_url: str = f"/reports/brokenlinks/{extension}?lang={language}"

    # WHEN
    resp: Result = client14.simulate_get(download_endpoint_url)

    # THEN
    assert resp.status_code == 302
    assert "location" in resp.headers
    location: str = resp.headers["location"]
    expected_file: Path = sample_public_broken_links_files[language, extension]
    assert location == f"{settings.REPORTS_MEDIA}/resources/public/{language}/{expected_file.name}"


@pytest.mark.parametrize("wrong_lang", ("de", "1", "true"))
def test_public_broken_links_report_download_failure_when_wrong_lang(
    client14: FalconTestClient,
    sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    wrong_lang: str,
):
    # GIVEN
    download_endpoint_url: str = f"/reports/brokenlinks/csv?lang={wrong_lang}"

    # WHEN
    resp: Result = client14.simulate_get(download_endpoint_url)

    # THEN
    assert resp.status_code == 400
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "400_bad_request"
    assert data_error["title"] == "400 Bad Request"
    assert data_error["detail"] == f"Wrong language '{wrong_lang}'; acceptable languages: 'pl','en'"


@pytest.mark.parametrize("wrong_format", ("xls", "pdf", "xml"))
def test_public_broken_links_report_download_failure_when_wrong_format(
    client14: FalconTestClient,
    sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    wrong_format: str,
):
    # GIVEN
    download_endpoint_url: str = f"/reports/brokenlinks/{wrong_format}"

    # WHEN
    resp: Result = client14.simulate_get(download_endpoint_url)

    # THEN
    assert resp.status_code == 400
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "400_bad_request"
    assert data_error["title"] == "Invalid format parameter"
    assert data_error["detail"] == f"Unsupported format '{wrong_format}'; acceptable formats: 'csv', 'xlsx'"


def test_public_broken_links_report_download_failure_when_no_report(
    client14: FalconTestClient,
    reports_media_root: Path,
):
    # WHEN
    resp: Result = client14.simulate_get("/reports/brokenlinks/csv")

    # THEN
    assert resp.status_code == 404
    assert "errors" in resp.json
    data_error = resp.json["errors"][0]
    assert data_error["code"] == "404_not_found"
    assert data_error["title"] == "404 Not Found"
    assert data_error["detail"] == "Report file not found"
