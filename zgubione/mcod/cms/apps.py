from django.apps import AppConfig


class CmsConfig(AppConfig):
    name = "mcod.cms"
    label = "cms"

    def ready(self):
        from django.db import models
        from wagtail.core.signals import page_unpublished, post_page_move

        from mcod.cms import models as cms_models
        from mcod.cms.models.base import BasePage

        for model_name in cms_models.__all__:
            page_model = getattr(cms_models, model_name)
            models.signals.post_save.connect(BasePage.on_post_save, sender=page_model)
            models.signals.pre_delete.connect(BasePage.on_pre_delete, sender=page_model)
            page_unpublished.connect(BasePage.on_unpublish, sender=page_model)
            post_page_move.connect(BasePage.on_post_page_move, sender=page_model)
