from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.utils import ErrorList
from django.utils.functional import cached_property
from wagtail.core import blocks
from wagtail.core.blocks.struct_block import StructBlockValidationError
from wagtail.documents.blocks import DocumentChooserBlock as WagtailDocumentChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock as WagtailImageChooserBlock
from wagtailvideos.blocks import VideoChooserBlock

from mcod.cms.widgets import ColorPickerWidget

CMS_RICH_TEXT_FIELD_MORE_FEATURES = settings.CMS_RICH_TEXT_FIELD_FEATURES + [
    "embed",
    "document-link",
    "image",
    "br",
    "hr",
]


class ImageChooserBlock(WagtailImageChooserBlock):
    def get_api_representation(self, value, context=None):
        if value is None:
            return None
        else:
            download_url = "{}{}".format(settings.CMS_URL, value.file.url)
            return {
                "title": value.title,
                "alt": value.alt_i18n,
                "width": value.width,
                "height": value.height,
                "download_url": download_url,
            }

    class Meta:
        icon = "image"
        form_classname = "struct-block image-block"


class DocumentChooserBlock(WagtailDocumentChooserBlock):
    def __init__(self, limit_choices_to=None, validators=(), **kwargs):
        self._limit_choices_to = limit_choices_to or None
        super().__init__(validators=validators, **kwargs)

    def get_queryset(self):
        return self.target_model.objects.all()

    def get_api_representation(self, value, context=None):
        if value is None:
            return None
        else:
            download_url = "{}{}".format(settings.CMS_URL, value.file.url)
            return {"title": value.title, "download_url": download_url}

    @cached_property
    def field(self):
        kwargs = {
            "queryset": self.get_queryset(),
            "widget": self.widget,
            "required": self._required,
            "validators": self._validators,
            "help_text": self._help_text,
        }
        if self._limit_choices_to:
            kwargs["limit_choices_to"] = self._limit_choices_to

        return forms.ModelChoiceField(**kwargs)

    class Meta:
        icon = "doc-empty"
        form_classname = "struct-block document-block"


class SvgDocumentChooserBlock(DocumentChooserBlock):
    def __init__(self, limit_choices_to=None, validators=(), **kwargs):
        limit_choices_to = limit_choices_to or Q(file__endswith=".svg")
        validators = validators or (lambda val: val.file.name.endswith(".svg"),)
        super().__init__(limit_choices_to=limit_choices_to, validators=validators, **kwargs)

    def get_queryset(self):
        return self.target_model.objects.filter(file__endswith=".svg")

    class Meta:
        icon = "fa-object-group"
        form_classname = "struct-block svg-document-block"


class ColorPickerBlock(blocks.FieldBlock):
    def __init__(self, required=True, **kwargs):
        self.field = forms.CharField(required=required, max_length=7, widget=ColorPickerWidget)
        super().__init__(**kwargs)


class AlignChoiceBlock(blocks.ChoiceBlock):
    choices = [
        ("left", "od lewej"),
        ("center", "na środku"),
        ("right", "od prawej"),
    ]


class ButtonSizeChoiceBlock(blocks.ChoiceBlock):
    choices = (("btn-normal", "Normalny"), ("btn-sm", "Mały"), ("btn-lg", "Duży"))


class ButtonStyleChoiceBlock(blocks.ChoiceBlock):
    choices = (
        ("btn-primary", "Niebieski"),
        ("btn-secondary", "Szary"),
        ("btn-success", "Zielony"),
        ("btn-danger", "Czerwony"),
        ("btn-warning", "Żółty"),
        ("btn-info", "Turkusowy"),
        ("btn-light", "Jasny"),
        ("btn-dark", "Ciemny"),
        ("btn-link", "Link"),
    )


class LinkTargetChoiceBlock(blocks.ChoiceBlock):
    choices = (("_self", "To samo okno"), ("_blank", "Nowe okno"))


class HeaderChoiceBlock(blocks.ChoiceBlock):
    choices = (
        ("h2", "H2"),
        ("h3", "H3"),
        ("h4", "H4"),
        ("h5", "H5"),
        ("h6", "H6"),
    )


class HeaderBlock(blocks.StructBlock):
    size = HeaderChoiceBlock(label="Rozmiar", help_text="Rozmiar nagłówka.")
    title = blocks.CharBlock(
        label="Tytuł",
        max_length=50,
        help_text="Tekst nagłówka.",
    )

    class Meta:
        icon = "title"


class UploadedVideoChooserBlock(VideoChooserBlock):

    def get_api_representation(self, value, context=None):
        return (
            {
                "title": value.title,
                "download_url": "{}{}".format(settings.CMS_URL, value.file.url),
                "thumbnail_url": "{}{}".format(settings.CMS_URL, value.thumbnail.url),
            }
            if value
            else None
        )


class VideoBlock(blocks.StructBlock):

    video = EmbedBlock(
        required=False,
        label="Wideo",
        help_text="Wklej adres URL do wideo, na przykład: https://www.youtube.com/watch?v=jVAYxah_RP8",
    )
    caption = blocks.TextBlock(
        rows=2,
        max_length=60,
        required=False,
        label="Podpis",
        help_text="Opcjonalny podpis filmu, dwie linie, maksymalnie 60 znaków.",
    )

    uploaded_video = UploadedVideoChooserBlock(
        required=False,
        label="Przesłane wideo",
        help_text="Wybierz plik wideo załadowany poprzez" " panel administracyjny CMS",
    )

    def clean(self, value):
        cleaned_data = super().clean(value)
        error = None
        if not cleaned_data["video"] and not cleaned_data.get("uploaded_video"):
            error = ValidationError("Należy uzupełnić jedno z pól.")
        elif cleaned_data["video"] and cleaned_data.get("uploaded_video"):
            error = ValidationError("Należy uzupełnić tylko jedno z pól.")
        if error:
            raise StructBlockValidationError({"video": ErrorList([error]), "uploaded_video": ErrorList([error])})
        return cleaned_data

    class Meta:
        icon = "media"
        form_classname = "struct-block video-block"


