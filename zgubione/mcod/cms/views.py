import io
from collections import OrderedDict

import pytz
import xlsxwriter
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import datetime
from django.utils.translation import ungettext
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from wagtail.admin import messages
from wagtail.admin.auth import user_has_any_page_permission, user_passes_test
from wagtail.admin.forms.search import SearchForm
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.admin.views.chooser import can_choose_page, page_models_from_string, shared_context
from wagtail.contrib.forms.views import SafePaginateListView
from wagtail.core import hooks
from wagtail.core.forms import PasswordViewRestrictionForm
from wagtail.core.models import Page, PageViewRestriction, UserPagePermissionsProxy
from wagtail.core.url_routing import RouteResult

from mcod.cms.forms import (
    SelectDateForm,
    TitleChooserForm,
    TitledAnchorLinkChooserForm,
    TitledEmailLinkChooserForm,
    TitledExternalLinkChooserForm,
    TitledPhoneLinkChooserForm,
)
from mcod.cms.models import FormPageSubmission
from mcod.cms.utils import filter_page_type, get_forms_for_user

warsaw_timezone = pytz.timezone("Europe/Warsaw")


@csrf_exempt
def serve(request, path):
    if not request.site:
        raise Http404

    if request.method == "GET":
        root_url = request.site.root_url
        return redirect(f"{root_url}/{path}")

    page = Page.objects.get(url_path=f"/{path}")
    if page.live:
        page, args, kwargs = RouteResult(page)
    else:
        raise Http404

    for fn in hooks.get_hooks("before_serve_page"):
        result = fn(page, request, args, kwargs)
        if isinstance(result, HttpResponse):
            return result

    return page.specific.serve(request, *args, **kwargs)


@require_http_methods(["POST"])
@user_passes_test(lambda user: user.is_superuser and user.is_active)
def copy_pl_to_en(request, page_id):
    page = get_object_or_404(Page, id=page_id).specific
    copyable_fields = page.get_copyable_fields()
    latest_revision = page.get_latest_revision_as_page()
    for field_name in copyable_fields:
        field_name_en = f"{field_name}_en"
        latest_revision_pl_attr = getattr(latest_revision, field_name)
        setattr(page, field_name_en, latest_revision_pl_attr)
        setattr(page, field_name, latest_revision_pl_attr)

    page.save_revision()
    return JsonResponse({"success": True})


def authenticate_with_password(request, page_view_restriction_id, page_id):
    restriction = get_object_or_404(PageViewRestriction, id=page_view_restriction_id)
    page = get_object_or_404(Page, id=page_id).specific

    if request.method == "POST":
        form = PasswordViewRestrictionForm(request.POST, instance=restriction)
        if form.is_valid():
            restriction.mark_as_passed(request)

            return redirect(form.cleaned_data["return_url"])
    else:
        form = PasswordViewRestrictionForm(instance=restriction)

    action_url = reverse("wagtailcore_authenticate_with_password", args=[restriction.id, page.id])
    return page.serve_password_required_response(request, form, action_url)


@user_passes_test(user_has_any_page_permission)
def revisions_view(request, page_id, revision_id):
    page = get_object_or_404(Page, id=page_id).specific

    perms = page.permissions_for_user(request.user)
    if not (perms.can_publish() or perms.can_edit()):
        raise PermissionDenied

    revision = get_object_or_404(page.revisions, id=revision_id)
    revision_page = revision.as_page_object()

    extra = {"revision_id": revision.id}

    return revision_page.make_preview_request(request, page.default_preview_mode, extra_request_attrs=extra)


