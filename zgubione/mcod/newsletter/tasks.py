import logging

from django.apps import apps

from mcod.core.tasks import extended_shared_task

logger = logging.getLogger("mcod")


@extended_shared_task
def remove_inactive_subscription(obj_id):
    subscription_model = apps.get_model("newsletter.Subscription")
    objs = subscription_model.objects.filter(id=obj_id, is_active=False)
    if objs.exists():
        for obj in objs:
            logger.debug(f"Inactive subscription is deleted: {obj}")
        objs.delete()
    return {}


@extended_shared_task
def send_newsletter_mail(newsletter_id, subscription_id, html_message):
    submission_model = apps.get_model("newsletter.Submission")
    obj, created = submission_model.objects.update_or_create(newsletter_id=newsletter_id, subscription_id=subscription_id)
    try:
        obj.send_newsletter_mail(html_message)
    except Exception as exc:
        obj.message = exc
        obj.save()
    return {}


@extended_shared_task
def send_subscription_confirm_mail(obj_id):
    subscription_model = apps.get_model("newsletter.Subscription")
    obj = subscription_model.objects.filter(id=obj_id).first()
    if obj:
        try:
            result = obj.send_subscription_confirm_mail()
            if result:
                logger.debug("Newsletter confirmation email successfully sent!")
        except Exception as exc:
            logger.error("Error during sending of newsletter confirmation email: {}".format(exc))
        return {}


@extended_shared_task
def send_newsletter():
    newsletter_model = apps.get_model("newsletter.Newsletter")
    for newsletter in newsletter_model.objects.to_send_today():
        newsletter.send()
    return {}
