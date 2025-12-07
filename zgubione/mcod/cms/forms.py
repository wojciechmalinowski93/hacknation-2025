import django.forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.forms.choosers import (
    AnchorLinkChooserForm,
    EmailLinkChooserForm,
    ExternalLinkChooserForm,
    PhoneLinkChooserForm,
)
from wagtail.core.blocks import BlockField, StreamValue

from mcod.cms.blocks.forms import (
    CheckboxBlock,
    CheckboxWithInputBlock,
    CheckboxWithMultilineInputBlock,
    MultilineTextInput,
    RadioButtonBlock,
    RadioButtonWithInputBlock,
    RadioButtonWithMultilineInputBlock,
    SinglelineTextInput,
)


class SelectDateForm(django.forms.Form):
    date_from = django.forms.DateTimeField(
        required=False,
        widget=django.forms.DateInput(attrs={"placeholder": _("Date from")}),
    )
    date_to = django.forms.DateTimeField(
        required=False,
        widget=django.forms.DateInput(attrs={"placeholder": _("Date to")}),
    )


class FormPageForm(WagtailAdminPageForm):
    ERROR_CHECKBOX_AND_RADIOBUTTON = "Checkbox i radiobutton nie mogą występować w ramach jednego pytania."
    ERROR_MULTIPLE_TEXT_RADIOBUTTONS = "W ramach jednego pytania może wystąpić tylko jeden radiobutton z polem tekstowym."
    ERROR_CHECKBOX_AND_INPUT = "Checkbox i pole tekstowe nie mogą występować w ramach jednego pytania."
    ERROR_RADIOBUTTON_AND_INPUT = "Radiobutton i pole tekstowe nie mogą występować w ramach jednego pytania."

    CHECKBOX_BLOCKS = {
        CheckboxBlock,
        CheckboxWithInputBlock,
        CheckboxWithMultilineInputBlock,
    }

    RADIOBUTTON_BLOCKS_WITH_INPUT = {
        RadioButtonWithInputBlock,
        RadioButtonWithMultilineInputBlock,
    }

    RADIOBUTTON_BLOCKS = {
        RadioButtonBlock,
        *RADIOBUTTON_BLOCKS_WITH_INPUT,
    }

    CHECKABLE_BLOCKS = CHECKBOX_BLOCKS | RADIOBUTTON_BLOCKS

    INPUT_BLOCKS = {
        SinglelineTextInput,
        MultilineTextInput,
    }

    @staticmethod
    def _contains_checkbox_and_radiobutton(types):
        types = set(types)
        if types & FormPageForm.CHECKBOX_BLOCKS and types & FormPageForm.RADIOBUTTON_BLOCKS:
            return True
        return False

    @staticmethod
    def _contains_multiple_radiobuttons_with_input(types):
        types = [_type for _type in types if _type in FormPageForm.RADIOBUTTON_BLOCKS_WITH_INPUT]
        return len(types) > 1

    @staticmethod
    def _contains_checkbox_and_input(types):
        types = set(types)
        if types & FormPageForm.CHECKBOX_BLOCKS and types & FormPageForm.INPUT_BLOCKS:
            return True
        return False

    @staticmethod
    def _contains_radiobutton_and_input(types):
        types = set(types)
        if types & FormPageForm.RADIOBUTTON_BLOCKS and types & FormPageForm.INPUT_BLOCKS:
            return True
        return False

    @staticmethod
    def _add_structure_error(form, message):
        form.add_error(
            "fields",
            ValidationError(f"DEBUG: {message}", params={"__all__": [message]}),
        )

    def _is_structure_valid(self, form):
        data = form.cleaned_data.get("fields")
        if isinstance(data, StreamValue):
            block_types = [type(getattr(x[1], "block")) for x in data.stream_data]

            if self._contains_checkbox_and_radiobutton(block_types):
                FormPageForm._add_structure_error(form, FormPageForm.ERROR_CHECKBOX_AND_RADIOBUTTON)
            elif self._contains_multiple_radiobuttons_with_input(block_types):
                FormPageForm._add_structure_error(form, FormPageForm.ERROR_MULTIPLE_TEXT_RADIOBUTTONS)
            elif self._contains_radiobutton_and_input(block_types):
                FormPageForm._add_structure_error(form, FormPageForm.ERROR_RADIOBUTTON_AND_INPUT)
            elif self._contains_checkbox_and_input(block_types):
                FormPageForm._add_structure_error(form, FormPageForm.ERROR_CHECKBOX_AND_INPUT)

        return len(form.errors) == 0

    def is_valid(self):
        form_is_valid = super().is_valid()
        formsets_are_valid = True

        for formset in self._posted_formsets:
            for form in formset.forms:
                if isinstance(form.fields.get("fields"), BlockField) and form.is_valid():
                    if not self._is_structure_valid(form):
                        formsets_are_valid = False

        return form_is_valid and formsets_are_valid


class TitleChooserForm(django.forms.Form):
    link_title = django.forms.CharField(required=False, label=_("Link title"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "email_address" in self.fields:
            self.fields["email_address"].label = _("Email address")
        if "link_text" in self.fields:
            self.fields["link_text"].label = _("Link text")
        if "phone_number" in self.fields:
            self.fields["phone_number"].label = _("Phone number")


class TitledExternalLinkChooserForm(TitleChooserForm, ExternalLinkChooserForm):
    pass


class TitledAnchorLinkChooserForm(TitleChooserForm, AnchorLinkChooserForm):
    pass


class TitledEmailLinkChooserForm(TitleChooserForm, EmailLinkChooserForm):
    pass


class TitledPhoneLinkChooserForm(TitleChooserForm, PhoneLinkChooserForm):
    pass
