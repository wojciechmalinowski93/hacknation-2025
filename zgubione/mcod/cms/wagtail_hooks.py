from django.conf.urls import include, url
from django.forms.utils import flatatt
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from wagtail.admin.menu import MenuItem
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.admin.rich_text.editors.draftail import features as draftail_features
from wagtail.admin.widgets import Button, ButtonWithDropdownFromHook, PageListingButton
from wagtail.core import hooks

from mcod.cms.handlers import (
    TitledExternalLinkElementHandler,
    TitledLinkHandler,
    TitledPageLinkElementHandler,
    TitledPageLinkHandler,
    titled_link_entity,
)
from mcod.cms.urls import chooser_urls, form_urls
from mcod.cms.utils import get_forms_for_user, to_i18n_url

CUSTOM_STYLESHEETS = [
    "cms/custom.css",
]
#
CUSTOM_SCRIPTS = ["cms/custom.js"]

hooks._hooks["register_page_listing_buttons"] = []


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        url(r"^forms/", include(form_urls)),
    ] + chooser_urls


class FormsMenuItem(MenuItem):
    def is_shown(self, request):
        return get_forms_for_user(request.user).exists()


@hooks.register("register_admin_menu_item")
def register_forms_menu_item():
    return FormsMenuItem(
        _("Ankiety"),
        reverse("cms_forms_index"),
        name="forms",
        classnames="icon icon-form",
        order=700,
    )


class ExtButtonWithDropdownFromHook(ButtonWithDropdownFromHook):
    template_name = "wagtailadmin/buttons/dropdown_with_hook.html"


class DropdownLink(Button):
    def __init__(self, label, url, classes=None, attrs=None, priority=1000):
        self.label = label
        self.url = url
        self.classes = classes or set()
        self.attrs = attrs or {}
        self.priority = priority

    def render(self):
        self.attrs["href"] = self.url
        return format_html("<a {}>{}</a>".format(flatatt(self.attrs), self.label))


@hooks.register("register_page_listing_buttons")
def page_listing_buttons(page, page_perms, is_parent=False, next_url=None):
    if page_perms.can_edit():
        yield PageListingButton(
            _("Edit"),
            reverse("wagtailadmin_pages:edit", args=[page.id]),
            attrs={"aria-label": _("Edit '%(title)s'") % {"title": page.get_admin_display_title()}},
            priority=10,
        )
    if page.has_unpublished_changes:
        yield ExtButtonWithDropdownFromHook(
            _("View draft"),
            hook_name="register_page_listing_preview_draft_buttons",
            page=page,
            page_perms=page_perms,
            is_parent=is_parent,
            attrs={
                "aria-label": _("Preview draft version of '%(title)s'") % {"title": page.get_admin_display_title()},
                "target": "_blank",
                "rel": "noopener noreferrer",
            },
            priority=20,
        )
    if page.live and page.url:
        yield ExtButtonWithDropdownFromHook(
            _("View live"),
            hook_name="register_page_listing_preview_buttons",
            page=page,
            page_perms=page_perms,
            is_parent=is_parent,
            attrs={
                "target": "_blank",
                "rel": "noopener noreferrer",
                "aria-label": _("View live version of '%(title)s'") % {"title": page.get_admin_display_title()},
            },
            priority=30,
        )
    if page_perms.can_add_subpage():
        if is_parent:
            yield Button(
                _("Add child page"),
                reverse("wagtailadmin_pages:add_subpage", args=[page.id]),
                attrs={
                    "aria-label": _("Add a child page to '%(title)s' ") % {"title": page.get_admin_display_title()},
                },
                classes={
                    "button",
                    "button-small",
                    "bicolor",
                    "icon",
                    "white",
                    "icon-plus",
                },
                priority=40,
            )
        else:
            yield PageListingButton(
                _("Add child page"),
                reverse("wagtailadmin_pages:add_subpage", args=[page.id]),
                attrs={"aria-label": _("Add a child page to '%(title)s' ") % {"title": page.get_admin_display_title()}},
                priority=40,
            )

    yield ButtonWithDropdownFromHook(
        _("More"),
        hook_name="register_page_listing_more_buttons",
        page=page,
        page_perms=page_perms,
        is_parent=is_parent,
        next_url=next_url,
        attrs={
            "target": "_blank",
            "rel": "noopener noreferrer",
            "title": _("View more options for '%(title)s'") % {"title": page.get_admin_display_title()},
        },
        priority=50,
    )


@hooks.register("register_page_listing_preview_draft_buttons")
def page_listing_preview_draft_buttons(page, page_perms, is_parent=False, next_url=None):
    if page.has_unpublished_changes:
        if not page.url:
            rev = page.revisions.order_by("id").first()
            page = rev.as_page_object()

        if page.url:
            yield Button(
                _("Polish"),
                to_i18n_url(page.full_url, "pl") + "?rev=latest&lang=pl",
                attrs={
                    "aria-label": _("Preview draft version of '%(title)s'") % {"title": page.get_admin_display_title()},
                    "target": "_blank",
                    "rel": "noopener noreferrer",
                },
                priority=20,
            )
            yield Button(
                _("English"),
                to_i18n_url(page.full_url, "en") + "?rev=latest&lang=en",
                attrs={
                    "aria-label": _("Preview draft version of '%(title)s'") % {"title": page.get_admin_display_title()},
                    "target": "_blank",
                    "rel": "noopener noreferrer",
                },
                priority=30,
            )


