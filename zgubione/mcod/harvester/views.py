from celery.result import AsyncResult
from celery_progress.backend import Progress as BaseProgress
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic.edit import FormView

from mcod.harvester.forms import XMLValidationForm
from mcod.harvester.tasks import validate_xml_url_task


class Progress(BaseProgress):

    def get_info(self):
        info = super().get_info()
        if self.result.ready() and self.result.failed():
            info["result"] = {"exception": str(self.result.result)}
        return info


def get_progress(request, task_id):
    result = AsyncResult(task_id)
    progress = Progress(result)
    return JsonResponse(progress.get_info())


class ValidateXMLDataSourceView(FormView):
    http_method_names = ["post"]
    form_class = XMLValidationForm

    def form_valid(self, form):
        task_id = validate_xml_url_task.s(form.cleaned_data["xml_url"]).apply_async_on_commit()
        progress_url = reverse("admin:validate-xml-task-status", args=[task_id])
        return JsonResponse({"success": True, "progress_url": progress_url})

    def form_invalid(self, form):
        return JsonResponse({"success": False, "errors": form.errors})
