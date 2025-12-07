from django.template.loader import get_template


def painless_body(col, rule):
    return {
        "query": {
            "bool": {
                "must": {
                    "script": {
                        "script": {
                            "source": add_rule(col, rule),
                            "lang": "painless",
                        }
                    }
                }
            }
        },
        "sort": {"row_no": "asc"},
    }


def add_rule(col: str, rule: str) -> str:
    rules = {
        "numeric": numeric_rule,
        "number": numeric_rule,
        "integer": numeric_rule,
        "regon": regon_rule,
        "nip": nip_rule,
        "krs": krs_rule,
        "uaddress": uaddress_rule,
        "pna": pna_rule,
        "address_feature": address_feature_rule,
        "phone": phone_rule,
        "bool": boolean_rule,
        "date": date_rule,
        "time": time_rule,
        "datetime": datetime_rule,
        # 'any': any_rule
    }
    return rules[rule](col)


def get_rule(template_name, col_name):
    context = {
        "colname": col_name,
        "col": col_name.replace(".keyword", "").replace(".val", ""),
        "is_keyword": col_name.endswith(".keyword"),
    }
    return get_template(f"painless/{template_name}.painless").render(context)


def boolean_rule(col_name):
    return get_rule("boolean", col_name)


def krs_rule(col_name):
    return get_rule("krs", col_name)


def nip_rule(col_name):
    return get_rule("nip", col_name)


def numeric_rule(col_name):
    return get_rule("numeric", col_name)


def pna_rule(col_name):
    return get_rule("pna", col_name)


def regon_rule(col_name):
    return get_rule("regon", col_name)


def uaddress_rule(col_name):
    return get_rule("uaddress", col_name)


def address_feature_rule(col_name):
    return get_rule("address_feature", col_name)


def phone_rule(col_name):
    return get_rule("phone", col_name)


def date_rule(col_name):
    return get_rule("date", col_name)


def datetime_rule(col_name):
    return get_rule("datetime", col_name)


def time_rule(col_name):
    return get_rule("time", col_name)
