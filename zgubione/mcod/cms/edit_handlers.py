from wagtail.admin.edit_handlers import FieldPanel as WagtailFieldPanel


class FieldPanel(WagtailFieldPanel):
    def on_form_bound(self):
        self.bound_field = self.form[self.field_name]
        self.heading = self.heading or self.bound_field.label
        self.help_text = self.help_text or self.bound_field.help_text
