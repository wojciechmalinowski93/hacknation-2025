from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _, ngettext
from suit.widgets import AutosizedTextarea, NumberInput, SuitDateWidget

from mcod.academy.models import Course, CourseModule

TOTAL_FORM_COUNT = "TOTAL_FORMS"


class CourseAdminForm(forms.ModelForm):

    class Meta:
        model = Course
        fields = (
            "title",
            "participants_number",
            "venue",
            "notes",
            "file",
            "materials_file",
            "status",
        )
        widgets = {
            "notes": AutosizedTextarea,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("title", "notes", "venue"):
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": "span12"})


class CourseModuleInlineAdminForm(forms.ModelForm):

    class Meta:
        model = CourseModule
        fields = ("start", "number_of_days", "type")
        widgets = {
            "start": SuitDateWidget,
            "number_of_days": NumberInput(attrs={"min": 1, "max": 2}),
        }


class CourseModuleAdminFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        start_dates = set()
        data = {}
        _forms = [form for form in self.forms if form.is_valid() and form not in self.deleted_forms]
        for form in _forms:
            start_date = form.cleaned_data.get("start")
            number_of_days = form.cleaned_data.get("number_of_days")
            end_date = start_date + relativedelta(days=number_of_days - 1)
            if start_date in start_dates:
                raise forms.ValidationError(_('Duplicate values for "Start date" are not allowed.'))
            start_dates.add(start_date)
            data[form.prefix] = {"start": start_date, "end": end_date}

        for form in _forms:
            self.validate_dates(form, data)

    def validate_dates(self, form, data):
        others = {k: v for k, v in data.items() if k != form.prefix}
        msg = _("Dates of sessions cannot overlap!")
        for prefix, other in others.items():
            if other["start"] <= form.cleaned_data["start"] <= other["end"]:
                form.add_error(None, msg)
                for _form in self.forms:
                    if _form.prefix == prefix:
                        _form.add_error(None, msg)

    def full_clean(self):
        """
        Method was moved here from parent class to change hard-coded error messages.
        """
        self._errors = []
        self._non_form_errors = self.error_class()
        empty_forms_count = 0

        if not self.is_bound:  # Stop further processing.
            return
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            # Empty forms are unchanged forms beyond those with initial data.
            if not form.has_changed() and i >= self.initial_form_count():
                empty_forms_count += 1
            # Accessing errors calls full_clean() if necessary.
            # _should_delete_form() requires cleaned_data.
            form_errors = form.errors
            if self.can_delete and self._should_delete_form(form):
                continue
            self._errors.append(form_errors)
        try:
            if (
                self.validate_max and self.total_form_count() - len(self.deleted_forms) > self.max_num
            ) or self.management_form.cleaned_data[TOTAL_FORM_COUNT] > self.absolute_max:
                raise ValidationError(
                    ngettext(
                        "Course must contain %d or fewer sessions.",
                        "Course must contain %d or fewer sessions.",
                        self.max_num,
                    )
                    % self.max_num,
                    code="too_many_course_modules",
                )
            if self.validate_min and self.total_form_count() - len(self.deleted_forms) - empty_forms_count < self.min_num:
                raise ValidationError(
                    ngettext(
                        "Course must contain at least %d session.",
                        "Course must contain at least %d session.",
                        self.min_num,
                    )
                    % self.min_num,
                    code="too_few_course_modules",
                )
            # Give self.clean() a chance to do cross-form validation.
            self.clean()
        except ValidationError as e:
            self._non_form_errors = self.error_class(e.error_list)