@hooks.register("register_page_listing_preview_buttons")
def page_listing_preview_buttons(page, page_perms, is_parent=False, next_url=None):
    if page.live and page.url:
        yield Button(
            _("Polish"),
            to_i18n_url(page.full_url, "pl") + "?lang=pl",
            attrs={
                "aria-label": _("View live version of '%(title)s'") % {"title": page.get_admin_display_title()},
                "target": "_blank",
                "rel": "noopener noreferrer",
            },
            priority=20,
        )
        yield Button(
            _("English"),
            to_i18n_url(page.full_url, "en") + "?lang=en",
            attrs={
                "aria-label": _("View live version of '%(title)s'") % {"title": page.get_admin_display_title()},
                "target": "_blank",
                "rel": "noopener noreferrer",
            },
            priority=30,
        )


@hooks.register("insert_global_admin_css", order=100)
def global_admin_css():
    return format_html_join(
        "\n",
        '<link rel="stylesheet" href="{}">',
        ((static(css),) for css in CUSTOM_STYLESHEETS),
    )


@hooks.register("insert_global_admin_js", order=100)
def global_admin_js():
    return format_html_join("\n", '<script src="{}"></script>', ((static(js),) for js in CUSTOM_SCRIPTS))


@hooks.register("construct_document_chooser_queryset")
def show_my_uploaded_documents_only(documents, request):
    documents = documents.filter(uploaded_by_user=request.user)

    return documents


@hooks.register("register_rich_text_features")
def register_lang_en_feature(features):
    languages = {"en": "Angielski", "pl": "Polski"}
    for lang_code, lang_name in languages.items():
        feature_name = f"lang-{lang_code}"
        type_ = f"LANG-{lang_code.upper()}"

        features.register_editor_plugin(
            "draftail",
            feature_name,
            draftail_features.InlineStyleFeature(
                {
                    "type": type_,
                    "label": f"{lang_code.upper()}",
                    "description": lang_name,
                    "style": {"fontStyle": "italic"},
                }
            ),
        )
        features.register_converter_rule(
            "contentstate",
            feature_name,
            {
                "from_database_format": {f"span[lang={lang_code}]": InlineStyleElementHandler(type_)},
                "to_database_format": {
                    "style_map": {
                        type_: {
                            "element": "span",
                            "props": {"dir": "ltr", "lang": lang_code},
                        }
                    }
                },
            },
        )

        features.default_features.append(feature_name)


@hooks.register("register_rich_text_features")
def register_external_link(features):
    features.default_features.append("titled_link")
    features.register_link_type(TitledLinkHandler)
    features.register_link_type(TitledPageLinkHandler)

    features.register_editor_plugin(
        "draftail",
        "titled_link",
        draftail_features.EntityFeature(
            {
                "type": "TITLED_LINK",
                "icon": "link",
                "description": "Link",
                # We want to enforce constraints on which links can be pasted into rich text.
                # Keep only the attributes Wagtail needs.
                "attributes": ["url", "id", "parentId", "link_title"],
                "whitelist": {
                    # Keep pasted links with http/https protocol, and not-pasted links (href = undefined).
                    "href": "^(http:|https:|undefined$)",
                    "title": "^.*",
                },
            },
            js=["cms/titled_link.js", "cms/page-chooser-modal.js"],
        ),
    )
    features.register_converter_rule(
        "contentstate",
        "titled_link",
        {
            "from_database_format": {
                "a[href]": TitledExternalLinkElementHandler("TITLED_LINK"),
                'a[linktype="page"]': TitledPageLinkElementHandler("TITLED_LINK"),
            },
            "to_database_format": {"entity_decorators": {"TITLED_LINK": titled_link_entity}},
        },
    )


@hooks.register("register_rich_text_features")
def register_mail_link(features):
    feature_name = "email-link"
    features.register_editor_plugin(
        "draftail",
        feature_name,
        draftail_features.EntityFeature(
            {
                "type": "EMAIL_LINK",
                "icon": "mail",
                "description": "Email",
                # We want to enforce constraints on which links can be pasted into rich text.
                # Keep only the attributes Wagtail needs.
                "attributes": ["url", "id", "parentId", "link_title"],
                "whitelist": {
                    # Keep pasted links with http/https protocol, and not-pasted links (href = undefined).
                    "href": "^(http:|https:|undefined$)",
                    "title": "^.*",
                },
            },
            js=["cms/titled_link.js", "cms/page-chooser-modal.js"],
        ),
    )
    features.register_converter_rule(
        "contentstate",
        feature_name,
        {
            "from_database_format": {
                "a[href]": TitledExternalLinkElementHandler("TITLED_LINK"),
                'a[linktype="page"]': TitledPageLinkElementHandler("TITLED_LINK"),
            },
            "to_database_format": {"entity_decorators": {"EMAIL_LINK": titled_link_entity}},
        },
    )
