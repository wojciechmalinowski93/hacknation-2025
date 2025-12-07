import falcon
from django.utils.translation import gettext as _

import mcod.core.api.rdf.namespaces as ns
from mcod.datasets.models import Dataset
from mcod.organizations.models import Organization
from mcod.resources.models import Resource

from .profiles import dcat_ap, dcat_ap_pl, schemaorg


class ProfilesMixin:
    DEFAULT_PROFILE = "dcat_ap"
    DCAT_AP = "dcat_ap"
    DCAT_AP_PL = "dcat_ap_pl"
    SCHEMA_ORG = "schemaorg"
    SUPPORTED_PROFILES = (DCAT_AP, DCAT_AP_PL, SCHEMA_ORG)

    BINDS = {
        DCAT_AP: ns.NAMESPACES,
        DCAT_AP_PL: ns.DCAT_AP_PL_NAMESPACES,
        SCHEMA_ORG: {"schema": ns.NAMESPACES["schema"]},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            self.profile = self.context["request"].params.get("profile", self.DEFAULT_PROFILE)
        else:
            self.profile = self.DEFAULT_PROFILE
        if self.profile not in self.SUPPORTED_PROFILES:
            raise falcon.HTTPBadRequest(title="400 Bad Request", description=_(f"'{self.profile}' profile is not supported"))

    def get_rdf_class_for_model(self, model):
        if self.profile not in self.SUPPORTED_PROFILES:
            raise falcon.HTTPBadRequest(title="400 Bad Request", description=_(f"'{self.profile}' profile is not supported"))

        return {
            self.DCAT_AP: {
                Organization: dcat_ap.FOAFAgent,
                Dataset: dcat_ap.DCATDataset,
                Resource: dcat_ap.DCATDistribution,
            },
            self.DCAT_AP_PL: {
                Organization: dcat_ap_pl.ExtendedFOAFAgent,
                Dataset: dcat_ap_pl.ExtendedDCATDataset,
                Resource: dcat_ap_pl.ExtendedDCATDistribution,
            },
            self.SCHEMA_ORG: {
                Organization: schemaorg.SCHEMAOrganization,
                Dataset: schemaorg.SCHEMADataset,
                Resource: schemaorg.SCHEMADistribution,
            },
        }[self.profile][model]

    def get_rdf_class_for_catalog(self):
        return {
            self.DCAT_AP: dcat_ap.DCATCatalog,
            self.DCAT_AP_PL: dcat_ap_pl.ExtendedDCATCatalog,
            self.SCHEMA_ORG: schemaorg.SCHEMACatalog,
        }[self.profile]

    def add_bindings(self, graph):
        for prefix, namespace in self.BINDS[self.profile].items():
            graph.bind(prefix, namespace)

    def add_pagination_bindings(self, graph):
        graph.bind("hydra", ns.HYDRA)
