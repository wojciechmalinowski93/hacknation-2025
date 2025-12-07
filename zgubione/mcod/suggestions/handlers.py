from functools import partial

from django.apps import apps

from mcod.core.api.handlers import RetrieveOneHdlr, SearchHdlr
from mcod.suggestions.deserializers import SubmissionApiRequest, SubmissionListRequest
from mcod.suggestions.documents import AcceptedDatasetSubmissionDoc
from mcod.suggestions.serializers import AcceptedSubmissionApiResponse


class AcceptedSubmissionSearchHdlr(SearchHdlr):
    deserializer_schema = partial(SubmissionListRequest, many=False)
    serializer_schema = partial(AcceptedSubmissionApiResponse, many=True)
    search_document = AcceptedDatasetSubmissionDoc()

    def _get_data(self, cleaned, *args, **kwargs):
        data = super()._get_data(cleaned, *args, **kwargs)
        if self.request.user and self.request.user.is_authenticated:
            for item in data:
                try:
                    my_feedback = next(fb for fb in item.feedback if fb.user_id == self.request.user.id)
                    item.my_feedback = my_feedback.opinion
                except StopIteration:
                    pass
        return data


class AcceptedSubmissionRetrieveOneHdlr(RetrieveOneHdlr):
    deserializer_schema = partial(SubmissionApiRequest, many=False)
    database_model = apps.get_model("suggestions", "AcceptedDatasetSubmission")
    feedback_model = apps.get_model("suggestions", "SubmissionFeedback")
    serializer_schema = partial(AcceptedSubmissionApiResponse, many=False)

    def _get_data(self, cleaned, *args, **kwargs):
        data = super()._get_data(cleaned, *args, **kwargs)
        if self.request.user and self.request.user.is_authenticated:
            try:
                my_feedback = data.feedback.get(user=self.request.user)
                data.my_feedback = my_feedback.opinion
            except self.feedback_model.DoesNotExist:
                pass
        return data
