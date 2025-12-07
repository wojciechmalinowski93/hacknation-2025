from django.utils.translation import gettext_lazy as _

spec = {
    "errors": {
        "blank-header": {
            "context": "head",
            "description": _(
                "A column in the header row is should be provided."
                "\n\n "
                "How it could be resolved:\n"
                " - Add the missing column name to "
                "the first row of the data "
                "source.\n"
                " - If the first row starts with, "
                "or ends with a comma, remove it.\n"
                " - If this error should be "
                "ignored disable `blank-header` "
                "check in {validator}."
            ),
            "message": _("Header in column {column_number} is blank"),
            "name": _("Blank Header"),
            "type": "structure",
            "weight": 3,
        },
        "blank-row": {
            "context": "body",
            "description": _(
                "This row is empty. A row should "
                "contain at least one value.\n"
                "\n"
                " How it could be resolved:\n"
                " - Delete the row.\n"
                " - If this error should be ignored "
                "disable `blank-row` check in "
                "{validator}."
            ),
            "message": _("Row {row_number} is completely blank"),
            "name": _("Blank Row"),
            "type": "structure",
            "weight": 9,
        },
        "duplicate-header": {
            "context": "head",
            "description": _(
                "Two columns in the header row "
                "have the same value. Column "
                "names should be unique.\n"
                "\n"
                " How it could be resolved:\n"
                " - Add the missing column "
                "name to the first row of the "
                "data.\n"
                " - If the first row starts "
                "with, or ends with a comma, "
                "remove it.\n"
                " - If this error should be "
                "ignored disable "
                "`duplicate-header` check in "
                "{validator}."
            ),
            "message": _("Header in column {column_number} " "is duplicated to header in " "column(s) {column_numbers}"),
            "name": _("Duplicate Header"),
            "type": "structure",
            "weight": 3,
        },
        "duplicate-row": {
            "context": "body",
            "description": _(
                "The exact same data has been "
                "seen in another row.\n"
                "\n"
                " How it could be resolved:\n"
                " - If some of the data is "
                "incorrect, correct it.\n"
                " - If the whole row is an "
                "incorrect duplicate, remove it.\n"
                " - If this error should be "
                "ignored disable `duplicate-row` "
                "check in {validator}."
            ),
            "message": _("Row {row_number} is duplicated to " "row(s) {row_numbers}"),
            "name": _("Duplicate Row"),
            "type": "structure",
            "weight": 5,
        },
        "encoding-error": {
            "context": "table",
            "description": _(
                "Data reading error because of "
                "an encoding problem.\n"
                "\n"
                " How it could be resolved:\n"
                " - Fix data source if it's "
                "broken.\n"
                " - Set correct encoding in "
                "{validator}."
            ),
            "message": _("The data source could not be " "successfully decoded with " "{encoding} encoding"),
            "name": _("Encoding Error"),
            "type": "source",
            "weight": 100,
        },
        "enumerable-constraint": {
            "context": "body",
            "description": _(
                "This field value should "
                "be equal to one of the "
                "values in the "
                "enumeration constraint.\n"
                "\n"
                " How it could be "
                "resolved:\n"
                " - If this value is not "
                "correct, update the "
                "value.\n"
                " - If value is correct, "
                "then remove or refine "
                "the `enum` constraint in "
                "the schema.\n"
                " - If this error should "
                "be ignored disable "
                "`enumerable-constraint` "
                "check in {validator}."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} does not "
                "conform to the given "
                "enumeration: {constraint}"
            ),
            "name": _("Enumerable Constraint"),
            "type": "schema",
            "weight": 7,
        },
        "extra-header": {
            "context": "head",
            "description": _(
                "The first row of the data source "
                "contains header that doesn't "
                "exist in the schema.\n"
                "\n"
                " How it could be resolved:\n"
                " - Remove the extra column from "
                "the data source or add the "
                "missing field to the schema\n"
                " - If this error should be "
                "ignored disable `extra-header` "
                "check in {validator}."
            ),
            "message": _("There is an extra header in column " "{column_number}"),
            "name": _("Extra Header"),
            "type": "schema",
            "weight": 9,
        },
        "extra-value": {
            "context": "body",
            "description": _(
                "This row has more values compared "
                "to the header row (the first row "
                "in the data source). A key concept "
                "is that all the rows in tabular "
                "data must have the same number of "
                "columns.\n"
                "\n"
                " How it could be resolved:\n"
                " - Check data has an extra comma "
                "between the values in this row.\n"
                " - If this error should be ignored "
                "disable `extra-value` check in "
                "{validator}."
            ),
            "message": _("Row {row_number} has an extra value in " "column {column_number}"),
            "name": _("Extra Value"),
            "type": "structure",
            "weight": 9,
        },
        "format-error": {
            "context": "table",
            "description": _(
                "Data reading error because of "
                "incorrect format.\n"
                "\n"
                " How it could be resolved:\n"
                " - Fix data format (e.g. change "
                "file extension from `txt` to "
                "`csv`).\n"
                " - Set correct format in "
                "{validator}."
            ),
            "message": _("The data source is in an unknown " "format; no tabular data can be " "extracted"),
            "name": _("Format Error"),
            "type": "source",
            "weight": 100,
        },
        "http-error": {
            "context": "table",
            "description": _(
                "Data reading error because of HTTP "
                "error.\n"
                "\n"
                " How it could be resolved:\n"
                " - Fix url link if it's not "
                "correct."
            ),
            "message": _("The data source returned an HTTP error " "with a status code of {status_code}"),
            "name": _("HTTP Error"),
            "type": "source",
            "weight": 100,
        },
        "io-error": {
            "context": "table",
            "description": _(
                "Data reading error because of IO "
                "error.\n"
                "\n"
                " How it could be resolved:\n"
                " - Fix path if it's not correct."
            ),
            "message": _("The data source returned an IO Error of " "type {error_type}"),
            "name": _("IO Error"),
            "type": "source",
            "weight": 100,
        },
        "maximum-constraint": {
            "context": "body",
            "description": _(
                "This field value should be "
                "less or equal than "
                "constraint value.\n"
                "\n"
                " How it could be resolved:\n"
                " - If this value is not "
                "correct, update the value.\n"
                " - If value is correct, "
                "then remove or refine the "
                "`maximum` constraint in the "
                "schema.\n"
                " - If this error should be "
                "ignored disable "
                "`maximum-constraint` check "
                "in {validator}."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} does not "
                "conform to the maximum "
                "constraint of {constraint}"
            ),
            "name": _("Maximum Constraint"),
            "type": "schema",
            "weight": 7,
        },
        "maximum-length-constraint": {
            "context": "body",
            "description": _(
                "A length of this "
                "field value should "
                "be less or equal "
                "than schema "
                "constraint value.\n"
                "\n"
                " How it could be "
                "resolved:\n"
                " - If this value is "
                "not correct, update "
                "the value.\n"
                " - If value is "
                "correct, then remove "
                "or refine the "
                "`maximumLength` "
                "constraint in the "
                "schema.\n"
                " - If this error "
                "should be ignored "
                "disable "
                "`maximum-length-constraint` "
                "check in "
                "{validator}."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} does not "
                "conform to the maximum "
                "length constraint of "
                "{constraint}"
            ),
            "name": _("Maximum Length Constraint"),
            "type": "schema",
            "weight": 7,
        },
        "minimum-constraint": {
            "context": "body",
            "description": _(
                "This field value should be "
                "greater or equal than "
                "constraint value.\n"
                "\n"
                " How it could be resolved:\n"
                " - If this value is not "
                "correct, update the value.\n"
                " - If value is correct, "
                "then remove or refine the "
                "`minimum` constraint in the "
                "schema.\n"
                " - If this error should be "
                "ignored disable "
                "`minimum-constraint` check "
                "in {validator}."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} does not "
                "conform to the minimum "
                "constraint of {constraint}"
            ),
            "name": _("Minimum Constraint"),
            "type": "schema",
            "weight": 7,
        },
        "minimum-length-constraint": {
            "context": "body",
            "description": _(
                "A length of this "
                "field value should "
                "be greater or equal "
                "than schema "
                "constraint value.\n"
                "\n"
                " How it could be "
                "resolved:\n"
                " - If this value is "
                "not correct, update "
                "the value.\n"
                " - If value is "
                "correct, then remove "
                "or refine the "
                "`minimumLength` "
                "constraint in the "
                "schema.\n"
                " - If this error "
                "should be ignored "
                "disable "
                "`minimum-length-constraint` "
                "check in "
                "{validator}."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} does not "
                "conform to the minimum "
                "length constraint of "
                "{constraint}"
            ),
            "name": _("Minimum Length Constraint"),
            "type": "schema",
            "weight": 7,
        },
        "missing-header": {
            "context": "head",
            "description": _(
                "Based on the schema there "
                "should be a header that is "
                "missing in the first row of the "
                "data source.\n"
                "\n"
                " How it could be resolved:\n"
                " - Add the missing column to "
                "the data source or remove the "
                "extra field from the schema\n"
                " - If this error should be "
                "ignored disable "
                "`missing-header` check in "
                "{validator}."
            ),
            "message": _("There is a missing header in column " "{column_number}"),
            "name": _("Missing Header"),
            "type": "schema",
            "weight": 9,
        },
        "missing-value": {
            "context": "body",
            "description": _(
                "This row has less values "
                "compared to the header row (the "
                "first row in the data source). A "
                "key concept is that all the rows "
                "in tabular data must have the "
                "same number of columns.\n"
                "\n"
                " How it could be resolved:\n"
                " - Check data is not missing a "
                "comma between the values in this "
                "row.\n"
                " - If this error should be "
                "ignored disable `missing-value` "
                "check in {validator}."
            ),
            "message": _("Row {row_number} has a missing value " "in column {column_number}"),
            "name": _("Missing Value"),
            "type": "structure",
            "weight": 9,
        },
        "non-matching-header": {
            "context": "head",
            "description": _(
                "One of the data source "
                "headers doesn't match the "
                "field name defined in the "
                "schema.\n"
                "\n"
                " How it could be "
                "resolved:\n"
                " - Rename header in the "
                "data source or field in "
                "the schema\n"
                " - If this error should be "
                "ignored disable "
                "`non-matching-header` "
                "check in {validator}."
            ),
            "message": _("Header in column " "{column_number} doesn't match " "field name {field_name} in the " "schema"),
            "name": _("Non-Matching Header"),
            "type": "schema",
            "weight": 9,
        },
        "pattern-constraint": {
            "context": "body",
            "description": _(
                "This field value should "
                "conform to constraint "
                "pattern.\n"
                "\n"
                " How it could be resolved:\n"
                " - If this value is not "
                "correct, update the value.\n"
                " - If value is correct, "
                "then remove or refine the "
                "`pattern` constraint in the "
                "schema.\n"
                " - If this error should be "
                "ignored disable "
                "`pattern-constraint` check "
                "in {validator}."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} does not "
                "conform to the pattern "
                "constraint of {constraint}"
            ),
            "name": _("Pattern Constraint"),
            "type": "schema",
            "weight": 7,
        },
        "required-constraint": {
            "context": "body",
            "description": _(
                "This field is a required "
                "field, but it contains no "
                "value.\n"
                "\n"
                " How it could be "
                "resolved:\n"
                " - If this value is not "
                "correct, update the "
                "value.\n"
                " - If value is correct, "
                "then remove the `required` "
                "constraint from the "
                "schema.\n"
                " - If this error should be "
                "ignored disable "
                "`required-constraint` "
                "check in {validator}."
            ),
            "message": _("Column {column_number} is a " "required field, but row " "{row_number} has no value"),
            "name": _("Required Constraint"),
            "type": "schema",
            "weight": 9,
        },
        "schema-error": {
            "context": "table",
            "description": _(
                "Provided schema is not valid.\n"
                "\n"
                " How it could be resolved:\n"
                " - Update schema descriptor to be "
                "a valid descriptor\n"
                " - If this error should be "
                "ignored disable schema checks in "
                "{validator}."
            ),
            "message": _("Table Schema error: {error_message}"),
            "name": _("Table Schema Error"),
            "type": "schema",
            "weight": 15,
        },
        "scheme-error": {
            "context": "table",
            "description": _(
                "Data reading error because of "
                "incorrect scheme.\n"
                "\n"
                " How it could be resolved:\n"
                " - Fix data scheme (e.g. change "
                "scheme from `ftp` to `http`).\n"
                " - Set correct scheme in "
                "{validator}."
            ),
            "message": _("The data source is in an unknown " "scheme; no tabular data can be " "extracted"),
            "name": _("Scheme Error"),
            "type": "source",
            "weight": 100,
        },
        "source-error": {
            "context": "table",
            "description": _(
                "Data reading error because of not "
                "supported or inconsistent "
                "contents.\n"
                "\n"
                " How it could be resolved:\n"
                " - Fix data contents (e.g. change "
                "JSON data to array or "
                "arrays/objects).\n"
                " - Set correct source settings in "
                "{validator}."
            ),
            "message": _(
                "The data source has not supported or " "has inconsistent contents; no tabular " "data can be extracted"
            ),
            "name": _("Source Error"),
            "type": "source",
            "weight": 100,
        },
        "type-or-format-error": {
            "context": "body",
            "description": _(
                "The value does not match "
                "the schema type and "
                "format for this field.\n"
                "\n"
                " How it could be "
                "resolved:\n"
                " - If this value is not "
                "correct, update the "
                "value.\n"
                " - If this value is "
                "correct, adjust the type "
                "and/or format.\n"
                " - To ignore the error, "
                "disable the "
                "`type-or-format-error` "
                "check in {validator}. In "
                "this case all schema "
                "checks for row values "
                "will be ignored."
            ),
            "message": _(
                "The value {value} in row "
                "{row_number} and column "
                "{column_number} is not type "
                "{field_type} and format "
                "{field_format}"
            ),
            "name": _("Type or Format Error"),
            "type": "schema",
            "weight": 9,
        },
        "unique-constraint": {
            "context": "body",
            "description": _(
                "This field is a unique field "
                "but it contains a value that "
                "has been used in another "
                "row.\n"
                "\n"
                " How it could be resolved:\n"
                " - If this value is not "
                "correct, update the value.\n"
                " - If value is correct, then "
                "the values in this column "
                "are not unique. Remove the "
                "`unique` constraint from the "
                "schema.\n"
                " - If this error should be "
                "ignored disable "
                "`unique-constraint` check in "
                "{validator}."
            ),
            "message": _("Rows {row_numbers} has unique " "constraint violation in column " "{column_number}"),
            "name": _("Unique Constraint"),
            "type": "schema",
            "weight": 9,
        },
    },
    "version": "1.0.1",
}
