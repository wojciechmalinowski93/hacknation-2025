from django.utils.html import escape
from draftjs_exporter.dom import DOM
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    ExternalLinkElementHandler,
    PageLinkElementHandler,
)
from wagtail.core.models import Page
from wagtail.core.rich_text import LinkHandler
from wagtail.core.rich_text.pages import PageLinkHandler


class TitledLinkHandler(LinkHandler):
    identifier = "external"

    @classmethod
    def expand_db_attributes(cls, attrs):
        href = attrs["href"]
        title = attrs.get("title", "")
        link_attrs = f'href="{escape(href)}" '
        if title:
            link_attrs += f'title="{title}" '
        return f"<a {link_attrs}>"


class TitledPageLinkHandler(PageLinkHandler):

    @classmethod
    def expand_db_attributes(cls, attrs):
        try:
            page = cls.get_instance(attrs)
            title = attrs.get("title", "")
            return '<a href="{}" title="{}">'.format(escape(page.specific.url), title)
        except Page.DoesNotExist:
            return "<a>"


class TitledExternalLinkElementHandler(ExternalLinkElementHandler):

    def get_attribute_data(self, attrs):
        attrs_data = super().get_attribute_data(attrs)
        attrs_data["link_title"] = attrs.get("title", "")
        return attrs_data


def titled_link_entity(props):
    """
    <a linktype="page" id="1">internal page link</a>
    """
    id_ = props.get("id")
    link_props = {"title": props.get("link_title", "")}
    if id_ is not None:
        link_props["linktype"] = "page"
        link_props["id"] = id_
    else:
        link_props["href"] = props.get("url")

    return DOM.create_element("a", link_props, props["children"])


class TitledPageLinkElementHandler(PageLinkElementHandler):

    def get_attribute_data(self, attrs):
        try:
            page = Page.objects.get(id=attrs["id"]).specific
        except Page.DoesNotExist:
            # retain ID so that it's still identified as a page link (albeit a broken one)
            return {
                "id": int(attrs["id"]),
                "url": None,
                "parentId": None,
                "link_title": None,
            }

        parent_page = page.get_parent()

        return {
            "id": page.id,
            "url": page.url,
            "parentId": parent_page.id if parent_page else None,
            "link_title": attrs.get("title", ""),
        }
