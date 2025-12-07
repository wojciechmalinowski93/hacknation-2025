import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _
from modelcluster.fields import ParentalKey
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.fields import CharField
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, RelatedField, UUIDField
from wagtail.admin.edit_handlers import (
    FieldPanel,
    FieldRowPanel,
    InlinePanel,
    MultiFieldPanel,
    ObjectList,
    PublishingPanel,
    RichTextFieldPanel,
    StreamFieldPanel,
    TabbedInterface,
)
from wagtail.api import APIField
from wagtail.api.v2.serializers import StreamField as StreamFieldSerializer
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Orderable, Page

from mcod.cms.blocks import forms as block_forms
from mcod.cms.forms import FormPageForm
from mcod.cms.models.base import BasePage


class FormPageIndex(BasePage):
    parent_page_types = ["cms.RootPage"]
    subpage_types = ["cms.FormPage"]

    max_count = 1
    fixed_url_path = "forms/"
    fixed_slug = "forms"

    class Meta:
        verbose_name = "Lista formularzy i ankiet"
        verbose_name_plural = "Listy formularzy i ankiet"


class AbstractFormset(Orderable):
    title = models.CharField(verbose_name="Tytuł", max_length=255, help_text=_("Tytuł"))
    description = RichTextField(null=True, blank=True)
    required = models.BooleanField(default=False, blank=True)
    ident = models.UUIDField(default=uuid.uuid4, editable=False)
    default_value = models.CharField(
        verbose_name=_("default value"),
        max_length=255,
        blank=True,
        help_text=_("Default value. Comma separated values supported for checkboxes."),
    )
    help_text = models.CharField(verbose_name=_("help text"), max_length=255, blank=True)
    fields = StreamField(
        [
            ("radiobutton", block_forms.RadioButtonBlock(label="Radio button")),
            (
                "radiobuttonwithinput",
                block_forms.RadioButtonWithInputBlock(label="Radio button z polem tekstowym"),
            ),
            (
                "radiobuttonwithmultilineinput",
                block_forms.RadioButtonWithMultilineInputBlock(label="Radio button z wielolinijkowym polem tekstowym"),
            ),
            ("checkbox", block_forms.CheckboxBlock(label="Checkbox")),
            (
                "checkboxwithinput",
                block_forms.CheckboxWithInputBlock(label="Checkbox z polem tekstowym"),
            ),
            (
                "checkboxwithmultilineinput",
                block_forms.CheckboxWithMultilineInputBlock(label="Checkbox z wielolinijkowym polem tekstowym"),
            ),
            (
                "singlelinetextinput",
                block_forms.SinglelineTextInput(label="Pole tekstowe"),
            ),
            (
                "multilinetextinput",
                block_forms.MultilineTextInput(label="Wielolinijkowe pole tekstowe"),
            ),
        ]
    )

    panels = [
        FieldPanel("title"),
        RichTextFieldPanel("description"),
        FieldPanel("required"),
        StreamFieldPanel("fields"),
    ]

    class Meta:
        abstract = True
        ordering = ["sort_order"]


class Formset(AbstractFormset):
    page = ParentalKey("FormPage", on_delete=models.CASCADE, related_name="formsets")


class FormsetEn(AbstractFormset):
    page = ParentalKey("FormPage", on_delete=models.CASCADE, related_name="formsets_en")


class FormFieldSerializer(ModelSerializer):
    fields = StreamFieldSerializer()
    name = UUIDField(source="ident")

    class Meta:
        model = Formset
        fields = ["title", "description", "required", "fields", "default_value", "name"]
        depth = 1


class FormFieldEnSerializer(ModelSerializer):
    fields = StreamFieldSerializer()
    name = UUIDField(source="ident")

    class Meta:
        model = FormsetEn
        fields = ["title", "description", "required", "fields", "default_value", "name"]
        depth = 1


class APIFormsetField(RelatedField):
    def to_representation(self, value):
        lang = get_language()
        serializer_cls = FormFieldEnSerializer if lang == "en" else FormFieldSerializer
        serialized = serializer_cls(value)
        return serialized.data


