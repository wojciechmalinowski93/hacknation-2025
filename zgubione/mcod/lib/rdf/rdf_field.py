from rdflib import Literal


class RDFField:
    def __init__(
        self,
        predicate=None,
        object_type=None,
        object_value=None,
        object=None,
        base_uri=None,
        allow_null=True,
        object_value_to_uppercase=False,
        swap_subject_and_object=False,
        many=False,
        required=True,
        try_non_lang=False,
        value_on_null=None,
    ):

        if object is None and object_type is None:
            object_type = Literal

        self.predicate = predicate
        self.object_type = object_type
        self.object_value = object_value
        self.object = object
        self.base_uri = base_uri
        self.allow_null = allow_null
        self.object_value_to_uppercase = object_value_to_uppercase
        self.swap_subject_and_object = swap_subject_and_object
        self.many = many
        self.required = required
        self.try_non_lang = try_non_lang
        self.value_on_null = value_on_null

    def parse_value(self, value):
        if isinstance(value, Literal) and self.object_type(value.value) == value:
            return value
        elif isinstance(value, Literal) and self.try_non_lang and Literal(value.value) == value:
            return value
        elif not isinstance(value, Literal):
            return value
        else:
            return None