class RichTextBlock(blocks.RichTextBlock):
    class Meta:
        form_classname = "struct-block rich-text-block"


class RawHTMLBlock(blocks.RawHTMLBlock):
    class Meta:
        form_classname = "struct-block raw-html-block"


class BannerBlock(blocks.StructBlock):
    image = ImageChooserBlock(
        required=True,
        label="Obrazek",
        help_text="""
                                Obrazek bannera. Zalecany rozmiar: 1920 x 340 pikseli.
                                """,
    )
    action_url = blocks.URLBlock(
        label="Adres URL",
        help_text="Strona, na którą zostanie przekierowany " "użytkownik po naciśnięciu na baner.",
        required=True,
    )
    target = LinkTargetChoiceBlock(
        label="Cel",
        help_text='Cel określa, czy strona w polu "Adres URL" ' "ma się otwierać w tym samym, czy też w nowym oknie.",
        default="_self",
        required=False,
    )

    class Meta:
        icon = "fa-link"
        form_classname = "struct-block banner-block"


class CTAImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(
        label="Obrazek",
        required=False,
        help_text="Obrazek, który będzie wyświetlany obok " "tekstu. Zalecany rozmiar: 1920 x 340 pikseli.",
    )
    position = AlignChoiceBlock(
        default="left",
        label="Położenie",
        required=False,
        help_text="""
                                Położenie obrazka względem tytułu oraz tekstu.
                                """,
    )


class CTABackgroundBlock(blocks.StructBlock):
    image = ImageChooserBlock(
        label="Obraz w tle",
        required=False,
        help_text="Obraz tła może być również animowanym gifem. " "Zalecany rozmiar: 1920 x 340 pikseli.",
    )
    color = ColorPickerBlock(
        default="#ffffff",
        label="Kolor tła",
        required=False,
        help_text="Kolor tła będzie zawsze pod spodem wszystkich " "innych elementów bloku (w tym również obrazu tła).",
    )
    paralax = blocks.BooleanBlock(
        default=False,
        required=False,
        label="Efekt paralaksy",
        help_text="Przy włączonym efekcie paralaksy tło przewija "
        "się wolniej niż pozostałe elementy strony, co tworzy wrażenie głębi.",
    )

    class Meta:
        form_classname = "struct-block cta-background-block"


class CTAButtonBlock(blocks.StructBlock):
    text = blocks.CharBlock(
        label="Tekst na przycisku",
        help_text="Maksymalnie 20 znaków.",
        max_length=20,
        required=True,
    )
    position = AlignChoiceBlock(label="Położenie", default="left", required=False)
    size = ButtonSizeChoiceBlock(label="Rozmiar", default="btn-normal", required=False)
    style = ButtonStyleChoiceBlock(label="Styl", default="btn-primary", required=False)
    action_url = blocks.URLBlock(
        label="Adres URL",
        help_text="Strona, na którą zostanie przekierowany " "użytkownik po naciśnięciu przycisku.",
        required=True,
    )
    target = LinkTargetChoiceBlock(
        label="Cel",
        help_text='Cel określa, czy strona w polu "Adres URL" ' "ma się otwierać w tym samym, czy też w nowym oknie.",
        default="_self",
        required=False,
    )

    class Meta:
        form_classname = "struct-block cta-button-block"


class CTAHeaderBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=20, required=False, label="Tytuł", help_text="Maksymalnie 20 znaków.")
    align = AlignChoiceBlock(
        default="left",
        label="Wyrównanie",
        help_text="""
                                    Określa położenie tekstu w bloku.
                                    """,
    )

    class Meta:
        form_classname = "struct-block cta-header-block"


class CTATextBlock(blocks.StructBlock):
    text = blocks.TextBlock(
        max_length=200,
        rows=4,
        required=False,
        label="Tekst",
        help_text="Treść tekstu wyświetlanego pod tytułem. Maksymalnie 4 linie, 200 znaków.",
    )
    align = AlignChoiceBlock(
        default="left",
        required=False,
        label="Wyrównanie",
        help_text="Określa położenie tekstu w bloku.",
    )

    class Meta:
        form_classname = "struct-block cta-text-block"


class CTABlock(blocks.StructBlock):
    background = CTABackgroundBlock(label="Tło bloku")
    image = CTAImageBlock(label="Obraz obok tekstu")
    header = CTAHeaderBlock(label="Tytuł")
    text = CTATextBlock(label="Tekst pod tytułem")
    button = CTAButtonBlock(
        label="Przycisk",
    )

    class Meta:
        icon = "form"
        form_classname = "struct-block cta-block"


class CarouselBlock(blocks.StreamBlock):
    cta = CTABlock(required=False, label="Call To Action")
    banner = BannerBlock(label="Baner reklamowy", required=False)
    video = VideoBlock(label="Film", required=False)
    text = RichTextBlock(label="Tekst sformatowany", required=False)
    raw_html = RawHTMLBlock(label="Kod HTML", required=False)
    svg = SvgDocumentChooserBlock(label="Obraz SVG", required=False)
    image = ImageChooserBlock(label="Obrazek", required=False)

    class Meta:
        form_classname = "struct-block carousel-block"


class CarouselBlockWithAdditionalTextTools(CarouselBlock):
    text = RichTextBlock(
        label="Tekst sformatowany",
        required=False,
        features=CMS_RICH_TEXT_FIELD_MORE_FEATURES,
    )
