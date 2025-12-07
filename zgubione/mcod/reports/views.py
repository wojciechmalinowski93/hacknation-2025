from functools import partial
from types import SimpleNamespace
from typing import List, Optional

import falcon
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from elasticsearch_dsl.query import Q

from mcod.core.api.handlers import BaseHdlr
from mcod.core.api.hooks import login_optional
from mcod.core.api.search.helpers import ElasticsearchHit, get_index_hits, get_index_total
from mcod.core.api.views import JsonAPIView
from mcod.core.exceptions import ElasticsearchIndexError
from mcod.core.utils import FileMeta, get_file_metadata
from mcod.core.versioning import versioned
from mcod.reports.broken_links.constants import (
    BROKENLINKS_ES_INDEX_NAME,
    ReportFormat,
    ReportLanguage,
)
from mcod.reports.broken_links.deserializers import (
    BrokenlinksReportApiRequest,
    BrokenlinksReportDataApiRequest,
    PublicBrokenLinksReportDownloadApiRequest,
)
from mcod.reports.broken_links.public import (
    get_public_broken_links_location,
    get_public_broken_links_root_path,
)
from mcod.reports.broken_links.serializers import (
    BrokenlinksReportApiResponse,
    BrokenlinksReportDataApiResponse,
)


class BrokenLinksReportView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/reports/public_brokenlinks_resources.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = BrokenlinksReportApiRequest
        serializer_schema = BrokenlinksReportApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            lang_str = self.request.language
            try:
                lang = ReportLanguage(lang_str)
            except ValueError:
                languages = ",".join(f"'{lang.value}'" for lang in ReportLanguage)
                raise falcon.HTTPBadRequest(description=f"Wrong language '{lang_str}'; acceptable languages: {languages}")
            csv_file_path = get_public_broken_links_root_path(lang, ReportFormat.CSV)
            xlsx_file_path = get_public_broken_links_root_path(lang, ReportFormat.XLSX)
            if not csv_file_path or not xlsx_file_path:
                raise falcon.HTTPNotFound(description="Report file not found")

            try:
                rows_count = get_index_total(index=BROKENLINKS_ES_INDEX_NAME)
            except ElasticsearchIndexError:
                raise falcon.HTTPNotFound(description="Report data not found")

            csv_meta = get_file_metadata(csv_file_path)
            xlsx_meta = get_file_metadata(xlsx_file_path)

            files = [
                {"file_size": meta.size, "download_url": self._get_download_url(fmt), "format": fmt.value}
                for fmt, meta in [(ReportFormat.CSV, csv_meta), (ReportFormat.XLSX, xlsx_meta)]
            ]

            return SimpleNamespace(
                id="public_brokenlinks_report",
                rows_count=rows_count,
                update_date=csv_meta.created,
                files=files,
            )

        def _get_download_url(self, format_: ReportFormat) -> str:
            """
            Get the URL to the endpoint for downloading report file (with the given format).
            """
            return f"{settings.API_URL.rstrip('/')}/reports/brokenlinks/{format_.value}"