class SubmissionsListView(SafePaginateListView):
    template_name = "wagtailadmin/forms/index_submissions.html"
    context_object_name = "submissions"
    form_page = None
    ordering = ("-submit_time",)
    ordering_xls = ("submit_time",)
    orderable_fields = (
        "id",
        "submit_time",
    )
    select_date_form = None

    def dispatch(self, request, *args, **kwargs):
        self.form_page = kwargs.get("form_page")

        if not get_forms_for_user(request.user).filter(pk=self.form_page.id).exists():
            raise PermissionDenied

        self.is_xls_export = self.request.GET.get("action") == "XLS"
        if self.is_xls_export:
            self.paginate_by = None

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = FormPageSubmission._default_manager.filter(page=self.form_page)

        filtering = self.get_filtering()
        if filtering and isinstance(filtering, dict):
            queryset = queryset.filter(**filtering)

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    def get_paginate_by(self, queryset):
        if self.is_xls_export:
            return None
        return self.paginate_by

    def get_validated_ordering(self):
        orderable_fields = self.orderable_fields or ()
        ordering = dict()
        if self.is_xls_export:
            default_ordering = self.ordering_xls or ()
        else:
            default_ordering = self.ordering or ()
        if isinstance(default_ordering, str):
            default_ordering = (default_ordering,)
        ordering_strs = self.request.GET.getlist("order_by") or list(default_ordering)
        for order in ordering_strs:
            try:
                _, prefix, field_name = order.rpartition("-")
                if field_name in orderable_fields:
                    ordering[field_name] = (
                        prefix,
                        "descending" if prefix == "-" else "ascending",
                    )
            except (IndexError, ValueError):
                continue
        return ordering

    def get_ordering(self):
        """Return the field or fields to use for ordering the queryset"""
        ordering = self.get_validated_ordering()
        return [values[0] + name for name, values in ordering.items()]

    def get_filtering(self):
        """Return filering as a dict for submissions queryset"""
        self.select_date_form = SelectDateForm(self.request.GET)
        result = dict()
        if self.select_date_form.is_valid():
            date_from = self.select_date_form.cleaned_data.get("date_from")
            date_to = self.select_date_form.cleaned_data.get("date_to")
            if date_to:
                date_to += datetime.timedelta(days=1)
                if date_from:
                    result["submit_time__range"] = [date_from, date_to]
                else:
                    result["submit_time__lte"] = date_to
            elif date_from:
                result["submit_time__gte"] = date_from
        return result

    def get_xls_filename(self):
        return "wyniki-{}-{}.xls".format(self.form_page.slug, datetime.today().strftime("%Y-%m-%d"))

    def get_xls_response(self, context):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        workbook.set_properties(
            {
                "title": 'Wyniki dla ankiety "{}"'.format(self.form_page.title),
                "subject": "Ankiety na portalu dane.gov.pl",
                "author": "System MCOD",
                "company": "Ministerstwo Cyfryzacji",
            }
        )

        q_hdr_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#007d7e",
                "border": 1,
                "font_size": 13,
                "font_color": "#FFFFFF",
            }
        )

        date_hdr_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#007d7e",
                "border": 1,
                "font_size": 13,
                "font_color": "#FFFFFF",
            }
        )

        date_format = workbook.add_format(
            {
                "num_format": "dd/mm/yy hh:mm:ss",
                "align": "center",
                "valign": "center",
                "left": 1,
                "right": 1,
            }
        )

        worksheet = workbook.add_worksheet("Odpowiedzi")

        worksheet.set_tab_color("red")

        worksheet.freeze_panes(1, 0)
        worksheet.freeze_panes(2, 0)

        worksheet.set_header('Wyniki dla ankiety "{}"'.format(self.form_page.title))
        worksheet.set_column(0, 0, 20)

        _col = 1
        for q_header, subheaders in context["data_headings"].items():
            if len(subheaders) == 1:
                worksheet.write(0, _col, q_header, q_hdr_format)
                _min_cell_size = len(q_header) + 5
            else:
                worksheet.merge_range(
                    0,
                    _col,
                    0,
                    _col + len(subheaders) - 1,
                    q_header,
                    cell_format=q_hdr_format,
                )
                _min_cell_size = 0

            for idx, item in enumerate(subheaders):
                col_style = {
                    "bottom": 0,
                    "top": 0,
                    "left": 0,
                    "right": 0,
                    "valign": "center",
                    "text_wrap": True,
                    "shrink": True,
                    "font_size": 9,
                }
                if idx == 0:
                    col_style["left"] = 1
                if idx == len(subheaders) - 1:
                    col_style["right"] = 1

                cell_size = max(len(item) + 5, _min_cell_size)

                worksheet.set_column(_col, _col, cell_size, cell_format=workbook.add_format(col_style))
                header_style = {
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#007d7e",
                    "font_color": "#FFFFFF",
                }
                header_style.update(col_style)
                header_style["font_size"] = 11
                worksheet.write(1, _col, item, workbook.add_format(header_style))
                _col += 1

        worksheet.merge_range("A1:A2", "Data", cell_format=date_hdr_format)

        for idx, data in enumerate(context["data_rows"]):
            row_no = idx + 2
            submit_date = data["submission_time"].astimezone(warsaw_timezone).replace(tzinfo=None)
            worksheet.write_datetime(row_no, 0, submit_date, date_format)
            row_data = data["submission_data"]
            for _idx, cell in enumerate(row_data):
                worksheet.write(row_no, _idx + 1, cell)

        workbook.close()
        output.seek(0)

        filename = self.get_xls_filename()
        response = HttpResponse(
            output,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment;filename={}".format(filename)

        return response

    def render_to_response(self, context, **response_kwargs):
        if self.is_xls_export:
            return self.get_xls_response(context)
        return super().render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        """Return context for view, handle CSV or normal output"""
        context = super().get_context_data(**kwargs)
        submissions = context[self.context_object_name]

        data_rows = []
        formsets = self.form_page.specific.formsets.all()
        headers = OrderedDict()
        for formset in formsets:
            labels = [field.value["label"] for field in formset.fields]
            headers[formset.title] = labels

        for submission in submissions:
            form_data = submission.get_data()
            data_row = []
            for header, subheaders in headers.items():
                data = form_data[header]
                for subheader in subheaders:
                    data = form_data[header]
                    if isinstance(data, dict) and subheader:
                        data = data[subheader]
                    data_row.append(data)

            data_rows.append(
                {
                    "model_id": submission.id,
                    "submission_data": data_row,
                    "submission_time": submission.submit_time,
                }
            )

        context.update(
            {
                "form_page": self.form_page,
                "select_date_form": self.select_date_form,
                "data_headings": headers,
                "data_rows": data_rows,
                "submissions": submissions,
            }
        )

        page_obj = context.get("page_obj")
        paginator = context.get("paginator")
        if page_obj and paginator:
            context["start_index"] = (page_obj.number - 1) * paginator.per_page

        return context


class FormPagesListView(SafePaginateListView):
    template_name = "wagtailadmin/forms/index.html"
    context_object_name = "form_pages"

    def get_queryset(self):
        queryset = get_forms_for_user(self.request.user)
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset


class DeleteSubmissionsView(TemplateView):
    template_name = "wagtailadmin/forms/confirm_delete.html"
    page = None
    submissions = None
    success_url = "cms_forms_list_submissions"

    def get_queryset(self):
        submission_ids = self.request.GET.getlist("selected-submissions")
        return FormPageSubmission._default_manager.filter(id__in=submission_ids)

    def handle_delete(self, submissions):
        count = submissions.count()
        submissions.delete()
        messages.success(
            self.request,
            ungettext(
                "One submission has been deleted.",
                "%(count)d submissions have been deleted.",
                count,
            )
            % {"count": count},
        )

    def get_success_url(self):
        """Returns the success URL to redirect to after a successful deletion"""
        return self.success_url

    def dispatch(self, request, *args, **kwargs):
        """Check permissions, set the page and submissions, handle delete"""
        page_id = kwargs.get("page_id")

        if not get_forms_for_user(self.request.user).filter(id=page_id).exists():
            raise PermissionDenied

        self.page = get_object_or_404(Page, id=page_id).specific

        self.submissions = self.get_queryset()

        if self.request.method == "POST":
            self.handle_delete(self.submissions)
            return redirect(self.get_success_url(), page_id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Get the context for this view"""
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "page": self.page,
                "submissions": self.submissions,
            }
        )

        return context


def get_submissions_list_view(request, *args, **kwargs):
    page_id = kwargs.get("page_id")
    form_page = get_object_or_404(Page, id=page_id).specific
    view = SubmissionsListView.as_view()
    return view(request, form_page=form_page, *args, **kwargs)


def titled_external_link(request):
    initial_data = {
        "url": request.GET.get("link_url", ""),
        "link_text": request.GET.get("link_text", ""),
        "link_title": request.GET.get("link_title", ""),
    }

    if request.method == "POST":
        form = TitledExternalLinkChooserForm(request.POST, initial=initial_data, prefix="external-link-chooser")

        if form.is_valid():
            result = {
                "url": form.cleaned_data["url"],
                "title": form.cleaned_data["link_text"].strip() or form.cleaned_data["url"],
                "link_title": form.cleaned_data["link_title"],
                # If the user has explicitly entered / edited something in the link_text field,
                # always use that text. If not, we should favour keeping the existing link/selection
                # text, where applicable.
                # (Normally this will match the link_text passed in the URL here anyhow,
                # but that won't account for non-text content such as images.)
                "prefer_this_title_as_link_text": ("link_text" in form.changed_data),
            }

            return render_modal_workflow(
                request,
                None,
                None,
                None,
                json_data={"step": "external_link_chosen", "result": result},
            )
    else:
        form = TitledExternalLinkChooserForm(initial=initial_data, prefix="external-link-chooser")

    return render_modal_workflow(
        request,
        "wagtailadmin/chooser/titled_external_link.html",
        None,
        shared_context(
            request,
            {
                "form": form,
            },
        ),
        json_data={"step": "external_link"},
    )


def titled_browse(request, parent_page_id=None):
    # A missing or empty page_type parameter indicates 'all page types'
    # (i.e. descendants of wagtailcore.page)
    page_type_string = request.GET.get("page_type") or "wagtailcore.page"
    user_perm = request.GET.get("user_perms", False)
    link_title = request.GET.get("link_title", "")

    try:
        desired_classes = page_models_from_string(page_type_string)
    except (ValueError, LookupError):
        raise Http404

    # Find parent page
    if parent_page_id:
        parent_page = get_object_or_404(Page, id=parent_page_id)
    elif desired_classes == (Page,):
        # Just use the root page
        parent_page = Page.get_first_root_node()
    else:
        # Find the highest common ancestor for the specific classes passed in
        # In many cases, such as selecting an EventPage under an EventIndex,
        # this will help the administrator find their page quicker.
        all_desired_pages = filter_page_type(Page.objects.all(), desired_classes)
        parent_page = all_desired_pages.first_common_ancestor()

    parent_page = parent_page.specific

    # Get children of parent page
    pages = parent_page.get_children().specific()

    # allow hooks to modify the queryset
    for hook in hooks.get_hooks("construct_page_chooser_queryset"):
        pages = hook(pages, request)

    # Filter them by page type
    if desired_classes != (Page,):
        # restrict the page listing to just those pages that:
        # - are of the given content type (taking into account class inheritance)
        # - or can be navigated into (i.e. have children)
        choosable_pages = filter_page_type(pages, desired_classes)
        descendable_pages = pages.filter(numchild__gt=0)
        pages = choosable_pages | descendable_pages

    can_choose_root = request.GET.get("can_choose_root", False)

    # Do permission lookups for this user now, instead of for every page.
    permission_proxy = UserPagePermissionsProxy(request.user)

    # Parent page can be chosen if it is a instance of desired_classes
    parent_page.can_choose = can_choose_page(parent_page, permission_proxy, desired_classes, can_choose_root, user_perm)

    # Pagination
    # We apply pagination first so we don't need to walk the entire list
    # in the block below
    paginator = Paginator(pages, per_page=25)
    pages = paginator.get_page(request.GET.get("p"))

    # Annotate each page with can_choose/can_decend flags
    for page in pages:
        page.can_choose = can_choose_page(page, permission_proxy, desired_classes, can_choose_root, user_perm)
        page.can_descend = page.get_children_count()

    # Render
    context = shared_context(
        request,
        {
            "parent_page": parent_page,
            "parent_page_id": parent_page.pk,
            "pages": pages,
            "search_form": SearchForm(),
            "title_form": TitleChooserForm(initial={"link_title": link_title}),
            "page_type_string": page_type_string,
            "page_type_names": [desired_class.get_verbose_name() for desired_class in desired_classes],
            "page_types_restricted": (page_type_string != "wagtailcore.page"),
        },
    )

    return render_modal_workflow(
        request,
        "wagtailadmin/chooser/titled_browse.html",
        None,
        context,
        json_data={"step": "browse", "parent_page_id": context["parent_page_id"]},
    )


def titled_anchor_link(request):
    initial_data = {
        "link_text": request.GET.get("link_text", ""),
        "url": request.GET.get("link_url", ""),
        "link_title": request.GET.get("link_title", ""),
    }

    if request.method == "POST":
        form = TitledAnchorLinkChooserForm(request.POST, initial=initial_data, prefix="anchor-link-chooser")

        if form.is_valid():
            result = {
                "url": "#" + form.cleaned_data["url"],
                "title": form.cleaned_data["link_text"].strip() or form.cleaned_data["url"],
                "prefer_this_title_as_link_text": ("link_text" in form.changed_data),
                "link_title": form.cleaned_data["link_title"],
            }
            return render_modal_workflow(
                request,
                None,
                None,
                None,
                json_data={"step": "external_link_chosen", "result": result},
            )
    else:
        form = TitledAnchorLinkChooserForm(initial=initial_data, prefix="anchor-link-chooser")

    return render_modal_workflow(
        request,
        "wagtailadmin/chooser/titled_anchor_link.html",
        None,
        shared_context(
            request,
            {
                "form": form,
            },
        ),
        json_data={"step": "anchor_link"},
    )


def titled_email_link(request):
    initial_data = {
        "link_text": request.GET.get("link_text", ""),
        "email_address": request.GET.get("link_url", ""),
        "link_title": request.GET.get("link_title", ""),
    }

    if request.method == "POST":
        form = TitledEmailLinkChooserForm(request.POST, initial=initial_data, prefix="email-link-chooser")

        if form.is_valid():
            result = {
                "url": "mailto:" + form.cleaned_data["email_address"],
                "title": form.cleaned_data["link_text"].strip() or form.cleaned_data["email_address"],
                "link_title": form.cleaned_data["link_title"],
                # If the user has explicitly entered / edited something in the link_text field,
                # always use that text. If not, we should favour keeping the existing link/selection
                # text, where applicable.
                "prefer_this_title_as_link_text": ("link_text" in form.changed_data),
            }
            return render_modal_workflow(
                request,
                None,
                None,
                None,
                json_data={"step": "external_link_chosen", "result": result},
            )
    else:
        form = TitledEmailLinkChooserForm(initial=initial_data, prefix="email-link-chooser")

    return render_modal_workflow(
        request,
        "wagtailadmin/chooser/titled_email_link.html",
        None,
        shared_context(
            request,
            {
                "form": form,
            },
        ),
        json_data={"step": "email_link"},
    )


def titled_phone_link(request):
    initial_data = {
        "link_text": request.GET.get("link_text", ""),
        "phone_number": request.GET.get("link_url", ""),
        "link_title": request.GET.get("link_title", ""),
    }

    if request.method == "POST":
        form = TitledPhoneLinkChooserForm(request.POST, initial=initial_data, prefix="phone-link-chooser")

        if form.is_valid():
            result = {
                "url": "tel:" + form.cleaned_data["phone_number"],
                "title": form.cleaned_data["link_text"].strip() or form.cleaned_data["phone_number"],
                "link_title": form.cleaned_data["link_title"],
                # If the user has explicitly entered / edited something in the link_text field,
                # always use that text. If not, we should favour keeping the existing link/selection
                # text, where applicable.
                "prefer_this_title_as_link_text": ("link_text" in form.changed_data),
            }
            return render_modal_workflow(
                request,
                None,
                None,
                None,
                json_data={"step": "external_link_chosen", "result": result},
            )
    else:
        form = TitledPhoneLinkChooserForm(initial=initial_data, prefix="phone-link-chooser")

    return render_modal_workflow(
        request,
        "wagtailadmin/chooser/titled_phone_link.html",
        None,
        shared_context(
            request,
            {
                "form": form,
            },
        ),
        json_data={"step": "phone_link"},
    )
