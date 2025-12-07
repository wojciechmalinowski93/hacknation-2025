import re
from collections import deque

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import EmptyPage, Paginator
from django.urls.exceptions import NoReverseMatch
from hypereditor.fields import HyperField
from rest_framework import fields as drff, relations
from wagtailvideos import get_video_model

from mcod.cms.api.exceptions import UnprocessableEntity
from mcod.cms.api.utils import get_object_detail_url
from mcod.cms.models import CustomImage


class TypeField(drff.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, obj):
        name = type(obj)._meta.app_label + "." + type(obj).__name__
        self.context["view"].seen_types[name] = type(obj)
        return name


class CharField(drff.CharField):
    def __init__(self, fallback_source=None, **kwargs):
        self.fallback_source = fallback_source
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        try:
            return super().get_attribute(instance)
        except AttributeError:
            self.source_attrs = [self.fallback_source]
            return super().get_attribute(instance)


class DetailUrlField(drff.Field):
    def get_attribute(self, instance):
        url = get_object_detail_url(
            self.context["router"],
            self.context["request"],
            type(instance),
            instance.url_path,
        )

        if url:
            return url
        else:
            raise drff.SkipField

    def to_representation(self, url):
        return url


class IntegerField(drff.IntegerField):
    pass


class PageHtmlUrlField(drff.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        try:
            return page.full_url
        except NoReverseMatch:
            return None


class PageTypeField(drff.Field):
    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        if page.specific_class is None:
            return None
        name = page.specific_class._meta.app_label + "." + page.specific_class.__name__
        self.context["view"].seen_types[name] = page.specific_class
        return name


class RelatedField(relations.RelatedField):
    """
    Serializes related objects (eg, foreign keys).

    Example:

    "feed_image": {
        "id": 1,
        "meta": {
            "type": "wagtailimages.Image",
            "detail_url": "http://api.example.com/v1/images/1/"
        }
    }
    """

    def __init__(self, *args, **kwargs):
        self.serializer_class = kwargs.pop("serializer_class")
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        serializer = self.serializer_class(context=self.context)
        return serializer.to_representation(value)


class PageParentField(relations.RelatedField):
    def get_attribute(self, instance):
        parent = instance.get_parent()

        if self.context["base_queryset"].filter(id=parent.id).exists():
            return parent

    def to_representation(self, value):
        from mcod.cms.api.serializers import CmsPageSerializer, get_serializer_class

        page = value.specific
        serializer_class = get_serializer_class(
            page.__class__,
            [
                "id",
                "type",
                "detail_url",
                "html_url",
                "slug",
                "first_published_at",
                "url_path",
                "title",
            ],
            meta_fields=[
                "type",
                "detail_url",
                "html_url",
                "slug",
                "url_path",
                "first_published_at",
            ],
            base=CmsPageSerializer,
        )
        serializer = serializer_class(context=self.context)
        return serializer.to_representation(page)


class PageChildrenField(relations.RelatedField):
    @staticmethod
    def _parse_positive_int_query_param(params, name, default=None):
        if name not in params:
            return default
        param_value = params[name]

        try:
            value = int(param_value)
        except ValueError:
            value = 0

        if value < 1:
            raise UnprocessableEntity(detail=f"{name}: '{param_value}' is not valid positive integer")
        return value

    @staticmethod
    def _parse_model_field_query_param(params, name, model):
        if name not in params:
            return
        param_value = params[name]
        field_name = param_value[1:] if param_value.startswith("-") else param_value
        try:
            model._meta.get_field(field_name)
        except FieldDoesNotExist:
            raise UnprocessableEntity(detail=f"{name}: '{field_name}' is not valid field name")

        return params[name]

    @staticmethod
    def _validate_model_fields(param_name, field_names, model):
        for field_name in field_names:
            try:
                model._meta.get_field(field_name)
            except FieldDoesNotExist:
                raise UnprocessableEntity(detail=f"{param_name}: '{field_name}' is not valid field name")
        return field_names

    def get_attribute(self, instance):
        qs = instance.get_children().public().live()
        try:
            params = self.context["request"].GET
        except (AttributeError, KeyError):
            params = {}

        children_sort = self._parse_model_field_query_param(params, "children_sort", qs.model)
        children_per_page = self._parse_positive_int_query_param(params, "children_per_page")
        children_page = self._parse_positive_int_query_param(params, "children_page", default=1)

        if children_sort:
            qs = qs.order_by(children_sort)

        if children_per_page:
            paginator = Paginator(qs, children_per_page)
            try:
                qs = paginator.page(children_page)
            except EmptyPage:
                qs = qs.none()

        return qs

    def to_representation(self, value):
        from mcod.cms.api.serializers import CmsPageSerializer, get_serializer_class

        try:
            params = self.context["request"].GET
        except (AttributeError, KeyError):
            params = {}

        children_extra_fields = []
        if "children_extra_fields" in params:
            children_extra_fields = params["children_extra_fields"].split(",")

        output = []
        for page in value:
            page = page.specific
            self._validate_model_fields("children_extra_fields", children_extra_fields, page.__class__)
            page_serializer_class = getattr(page, "serializer_class", CmsPageSerializer)
            serializer_class = get_serializer_class(
                page.__class__,
                [
                    "id",
                    "type",
                    "detail_url",
                    "html_url",
                    "slug",
                    "first_published_at",
                    "last_published_at",
                    "url_path",
                    "title",
                    *children_extra_fields,
                ],
                meta_fields=[
                    "type",
                    "detail_url",
                    "html_url",
                    "slug",
                    "url_path",
                    "first_published_at",
                    "last_published_at",
                ],
                base=page_serializer_class,
            )
            serializer = serializer_class(context=self.context)
            output.append(serializer.to_representation(page))
        return output


class ChildRelationField(drff.Field):
    """
    Serializes child relations.

    Child relations are any model that is related to a Page using a ParentalKey.
    They are used for repeated fields on a page such as carousel items or related
    links.

    Child objects are part of the pages content so we nest them. The relation is
    represented as a list of objects.

    Example:

    "carousel_items": [
        {
            "id": 1,
            "meta": {
                "type": "demo.MyCarouselItem"
            },
            "title": "First carousel item",
            "image": {
                "id": 1,
                "meta": {
                    "type": "wagtailimages.Image",
                    "detail_url": "http://api.example.com/v1/images/1/"
                }
            }
        },
        {
            "id": 2,
            "meta": {
                "type": "demo.MyCarouselItem"
            },
            "title": "Second carousel item (no image)",
            "image": null
        }
    ]
    """

    def __init__(self, *args, **kwargs):
        self.serializer_class = kwargs.pop("serializer_class")
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        serializer = self.serializer_class(context=self.context)

        return [serializer.to_representation(child_object) for child_object in value.all()]


class StreamField(drff.Field):
    """
    Serializes StreamField values.

    Stream fields are stored in JSON format in the database. We reuse that in
    the API.

    Example:

    "body": [
        {
            "type": "heading",
            "value": {
                "text": "Hello world!",
                "size": "h1"
            }
        },
        {
            "type": "paragraph",
            "value": "Some content"
        }
        {
            "type": "image",
            "value": 1
        }
    ]

    Where "heading" is a struct block containing "text" and "size" fields, and
    "paragraph" is a simple text block.

    Note that foreign keys are represented slightly differently in stream fields
    to other parts of the API. In stream fields, a foreign key is represented
    by an integer (the ID of the related object) but elsewhere in the API,
    foreign objects are nested objects with id and meta as attributes.
    """

    def to_representation(self, value):
        return value.stream_block.get_api_representation(value, self.context)


class TagsField(drff.Field):
    """
    Serializes django-taggit TaggableManager fields.

    These fields are a common way to link tags to objects in Wagtail. The API
    serializes these as a list of strings taken from the name attribute of each
    tag.

    Example:

    "tags": ["bird", "wagtail"]
    """

    def to_representation(self, value):
        return list(value.all().order_by("name").values_list("name", flat=True))


class LocalizedHyperField(HyperField):

    def __init__(self, *args, **kwargs):
        self.default_classes = kwargs.pop("default_classes", {})
        super().__init__(*args, **kwargs)

    def get_uploaded_video(self, block_settings):
        od_pattern = [pattern for pattern in settings.OD_EMBED["urls"] if re.match(pattern, block_settings.get("video_url", ""))]
        if od_pattern:
            match = re.search(r"/(\d+)/?", block_settings.get("video_url", ""))
            video_pk = match.group(1)
            try:
                video = get_video_model().objects.get(pk=video_pk)
                video_data = {
                    "title": video.title,
                    "thumbnail_url": video.thumbnail_url,
                    "download_url": video.video_url,
                }
            except get_video_model().DoesNotExist:
                video_data = {}
            block_settings["uploaded_video"] = video_data

    def from_db_value(self, value, expression, connection, context=None):
        # Django>=3.0 upgrade fix.
        # https://docs.djangoproject.com/en/3.0/releases/3.0/#features-removed-in-3-0
        return self.to_python(value)

    def update_general_settings(self, block):
        for block_type, default_classes_str in self.default_classes.items():
            if block["settings"].get(block_type) and "id" in block:
                classes = [class_name for class_name in block["general"].get("classes", "").split(" ") if class_name]
                classes.extend([class_name for class_name in default_classes_str.split(" ") if class_name not in classes])
                block["general"]["classes"] = " ".join(classes)

    def to_python(self, value):
        """
        Injects image's alt_pl or alt_en depending on current language,
        provided in 'lang' query param.
        """
        response = super().to_python(value)

        if hasattr(response, "data") and isinstance(response.data, dict):
            blocks = response.data.get("blocks", [])
            all_blocks_settings = []
            visit_queue = deque(blocks)
            while visit_queue:
                block = visit_queue.popleft()
                if isinstance(block.get("settings"), dict):
                    self.update_general_settings(block)
                    all_blocks_settings.append(block["settings"])

                try:
                    visit_queue.extend(block["children"])
                except KeyError:
                    pass

            for block_settings in all_blocks_settings:
                if isinstance(block_settings.get("image"), dict) and "id" in block_settings["image"]:
                    try:
                        img = CustomImage.objects.get(pk=block_settings["image"]["id"])
                        block_settings["image"]["alt"] = img.alt_i18n
                    except CustomImage.DoesNotExist:
                        pass
                self.get_uploaded_video(block_settings)

        return response


class RichTextField(drff.CharField):
    def to_representation(self, value):
        soup = BeautifulSoup(value, "html.parser")
        for embed in soup.findAll("embed"):
            _type = embed.attrs.get("embedtype", "image")
            if _type == "image":
                try:
                    _id = embed.attrs["id"]
                    alt = embed.attrs["alt"]
                    img = CustomImage.objects.get(pk=_id)
                    attrs = {
                        "src": "{}{}".format(settings.CMS_URL, img.file.url),
                        "alt": alt,
                        "id": "cmsImage-{}".format(_id),
                        "class": "cmsImage--{}".format(embed.attrs.get("format", "center")),
                    }
                    new_tag = soup.new_tag("img", **attrs)
                except (CustomImage.DoesNotExist, KeyError):
                    new_tag = ""

                embed.replace_with(new_tag)

        return str(soup)


class HyperEditorJSONField(drff.JSONField):
    def get_attribute(self, instance):
        if getattr(instance, self.source, None):
            self.source_attrs = [self.source, "data"]

        return super().get_attribute(instance)