class BrokenLinksReportDataView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/reports/public_brokenlinks_resources_data.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = BrokenlinksReportDataApiRequest
        serializer_schema = partial(BrokenlinksReportDataApiResponse, many=True)

        def _get_data(self, cleaned, *args, **kwargs):
            lang_str = self.request.language
            try:
                lang = ReportLanguage(lang_str)
            except ValueError:
                languages = ",".join(f"'{lang.value}'" for lang in ReportLanguage)
                raise falcon.HTTPBadRequest(description=f"Wrong language '{lang_str}'; acceptable languages: {languages}")

            csv_file_path: Optional[str] = get_public_broken_links_root_path(lang, ReportFormat.CSV)
            if not csv_file_path:
                raise falcon.HTTPNotFound(description="Report file not found")
            csv_meta: FileMeta = get_file_metadata(csv_file_path)

            page, per_page = cleaned.get("page", 1), cleaned.get("per_page", 20)
            es_query = self._build_es_query(cleaned.get("q"))
            es_sort = self._build_es_sort(cleaned.get("sort"))
            try:
                es_documents: List[ElasticsearchHit] = get_index_hits(
                    index=BROKENLINKS_ES_INDEX_NAME,
                    size=per_page,
                    from_=(page - 1) * per_page,
                    query=es_query,
                    sort=es_sort,
                )
                es_count = get_index_total(BROKENLINKS_ES_INDEX_NAME, query=es_query)
            except ElasticsearchIndexError:
                raise falcon.HTTPNotFound(description="Report data not found")

            link_repr = str(_("Broken link"))
            data = []
            for i, hit in enumerate(es_documents, start=1):
                obj_id = hit.id
                institution = {"repr": hit.source["institution"], "val": hit.source["institution"]}
                dataset = {"repr": hit.source["dataset"], "val": hit.source["dataset"]}
                portal_data_link = {"repr": hit.source["title"], "val": hit.source["portal_data_link"]}
                link = {"repr": link_repr, "val": hit.source["link"]}

                data.append(
                    SimpleNamespace(
                        id=obj_id,
                        institution=institution,
                        dataset=dataset,
                        portal_data_link=portal_data_link,
                        link=link,
                        updated_at=csv_meta.created,
                        row_no=i,
                        rows_count=es_count,
                    )
                )

            return data

        def _get_meta(self, cleaned: dict, *args, **kwargs) -> dict:
            return {
                "data_schema": {
                    "fields": [
                        {"name": "institution", "type": "string", "format": "default"},
                        {"name": "dataset", "type": "string", "format": "default"},
                        {"name": "portal_data_link", "type": "string", "format": "default"},
                        {"name": "link", "type": "string", "format": "default"},
                    ]
                },
                "headers_map": {
                    "institution": str(_("Publisher")),
                    "dataset": str(_("Dataset")),
                    "portal_data_link": str(_("portal_data_link")),
                    "link": str(_("Broken link to provider data")),
                },
            }

        def _build_es_sort(self, sort_input: Optional[list]) -> list:
            """
            Build Elasticsearch sort DSL from the validated sort input
            (parameter sort from the endpoint string).
            """
            if not sort_input:
                return []

            sort_field = self.deserializer.fields["sort"]
            return sort_field.q(sort_input) or []

        def _build_es_query(self, query_input: Optional[str]) -> Q:
            """
            Build Elasticsearch query DSL for query filter (parameter q
            from the endpoint string).
            """
            return Q("query_string", query=query_input) if query_input else Q()


class PublicBrokenLinksReportDownloadView:
    deserializer_schema = PublicBrokenLinksReportDownloadApiRequest

    def on_request(self, request, response, extension: str, *args, **kwargs):

        try:
            report_format = ReportFormat(extension)
        except ValueError:
            formats: str = ", ".join(f"'{f.value}'" for f in ReportFormat)
            raise falcon.HTTPBadRequest(
                title="Invalid format parameter",
                description=f"Unsupported format '{extension}'; acceptable formats: {formats}",
            )

        lang_str: str = request.language
        try:
            lang = ReportLanguage(lang_str)
        except ValueError:
            languages: str = ",".join(f"'{lang.value}'" for lang in ReportLanguage)
            raise falcon.HTTPBadRequest(description=f"Wrong language '{lang_str}'; acceptable languages: {languages}")

        file_url: Optional[str] = get_public_broken_links_location(lang, report_format)
        if not file_url:
            raise falcon.HTTPNotFound(description="Report file not found")

        response.location = file_url
        response.status = falcon.HTTP_302

    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, extension: str, *args, **kwargs):
        """
        ---
        doc_template: docs/reports/public_brokenlinks_resources_download.yml
        """
        self.on_request(request, response, extension, *args, **kwargs)
