# app.videos.models
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.utils import flatatt
from django.utils.safestring import mark_safe
from modelcluster.fields import ParentalKey
from wagtail.embeds.embeds import get_embed_hash
from wagtail.embeds.models import Embed
from wagtailvideos.models import (
    AbstractTrackListing,
    AbstractVideo,
    AbstractVideoTrack,
    AbstractVideoTranscode,
)


class CustomVideo(AbstractVideo):

    admin_form_fields = (
        "title",
        "file",
        "collection",
        "thumbnail",
        "tags",
    )

    @property
    def thumbnail_url(self):
        return self._get_cms_url(self.thumbnail.url) if self.thumbnail else ""

    @property
    def video_url(self):
        return self._get_cms_url(self.url)

    @property
    def embed_html(self):
        attrs = {"controls": "", "style": "max-width:100%;width:100%;height:auto;"}
        if self.thumbnail:
            attrs["poster"] = self.thumbnail_url

        transcodes = self.get_current_transcodes()
        sources = []
        for transcode in transcodes:
            sources.append(
                "<source src='{0}' type='video/{1}' >".format(self._get_cms_url(transcode.url), transcode.media_format.name)
            )

        sources.append("<source src='{0}' type='{1}'>".format(self.video_url, self.content_type))
        return mark_safe(
            "<video {0}>\n{1}\n{2}\n</video>".format(flatatt(attrs), "\n".join(sources), "\n".join(self.get_tracks()))
        )

    def _get_cms_url(self, url):
        return f"{settings.CMS_URL}{url}"

    def update_video_embed(self, update_html_only=False):
        url = self._get_cms_url(f"/admin/videos/{self.pk}/")
        urls_to_check = [url, url[:-1]]
        embed_hashes = []
        for link in urls_to_check:
            embed_hashes.append(get_embed_hash(link))
        embeds = Embed.objects.filter(hash__in=embed_hashes)
        if embeds:
            update_kwargs = {
                "html": self.embed_html,
            }
            if not update_html_only:
                update_kwargs["title"] = self.title
                update_kwargs["thumbnail_url"] = self.thumbnail_url
            embeds.update(**update_kwargs)

    class Meta:
        ordering = ["-created_at"]


class CustomTranscode(AbstractVideoTranscode):
    video = models.ForeignKey(CustomVideo, related_name="transcodes", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("video", "media_format")


class CustomTrackListing(AbstractTrackListing):
    video = models.OneToOneField(CustomVideo, related_name="track_listing", on_delete=models.CASCADE)


class CustomVideoTrack(AbstractVideoTrack):
    listing = ParentalKey(CustomTrackListing, related_name="tracks", on_delete=models.CASCADE)

    def track_tag(self):
        attrs = {
            "kind": self.kind,
            "src": f"{settings.CMS_URL}{self.url}",
        }
        if self.label:
            attrs["label"] = self.label
        if self.language:
            attrs["srclang"] = self.language

        return "<track {0}{1}>".format(flatatt(attrs), " default" if self.sort_order == 0 else "")


@receiver(post_save, sender=CustomVideo)
def video_embed_update_handler(sender, instance, *args, **kwargs):
    instance.update_video_embed()


@receiver(post_save, sender=CustomTranscode)
@receiver(post_delete, sender=CustomTranscode)
@receiver(post_save, sender=CustomTrackListing)
@receiver(post_delete, sender=CustomTrackListing)
def related_embed_update_handler(sender, instance, *args, **kwargs):
    instance.video.update_video_embed(update_html_only=True)


@receiver(post_save, sender=CustomVideoTrack)
@receiver(post_delete, sender=CustomVideoTrack)
def video_track_embed_update_handler(sender, instance, *args, **kwargs):
    instance.listing.video.update_video_embed(update_html_only=True)
