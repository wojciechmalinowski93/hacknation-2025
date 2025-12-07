from mcod.academy import views as academy_views
from mcod.core.api.utils import views as core_views
from mcod.core.api.views import MetricsResource
from mcod.datasets import views as dataset_views
from mcod.guides import views as guides_views
from mcod.histories.api import views as history_views
from mcod.laboratory import views as laboratory_views
from mcod.newsletter import views as newsletter_views
from mcod.organizations import views as org_views
from mcod.reports import views as reports_views
from mcod.resources import views as res_views
from mcod.schedules import views as schedules_views
from mcod.search import views as search_views
from mcod.searchhistories import views as searchhistory_views
from mcod.showcases import views as showcases_views
from mcod.suggestions import views as submission_views
from mcod.tools import views as tools_views
from mcod.users import views as user_views
from mcod.watchers import views as watcher_views

routes = [
    # Tools & utilities
    ("/search", search_views.SearchView()),
    ("/sparql/{token:uuid}", search_views.SparqlDownloadView()),
    ("/sparql", search_views.SparqlView()),
    ("/search/suggest", search_views.SuggestView()),
    ("/stats", tools_views.StatsView()),
    ("/cluster/health", core_views.ClusterHealthView()),
    ("/cluster/explain", core_views.ClusterAllocationView()),
    ("/cluster/state", core_views.ClusterStateView()),
    ("/catalog/dcat_ap/spec", core_views.RdfDcatApApiSpec()),
    ("/catalog/dcat_ap_pl/spec", core_views.RdfDcatApPlApiSpec()),
    ("/spec", core_views.OpenApiSpec()),
    ("/spec/{version}", core_views.OpenApiSpec()),
    ("/doc", core_views.SwaggerView()),
    ("/licenses/{name}", dataset_views.LicenseView()),
    # User
    ("/auth/login", user_views.LoginView()),
    ("/auth/logout", user_views.LogoutView()),
    ("/auth/password/reset", user_views.ResetPasswordView()),
    ("/auth/password/reset/{token:uuid}", user_views.ConfirmResetPasswordView()),
    ("/auth/password/change", user_views.ChangePasswordView()),
    ("/auth/user", user_views.AccountView()),
    ("/auth/user/dashboard", user_views.DashboardView()),
    ("/auth/registration", user_views.RegistrationView()),
    ("/auth/registration/verify-email/{token:uuid}", user_views.VerifyEmailView()),
    ("/auth/registration/resend-email", user_views.ResendActivationEmailView()),
    ("/auth/subscriptions", watcher_views.SubscriptionsView()),
    ("/auth/subscriptions/{id:int}", watcher_views.SubscriptionView()),
    (
        "/auth/subscriptions/{id:int}/notifications",
        watcher_views.SubscriptionNotificationsView(),
    ),
    ("/auth/notifications", watcher_views.NotificationsView()),
    ("/auth/notifications/status", watcher_views.NotificationsStatusView()),
    # Organizations
    ("/institutions", org_views.InstitutionSearchView()),
    ("/institutions/{id:int}", org_views.InstitutionApiView()),
    ("/institutions/{id:int},{slug}", org_views.InstitutionApiView()),
    ("/institutions/{id:int}/datasets", org_views.InstitutionDatasetSearchApiView()),
    (
        "/institutions/{id:int},{slug}/datasets",
        org_views.InstitutionDatasetSearchApiView(),
    ),
    # RDF
    ("/catalog", dataset_views.CatalogRDFView()),
    ("/catalog.{rdf_format:rdf_format}", dataset_views.CatalogRDFView()),
    (
        "/catalog/dataset/{id:int}.{rdf_format:rdf_format}",
        dataset_views.DatasetRDFView(),
    ),
    ("/catalog/dataset/{id:int}", dataset_views.DatasetRDFView()),
    (
        "/catalog/dataset/{id:int},{slug}.{rdf_format:rdf_format}",
        dataset_views.DatasetRDFView(),
    ),
    ("/catalog/dataset/{id:int},{slug}", dataset_views.DatasetRDFView()),
    (
        "/catalog/dataset/{id:int}/resource/{res_id:int}.{rdf_format:rdf_format}",
        res_views.ResourceRDFView(),
    ),
    ("/catalog/dataset/{id:int}/resource/{res_id:int}", res_views.ResourceRDFView()),
    (
        "/catalog/dataset/{id:int}/resource/{res_id:int},{slug}.{rdf_format:rdf_format}",
        res_views.ResourceRDFView(),
    ),
    (
        "/catalog/dataset/{id:int}/resource/{res_id:int},{slug}",
        res_views.ResourceRDFView(),
    ),
    # RDF Vocabularies
    ("/vocab/openness-score", res_views.VocabOpennessScoreRDFView()),
    ("/vocab/openness-score/{entry_name}", res_views.VocabEntryOpennessScoreRDFView()),
    ("/vocab/special-sign", res_views.VocabSpecialSignRDFView()),
    ("/vocab/special-sign/{entry_name}", res_views.VocabEntrySpecialSignRDFView()),
    # Datasets
    ("/datasets", dataset_views.DatasetSearchView()),
    ("/datasets/{id:int}", dataset_views.DatasetApiView()),
    ("/datasets/{id:int},{slug}", dataset_views.DatasetApiView()),
    ("/datasets/{id:int}/resources", dataset_views.DatasetResourceSearchApiView()),
    (
        "/datasets/{id:int},{slug}/resources",
        dataset_views.DatasetResourceSearchApiView(),
    ),
    ("/datasets/{id:int}/showcases", showcases_views.DatasetShowcasesApiView()),
    ("/datasets/{id:int},{slug}/showcases", showcases_views.DatasetShowcasesApiView()),
    ("/datasets/{id:int}/comments", dataset_views.DatasetCommentsView()),
    ("/datasets/{id:int},{slug}/comments", dataset_views.DatasetCommentsView()),
    (
        "/datasets/{id:int}/resources/files/download",
        dataset_views.DatasetResourcesFilesBulkDownloadView(),
    ),
    (
        "/datasets/{id:int},{slug}/resources/files/download",
        dataset_views.DatasetResourcesFilesBulkDownloadView(),
    ),
    # Resources
    ("/resources", res_views.ResourcesView()),
    ("/resources/charts/{chart_id:int}", res_views.ChartView()),  # obsolete endpoint.
    ("/resources/{id:int}/charts", res_views.ChartsView()),
    ("/resources/{id:int},{slug}/charts", res_views.ChartsView()),
    ("/resources/{id:int}/charts/{chart_id:int}", res_views.ChartView()),
    ("/resources/{id:int},{slug}/charts/{chart_id:int}", res_views.ChartView()),
    ("/resources/{id:int}/chart", res_views.ChartView()),
    ("/resources/{id:int},{slug}/chart", res_views.ChartView()),
    ("/resources/{id:int}", res_views.ResourceView()),
    ("/resources/{id:int},{slug}", res_views.ResourceView()),
    ("/resources/{id:int}/data", res_views.ResourceTableView()),
    ("/resources/{id:int},{slug}/data", res_views.ResourceTableView()),
    ("/resources/{id:int}/data/{row_id:uuid}", res_views.ResourceTableRowView()),
    ("/resources/{id:int},{slug}/data/{row_id:uuid}", res_views.ResourceTableRowView()),
    ("/resources/{id:int}/data/spec", res_views.ResourceTableSpecView()),
    ("/resources/{id:int},{slug}/data/spec", res_views.ResourceTableSpecView()),
    ("/resources/{id:int}/data/spec/{version}", res_views.ResourceTableSpecView()),
    (
        "/resources/{id:int},{slug}/data/spec/{version}",
        res_views.ResourceTableSpecView(),
    ),
    ("/resources/{id:int}/data/doc", res_views.ResourceSwaggerView()),
    ("/resources/{id:int},{slug}/data/doc", res_views.ResourceSwaggerView()),
    ("/resources/{id:int}/geo", res_views.ResourceGeoView()),
    ("/resources/{id:int},{slug}/geo", res_views.ResourceGeoView()),
    ("/resources/{id:int},{slug}/comments", res_views.ResourceCommentsView()),
    # DGA
    ("/dga-aggregated", res_views.AggregatedDGAInfoView()),
    # Depricated views
    ("/resources/{id:int}/incr_download_count", res_views.ResourceDownloadCounter()),
    (
        "/resources/{id:int},{slug}/incr_download_count",
        res_views.ResourceDownloadCounter(),
    ),
    ("/resources/{id:int}/comments", res_views.ResourceCommentsView()),
    ("/resources/{id:int}/csv", res_views.ResourceFileDownloadView(file_type="csv")),
    (
        "/resources/{id:int}/jsonld",
        res_views.ResourceFileDownloadView(file_type="jsonld"),
    ),
    ("/resources/{id:int}/file", res_views.ResourceFileDownloadView()),
    (
        "/resources/{id:int},{slug}/csv",
        res_views.ResourceFileDownloadView(file_type="csv"),
    ),
    (
        "/resources/{id:int},{slug}/jsonld",
        res_views.ResourceFileDownloadView(file_type="jsonld"),
    ),
    ("/resources/{id:int},{slug}/file", res_views.ResourceFileDownloadView()),
    # Histories
    ("/histories", history_views.HistoriesView()),
    ("/histories/{id:int}", history_views.HistoryView()),
    ("/searchhistories", searchhistory_views.SearchHistoriesView()),
    ("/submissions", submission_views.SubmissionView()),
    ("/submissions/accepted", submission_views.AcceptedSubmissionListView()),
    ("/submissions/accepted/{id:int}", submission_views.AcceptedSubmissionDetailView()),
    (
        "/submissions/accepted/{id:int}/feedback",
        submission_views.FeedbackDatasetSubmission(),
    ),
    (
        "/submissions/accepted/public",
        submission_views.AcceptedSubmissionListView(),
        "public_submission",
    ),
    (
        "/submissions/accepted/public/{id:int}",
        submission_views.AcceptedSubmissionDetailView(),
        "public_submission",
    ),
    (
        "/submissions/accepted/public/{id:int}/comment",
        submission_views.AcceptedDatasetSubmissionCommentView(),
    ),
    # LOD
    ("/laboratory", laboratory_views.LaboratorySearchApiView()),
    # Newsletter
    ("/auth/newsletter/subscribe", newsletter_views.SubscribeNewsletterView()),
    (
        "/auth/newsletter/subscribe/{activation_code:uuid}/confirm",
        newsletter_views.ConfirmNewsletterView(),
    ),
    ("/auth/newsletter/unsubscribe", newsletter_views.UnsubscribeNewsletterView()),
    ("/courses", academy_views.CoursesSearchApiView()),
    ("/meetings", user_views.MeetingsView()),
    # Schedules
    ("/auth/schedule_agents", schedules_views.AgentsView()),
    ("/auth/schedule_agents/{id:int}", schedules_views.AgentView()),
    ("/auth/schedule_notifications", schedules_views.NotificationsView()),
    ("/auth/schedule_notifications/{id:int}", schedules_views.NotificationView()),
    ("/auth/schedules", schedules_views.SchedulesView()),
    ("/auth/schedules/current", schedules_views.ScheduleView()),
    (
        "/auth/schedules/current.{export_format:export_format}",
        schedules_views.ExportUrlView(),
    ),
    (
        "/auth/schedules/current/{token:uuid}.{export_format:export_format}",
        schedules_views.ScheduleTabularView(),
    ),
    ("/auth/schedules/{schedule_id:int}", schedules_views.ScheduleView()),
    ("/auth/schedules/{schedule_id:int},{slug}", schedules_views.ScheduleView()),
    (
        "/auth/schedules/{schedule_id:int}.{export_format:export_format}",
        schedules_views.ExportUrlView(),
    ),
    (
        "/auth/schedules/{schedule_id:int}/{token:uuid}.{export_format:export_format}",
        schedules_views.ScheduleTabularView(),
    ),
    (
        "/auth/schedules/{schedule_id:int}/user_schedules",
        schedules_views.UserSchedulesView(),
    ),
    (
        "/auth/schedules/{schedule_id:int},{slug}/user_schedules",
        schedules_views.UserSchedulesView(),
    ),
    (
        "/auth/schedules/{schedule_id:int}/user_schedule_items",
        schedules_views.UserScheduleItemsView(),
    ),
    (
        "/auth/schedules/{schedule_id:int},{slug}/user_schedule_items",
        schedules_views.UserScheduleItemsView(),
    ),
    ("/auth/user_schedules", schedules_views.UserSchedulesView()),
    (
        "/auth/user_schedules.{export_format:export_format}",
        schedules_views.ExportUrlView(),
    ),
    (
        "/auth/user_schedules/{token:uuid}.{export_format:export_format}",
        schedules_views.UserSchedulesTabularView(),
    ),
    ("/auth/user_schedules/current", schedules_views.UserScheduleView()),
    ("/auth/user_schedules/{id:int}", schedules_views.UserScheduleView()),
    ("/auth/user_schedules/{id:int},{slug}", schedules_views.UserScheduleView()),
    ("/auth/user_schedules/{id:int}/items", schedules_views.UserScheduleItemsView()),
    (
        "/auth/user_schedules/{id:int}/items.{export_format:export_format}",
        schedules_views.ExportUrlView(),
    ),
    (
        "/auth/user_schedules/{id:int}/items/{token:uuid}.{export_format:export_format}",
        schedules_views.UserScheduleItemsTabularView(),
    ),
    (
        "/auth/user_schedules/{id:int},{slug}/items",
        schedules_views.UserScheduleItemsView(),
    ),
    (
        "/auth/user_schedules/{id:int},{slug}/items.{export_format:export_format}",
        schedules_views.ExportUrlView(),
    ),
    (
        "/auth/user_schedules/{id:int},{slug}/items/{token:uuid}.{export_format:export_format}",
        schedules_views.UserScheduleItemsTabularView(),
    ),
    ("/auth/user_schedule_items", schedules_views.UserScheduleItemsView()),
    (
        "/auth/user_schedule_items/formats",
        schedules_views.UserScheduleItemFormatsView(),
    ),
    (
        "/auth/user_schedule_items/institutions",
        schedules_views.UserScheduleItemInstitutionsView(),
    ),
    (
        "/auth/user_schedule_items/institutions/{user_id:int}",
        schedules_views.UserScheduleItemInstitutionsView(),
    ),
    (
        "/auth/user_schedule_items.{export_format:export_format}",
        schedules_views.ExportUrlView(),
    ),
    (
        "/auth/user_schedule_items/{token:uuid}.{export_format:export_format}",
        schedules_views.UserScheduleItemsTabularView(),
    ),
    ("/auth/user_schedule_items/{id:int}", schedules_views.UserScheduleItemView()),
    (
        "/auth/user_schedule_items/{id:int},{slug}",
        schedules_views.UserScheduleItemView(),
    ),
    ("/auth/user_schedule_items/{id:int}/comments", schedules_views.CommentsView()),
    (
        "/auth/user_schedule_items/comments/{id:int}/edit",
        schedules_views.CommentsView(),
    ),
    (
        "/auth/user_schedule_items/{id:int},{slug}/comments",
        schedules_views.CommentsView(),
    ),
    ("/datasets/{id:int}/resources/metadata.csv", dataset_views.CSVMetadataView()),
    ("/datasets/resources/metadata.csv", dataset_views.CSVMetadataView(), "catalog"),
    ("/datasets/{id:int}/resources/metadata.xml", dataset_views.XMLMetadataView()),
    ("/datasets/resources/metadata.xml", dataset_views.XMLMetadataView(), "catalog"),
    # Guides
    ("/guides", guides_views.GuidesView()),
    ("/guides/{id:int}", guides_views.GuideView()),
    ("/showcases", showcases_views.ShowcasesApiView()),
    ("/showcases/{id:int}", showcases_views.ShowcaseApiView()),
    ("/showcases/{id:int},{slug}", showcases_views.ShowcaseApiView()),
    ("/showcases/{id:int}/datasets", showcases_views.ShowcaseDatasetsView()),
    ("/showcases/{id:int},{slug}/datasets", showcases_views.ShowcaseDatasetsView()),
    ("/showcases/suggest", showcases_views.ShowcaseProposalView()),
    ("/metrics", MetricsResource()),
    # Reports
    ("/reports/brokenlinks", reports_views.BrokenLinksReportView()),
    ("/reports/brokenlinks/data", reports_views.BrokenLinksReportDataView()),
    ("/reports/brokenlinks/{extension}", reports_views.PublicBrokenLinksReportDownloadView()),
]


routes.extend(list(map(lambda x: ("/{api_version}" + x[0], *x[1:]), routes)))
