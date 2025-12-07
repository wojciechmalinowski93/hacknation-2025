from dateutil import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from mcod.core.tasks import extended_shared_task

User = get_user_model()


@extended_shared_task
def create_data_suggestion(data_suggestion):
    model = apps.get_model("suggestions", "Suggestion")
    suggestion = model()
    suggestion.notes = data_suggestion["notes"]
    suggestion.save()


@extended_shared_task
def send_data_suggestion(suggestion_id):
    model = apps.get_model("suggestions", "Suggestion")
    obj = model.objects.filter(id=suggestion_id).first()
    if obj:
        obj.send_data_suggestion_mail()
        model.objects.filter(pk=suggestion_id).update(send_date=now())
    return {"suggestion": obj.notes} if obj else {}


@extended_shared_task
def create_dataset_suggestion(data_suggestion):
    model = apps.get_model("suggestions", "DatasetSubmission")
    if "submitted_by" in data_suggestion:
        user_id = data_suggestion.pop("submitted_by", None)
        user = User.objects.get(pk=user_id)
        data_suggestion["submitted_by"] = user
    submission = model(**data_suggestion)
    submission.save()


@extended_shared_task
def send_dataset_suggestion_mail_task(obj_id):
    model = apps.get_model("suggestions", "DatasetSubmission")
    obj = model.objects.filter(pk=obj_id).first()
    result = obj.send_dataset_suggestion_mail() if obj else None
    return {
        "sent": bool(result),
        "obj_id": obj.id if obj else None,
    }


@extended_shared_task
def create_accepted_dataset_suggestion_task(obj_id):
    model = apps.get_model("suggestions.DatasetSubmission")
    obj = model.convert_to_accepted(obj_id)
    return {
        "created": bool(obj),
        "obj_id": obj.id if obj else None,
    }


@extended_shared_task
def deactivate_accepted_dataset_submissions():
    model = apps.get_model("suggestions.AcceptedDatasetSubmission")
    published_at_limit = now() - relativedelta.relativedelta(
        days=settings.DEACTIVATE_ACCEPTED_DATASET_SUBMISSIONS_PUBLISHED_DAYS_AGO
    )
    objs = model.published.filter(is_active=True, published_at__lt=published_at_limit)
    for obj in objs:
        obj.is_active = False
        obj.save()
    return {"deactivated": objs.count()}


@extended_shared_task
def send_accepted_submission_comment(obj_id, comment):
    model = apps.get_model("suggestions.AcceptedDatasetSubmission")
    obj = model.objects.filter(id=obj_id).first()
    result = obj.send_accepted_submission_comment_mail(comment) if obj else None
    return {
        "sent": bool(result),
        "obj_id": obj.id if obj else None,
    }
