import json

import falcon
from django.template import loader
from elasticsearch import RequestError
from elasticsearch_dsl.connections import get_connection

from mcod import settings
from mcod.core.api.openapi.specs import get_spec
from mcod.core.api.versions import DOC_VERSIONS
from mcod.datasets import serializers as dat_responses, views as dat_views
from mcod.histories.api import views as his_views
from mcod.histories.serializers import LogEntryApiResponse
from mcod.lib.encoders import DateTimeToISOEncoder
from mcod.organizations import views as org_views
from mcod.organizations.serializers import InstitutionApiResponse
from mcod.reports import views as reports_views
from mcod.reports.broken_links.serializers import (
    BrokenlinksReportApiResponse,
    BrokenlinksReportDataApiResponse,
)
from mcod.resources import serializers as res_responses, views as res_views
from mcod.search import views as search_views
from mcod.search.serializers import CommonObjectResponse
from mcod.showcases import views as showcases_views
from mcod.showcases.serializers import ShowcaseApiResponse

connection = get_connection()


class ClusterHealthView:
    def on_get(self, request, response, *args, **kwargs):
        response.text = json.dumps(connection.cluster.health())
        response.status = falcon.HTTP_200


class ClusterStateView:
    def on_get(self, request, response, *args, **kwargs):
        response.text = json.dumps(connection.cluster.state())
        response.status = falcon.HTTP_200


class ClusterAllocationView:
    def on_get(self, request, response, *args, **kwargs):
        try:
            result = connection.cluster.allocation_explain()
        except RequestError:
            result = {}
        response.text = json.dumps(result)
        response.status = falcon.HTTP_200


class SwaggerView:
    def on_get(self, request, response, *args, **kwargs):
        template = loader.get_template("swagger_ui/index.html")
        versions = sorted(DOC_VERSIONS, reverse=True)
        active_spec_name = request.params.get("urls.primaryName", f"DANE.GOV.PL API v{versions[0]}")

        spec_urls = [
            *[
                {
                    "url": f"{settings.API_URL}/spec/{version}",
                    "name": f"DANE.GOV.PL API v{version}",
                }
                for version in versions
            ],
            {
                "url": f"{settings.API_URL}/catalog/dcat_ap/spec",
                "name": "DANE.GOV.PL RDF API (DCAT-AP)",
            },
            {
                "url": f"{settings.API_URL}/catalog/dcat_ap_pl/spec",
                "name": "DANE.GOV.PL RDF API (DCAT-AP-PL)",
            },
        ]
        spec_urls.sort(key=lambda spec: spec["name"] != active_spec_name)

        context = {"spec_urls": spec_urls, "custom_css": "custom.css"}

        response.status = falcon.HTTP_200
        response.content_type = "text/html"
        response.text = template.render(context)


class OpenApiSpec:

    def on_get(self, req, resp, version=None, *args, **kwargs):
        if version and version not in DOC_VERSIONS:
            raise falcon.HTTPBadRequest(description="Invalid version")
        spec = get_spec(version=version)
        spec.components.schema("Institutions", schema=InstitutionApiResponse, many=True)
        spec.components.schema("Institution", schema=InstitutionApiResponse, many=False)
        spec.components.schema("Datasets", schema=dat_responses.DatasetApiResponse, many=True)
        spec.components.schema("Dataset", schema=dat_responses.DatasetApiResponse, many=False)
        spec.components.schema("Resources", schema=res_responses.ResourceApiResponse, many=True)
        spec.components.schema("Resource", schema=res_responses.ResourceApiResponse, many=False)
        spec.components.schema(
            "AggregatedDGAInfo",
            schema=res_responses.AggregatedDGAInfoApiResponse,
            many=False,
        )
        spec.components.schema("Charts", schema=res_responses.ChartApiResponse, many=True)
        spec.components.schema("Chart", schema=res_responses.ChartApiResponse, many=False)
        spec.components.schema("ResourceTable", schema=res_responses.TableApiResponse, many=True)
        spec.components.schema("ResourceTableRow", schema=res_responses.TableApiResponse, many=False)
        spec.components.schema("Search", schema=CommonObjectResponse, many=True)
        spec.components.schema("Showcases", schema=ShowcaseApiResponse, many=True)
        spec.components.schema("Showcase", schema=ShowcaseApiResponse, many=False)
        spec.components.schema("Histories", schema=LogEntryApiResponse, many=True)
        spec.components.schema("History", schema=LogEntryApiResponse, many=False)
        spec.components.schema("BrokenlinksReport", schema=BrokenlinksReportApiResponse, many=False)
        spec.components.schema("BrokenlinksReportData", schema=BrokenlinksReportDataApiResponse, many=True)
        spec.path(resource=org_views.InstitutionSearchView)
        spec.path(resource=org_views.InstitutionApiView)
        spec.path(resource=org_views.InstitutionDatasetSearchApiView)
        spec.path(resource=dat_views.DatasetSearchView)
        spec.path(resource=dat_views.DatasetApiView)
        spec.path(resource=dat_views.DatasetResourceSearchApiView)
        spec.path(resource=showcases_views.DatasetShowcasesApiView)
        spec.path(resource=res_views.ResourcesView)
        spec.path(resource=res_views.ResourceView)
        spec.path(resource=res_views.AggregatedDGAInfoView)
        spec.path(resource=res_views.ResourceTableView)
        spec.path(resource=res_views.ResourceTableRowView)
        spec.path(resource=search_views.SearchView)
        spec.path(resource=showcases_views.ShowcasesApiView)
        spec.path(resource=showcases_views.ShowcaseApiView)
        spec.path(resource=his_views.HistoriesView)
        spec.path(resource=his_views.HistoryView)
        spec.path(resource=reports_views.BrokenLinksReportView)
        spec.path(resource=reports_views.BrokenLinksReportDataView)
        spec.path(resource=reports_views.PublicBrokenLinksReportDownloadView)

        resp.text = json.dumps(spec.to_dict(), cls=DateTimeToISOEncoder)
        resp.status = falcon.HTTP_200


class RdfApiSpec:
    desc = None
    spec = None

    def on_get(self, req, resp, version=None, *args, **kwargs):
        with open(settings.SPEC_DIR.path(self.desc), "r") as file:
            description = file.read()
        with open(settings.SPEC_DIR.path(self.spec), "rb") as file:
            spec = json.load(file)
        spec["info"]["description"] = description
        resp.media = spec
        resp.status = falcon.HTTP_200


class RdfDcatApApiSpec(RdfApiSpec):
    desc = "rdf_api_desc_dcat_ap.html"
    spec = "rdf_api_spec_dcat_ap.json"


class RdfDcatApPlApiSpec(RdfApiSpec):
    desc = "rdf_api_desc_dcat_ap_pl.html"
    spec = "rdf_api_spec_dcat_ap_pl.json"