class FormPageSubmission(models.Model):
    form_data = JSONField(blank=True, null=True, verbose_name=_("Form data"))
    page = models.ForeignKey(Page, on_delete=models.CASCADE)

    submit_time = models.DateTimeField(verbose_name=_("Submit time"), auto_now_add=True)

    @property
    def is_indexable(self):
        return False

    class Meta:
        verbose_name = _("form submission")
        verbose_name_plural = _("form submissions")

    @staticmethod
    def _set_value(field, value):
        if field.block_type in ("radiobutton", "checkbox"):
            value = "TAK" if value == field.value["value"] else ""
        else:
            value = value if value else ""

        result = {field.value["label"]: value}
        return result

    def get_data(self):
        output = {}
        formsets = Formset.objects.filter(page=self.page)
        for question in formsets:
            result = self.form_data.get(str(question.ident), None)
            answers = {}

            radiobutton_was_selected = any(
                field.value["value"] == result for field in question.fields if field.block_type == "radiobutton"
            )

            for idx, field in enumerate(question.fields):
                if field.block_type in ("singlelinetextinput", "multilinetextinput"):
                    answers = result if result else ""
                    break

                update_answer = True

                if isinstance(result, dict):
                    update_answer = False
                    answers.update(self._set_value(field, result.get(field.id)))

                elif isinstance(result, list):
                    update_answer = False
                    try:
                        answers.update(self._set_value(field, result[idx]))
                    except IndexError:
                        answers.update(self._set_value(field, None))

                if update_answer:
                    if field.block_type in ("checkbox", "radiobutton"):
                        val = result if result == field.value["value"] else None
                    else:
                        val = None if radiobutton_was_selected else result
                    answers.update(self._set_value(field, val))

            output[question.title] = answers

        return output


class FormPage(BasePage):
    base_form_class = FormPageForm

    intro = RichTextField(blank=True)
    thank_you_text = RichTextField(
        blank=True,
        help_text="Komunikat, który zostanie wyświetlony po zakończeniu ankiety.",
        verbose_name="Tekst po zakończeniu",
    )
    intro_en = RichTextField(blank=True, null=True)
    thank_you_text_en = RichTextField(blank=True, null=True)
    to_address = models.CharField(
        verbose_name=_("to address"),
        max_length=255,
        blank=True,
        help_text=_("Optional - form submissions will be emailed to these addresses. Separate multiple addresses by comma."),
    )
    from_address = models.CharField(verbose_name=_("from address"), max_length=255, blank=True)
    subject = models.CharField(verbose_name=_("subject"), max_length=255, blank=True)

    parent_page_types = [
        "cms.FormPageIndex",
    ]

    subpage_types = []

    i18n_fields = BasePage.i18n_fields + ["intro", "thank_you_text", "formsets"]

    api_fields = BasePage.api_fields + [
        APIField("intro", serializer=CharField(source="intro_i18n")),
        APIField("thank_you_text", serializer=CharField(source="thank_you_text_i18n")),
        APIField("formsets"),
        APIField(
            "formsets",
            serializer=APIFormsetField(source="formsets_i18n", many=True, read_only=True),
        ),
    ]

    content_panels_pl = BasePage.content_panels + [
        FieldPanel(
            "intro",
            classname="full",
            heading="Wstęp",
            help_text="Opis formularza lub ankiety.",
        ),
        InlinePanel("formsets", label="Pole formularza"),
        FieldPanel(
            "thank_you_text",
            classname="full",
            heading="Tekst po wypełnieniu",
            help_text="Komunikat, który zostanie wyświetlony po zakończeniu ankiety.",
        ),
    ]

    content_panels_en = BasePage.content_panels_en + [
        FieldPanel(
            "intro_en",
            classname="full",
            heading="Wstęp",
            help_text="Opis formularza lub ankiety.",
        ),
        InlinePanel("formsets_en", label="Pole formularza"),
        FieldPanel(
            "thank_you_text_en",
            classname="full",
            heading="Tekst po wypełnieniu",
            help_text="Komunikat, który zostanie wyświetlony po zakończeniu ankiety.",
        ),
    ]

    settings_panels = [
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel(
                            "from_address",
                            classname="col6",
                            heading="Adres email nadawcy",
                            help_text='Adres email, który będzie widoczny w polu "Od" powiadomienia.',
                        ),
                        FieldPanel(
                            "to_address",
                            classname="col6",
                            heading="Adres email adresata",
                            help_text="Adres email, pod który powiadomienie ma zostać wysłane.",
                        ),
                    ]
                ),
                FieldPanel(
                    "subject",
                    heading="Tytuł powiadomienia",
                    help_text="Tekst, który będzie widoczny w tytule powiadomienia.",
                ),
            ],
            "Ustawienia powiadomień email dla formularza",
        ),
        PublishingPanel(),
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("show_in_menus"),
            ],
            "Ustawienia strony",
        ),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels_pl, heading="Formularz (PL)"),
            ObjectList(content_panels_en, heading="Formularz (EN)"),
            ObjectList(BasePage.seo_panels_pl, heading="Promocja (PL)"),
            ObjectList(BasePage.seo_panels_en, heading="Promocja (EN)"),
            ObjectList(settings_panels, heading="Ustawienia", classname="settings"),
        ]
    )

    def save_post(self, request):
        if request.content_type == "application/json":
            if request.data:
                FormPageSubmission.objects.create(form_data=request.data, page=self)
            return Response(200)

        raise UnsupportedMediaType(request.content_type)

    class Meta:
        verbose_name = "Formularz lub ankieta"
        verbose_name_plural = "Formularze lub ankiety"

    def get_copyable_fields(self):
        return super().get_copyable_fields() + ["intro", "thank_you_text"]
