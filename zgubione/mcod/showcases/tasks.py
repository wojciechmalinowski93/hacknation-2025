from django.apps import apps

from mcod.core.api.search import signals as search_signals
from mcod.core.tasks import extended_shared_task


@extended_shared_task
def create_showcase_proposal_task(data):
    model = apps.get_model("showcases.ShowcaseProposal")
    obj = model.create(data)
    return {
        "created": True if obj else False,
        "obj_id": obj.id if obj else None,
    }


@extended_shared_task
def create_showcase_task(showcase_proposal_id):
    model = apps.get_model("showcases.ShowcaseProposal")
    obj = model.objects.filter(id=showcase_proposal_id).first()
    created = obj.convert_to_showcase() if obj else False
    return {
        "created": created,
        "obj_id": obj.showcase_id,
    }


@extended_shared_task
def generate_logo_thumbnail_task(showcase_id):
    model = apps.get_model("showcases.Showcase")
    obj = model.objects.filter(pk=showcase_id).first()
    if obj:
        obj.generate_logo_thumbnail()
        model.objects.filter(pk=showcase_id).update(image_thumb=obj.image_thumb)
        search_signals.update_document.send(model, obj)
    return {"image_thumb": obj.image_thumb_url if obj else None}


@extended_shared_task
def send_showcase_proposal_mail_task(showcaseproposal_id):
    model = apps.get_model("showcases.ShowcaseProposal")
    obj = model.objects.filter(id=showcaseproposal_id).first()
    if obj:
        model.send_showcase_proposal_mail(obj)
        return {"showcase_proposed": f"{obj.title} - {obj.applicant_email}"}
