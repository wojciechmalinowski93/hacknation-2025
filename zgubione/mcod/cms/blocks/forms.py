from wagtail.core import blocks


class RadioButtonBlock(blocks.StructBlock):
    field_type = "radio-button"
    label = blocks.CharBlock(
        label="Etykieta",
        max_length=5000,
        help_text="Etykieta dla przycisku.",
        required=False,
    )
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy",
        max_length=5000,
        help_text="Tekst pomocniczy dla przycisku.",
        required=False,
    )
    value = blocks.CharBlock(label="Wartość", max_length=5000, help_text="Wartość pola.", required=True)
    checked = blocks.BooleanBlock(required=False, label="Zaznaczony domyslnie", help_text="")

    class Meta:
        form_classname = "form-block radio-button-block"


class RadioButtonWithInputBlock(blocks.StructBlock):
    field_type = "radio-button-with-input"
    label = blocks.CharBlock(label="Etykieta dla przycisku radio", max_length=5000, required=False)
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy dla przycisku radio",
        max_length=5000,
        help_text="Tekst pomocniczy.",
        required=False,
    )
    checked = blocks.BooleanBlock(required=False, label="Zaznaczony domyslnie", help_text="")
    input_label = blocks.CharBlock(label="Etykieta dla pola tekstowego", max_length=5000, required=False)
    input_help_text = blocks.CharBlock(label="Tekst pomocniczy dla pola tekstowego", max_length=5000, required=False)

    input_default_value = blocks.CharBlock(label="Domyślna wartość pola tekstowego", max_length=5000, required=False)
    input_placeholder = blocks.CharBlock(
        label="Tekst do placeholdera",
        max_length=5000,
        help_text="Tekst wyświetlany na polu do wprowadzania własnej odpowiedzi.",
        required=False,
    )

    class Meta:
        form_classname = "form-block radio-button-block-input"


class RadioButtonWithMultilineInputBlock(blocks.StructBlock):
    field_type = "radio-button-with-multiline-input"
    label = blocks.CharBlock(label="Etykieta dla przycisku radio", max_length=5000, required=False)
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy dla przycisku radio",
        max_length=5000,
        help_text="Tekst pomocniczy.",
        required=False,
    )
    checked = blocks.BooleanBlock(required=False, label="Zaznaczony domyslnie", help_text="")
    input_label = blocks.CharBlock(label="Etykieta dla pola tekstowego", max_length=5000, required=False)
    input_help_text = blocks.CharBlock(label="Tekst pomocniczy dla pola tekstowego", max_length=5000, required=False)

    input_default_value = blocks.CharBlock(label="Domyślna wartość pola tekstowego", max_length=5000, required=False)
    input_placeholder = blocks.CharBlock(
        label="Tekst do placeholdera",
        max_length=5000,
        help_text="Tekst wyświetlany na polu do wprowadzania własnej odpowiedzi.",
        required=False,
    )

    class Meta:
        form_classname = "form-block radio-button-multiline-input-block"


class CheckboxBlock(blocks.StructBlock):
    field_type = "checkbox-button"
    label = blocks.CharBlock(
        label="Etykieta",
        max_length=5000,
        help_text="Etykieta dla przycisku.",
        required=False,
    )
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy",
        max_length=5000,
        help_text="Tekst pomocniczy dla przycisku.",
        required=False,
    )
    value = blocks.CharBlock(label="Wartość", max_length=5000, help_text="Wartość pola.", required=True)
    checked = blocks.BooleanBlock(required=False, label="Zaznaczony domyslnie", help_text="")

    class Meta:
        form_classname = "form-block checkbox-button-block"


class CheckboxWithInputBlock(blocks.StructBlock):
    field_type = "checkbox-with-input"
    label = blocks.CharBlock(label="Etykieta dla przycisku checkbox", max_length=5000, required=False)
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy dla przycisku checkbox",
        max_length=5000,
        help_text="Tekst pomocniczy.",
        required=False,
    )
    checked = blocks.BooleanBlock(required=False, label="Zaznaczony domyslnie", help_text="")
    input_label = blocks.CharBlock(label="Etykieta dla pola tekstowego", max_length=5000, required=False)
    input_help_text = blocks.CharBlock(label="Tekst pomocniczy dla pola tekstowego", max_length=5000, required=False)

    input_default_value = blocks.CharBlock(label="Domyślna wartość pola tekstowego", max_length=5000, required=False)
    input_placeholder = blocks.CharBlock(
        label="Tekst do placeholdera",
        max_length=5000,
        help_text="Tekst wyświetlany na polu do wprowadzania własnej odpowiedzi.",
        required=False,
    )

    class Meta:
        form_classname = "form-block checkbox-input-block"


class CheckboxWithMultilineInputBlock(blocks.StructBlock):
    field_type = "checkbox-with-multiline-input"
    label = blocks.CharBlock(label="Etykieta dla przycisku checkbox", max_length=5000, required=False)
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy dla przycisku checkbox",
        max_length=5000,
        help_text="Tekst pomocniczy.",
        required=False,
    )
    checked = blocks.BooleanBlock(required=False, label="Zaznaczony domyslnie", help_text="")
    input_label = blocks.CharBlock(label="Etykieta dla pola tekstowego", max_length=5000, required=False)
    input_help_text = blocks.CharBlock(label="Tekst pomocniczy dla pola tekstowego", max_length=5000, required=False)

    input_default_value = blocks.CharBlock(label="Domyślna wartość pola tekstowego", max_length=5000, required=False)
    input_placeholder = blocks.CharBlock(
        label="Tekst do placeholdera",
        max_length=5000,
        help_text="Tekst wyświetlany na polu do wprowadzania własnej odpowiedzi.",
        required=False,
    )

    class Meta:
        form_classname = "form-block checkbox-with-multiline-input-block"


class SinglelineTextInput(blocks.StructBlock):
    field_type = "singleline-text-input"
    label = blocks.CharBlock(
        label="Etykieta",
        max_length=5000,
        help_text="Etykieta dla przycisku.",
        required=False,
    )
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy",
        max_length=5000,
        help_text="Tekst pomocniczy dla przycisku.",
        required=False,
    )
    value = blocks.CharBlock(label="Domyślna wartość", max_length=5000, required=False)
    placeholder = blocks.CharBlock(
        label="Tekst do placeholdera",
        max_length=5000,
        help_text="Tekst wyświetlany na polu.",
        required=False,
    )

    class Meta:
        form_classname = "form-block singleline-text-input-block"


class MultilineTextInput(blocks.StructBlock):
    field_type = "multiline-text-input"
    label = blocks.CharBlock(
        label="Etykieta",
        max_length=5000,
        help_text="Etykieta dla przycisku.",
        required=False,
    )
    help_text = blocks.CharBlock(
        label="Tekst pomocniczy",
        max_length=5000,
        help_text="Tekst pomocniczy dla przycisku.",
        required=False,
    )
    value = blocks.CharBlock(label="Wartość", max_length=5000, help_text="Wartość pola.", required=False)
    placeholder = blocks.CharBlock(
        label="Tekst do placeholdera",
        max_length=5000,
        help_text="Tekst wyświetlany na polu.",
        required=False,
    )

    class Meta:
        form_classname = "form-block multiline-text-input-block"


class DropdownInput(blocks.StructBlock):
    field_type = "dropdown-input"

    class Meta:
        form_classname = "dropdown-block"
