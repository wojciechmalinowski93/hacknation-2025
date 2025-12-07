from django.conf import settings
from django.db import migrations


def get_common_params(query_url):
    base_url, params = query_url.split("?")
    model = base_url.split("/")[-1][:-1]
    orig_params = dict(param.split("=") for param in params.split("&"))
    return model, orig_params


def convert14(query_url):
    model, orig_params = get_common_params(query_url)
    new_params = {}
    q = []
    for key, val in orig_params.items():
        if key == "id":
            new_params["id"] = f"{model}-{val}"
        elif any(key.startswith(fld) for fld in ("title", "notes", "tag")):
            q.append(val)
        elif key == "created":
            new_params[key.replace("created", "date")] = val
        elif key == "sort":
            if any(val.endswith(date) for date in ("modified", "created", "verified")):
                new_params["sort"] = "-date" if val.startswith("-") else "date"
            elif val == "title":
                new_params[key] = orig_params[key]
        elif key == "facet[terms]":
            facets = val.split(",")
            try:
                facets.remove("by_tag")
            except ValueError:
                pass
            new_params[key] = ",".join(facets)
        elif any(key.startswith(fld) for fld in ("application", "resource", "include")):
            pass
        else:
            new_params[key] = orig_params[key]

    q.append(orig_params.get("q", ""))
    new_params["q"] = " ".join(q)
    return settings.API_URL + f"/search?model={model}&" + "&".join(f"{key}={val}" for key, val in new_params.items())


def convert10(query_url):
    model, orig_params = get_common_params(query_url)
    new_params = {}
    q = []

    OPER_MAP = {
        "prefix": "[startswith]",
        "in": "[terms]",
    }
    FACET_MAP = {
        "institutions": "by_institution",
        "categories": "by_category",
        "formats": "by_format",
        "openness_scores": "by_openness_score",
    }

    for key, val in orig_params.items():
        field, oper = "", ""
        try:
            field, oper = key.split("__")

            if oper in ("wildcard", "exclude"):
                continue
            elif oper in OPER_MAP.keys():
                oper = OPER_MAP[oper]
            else:
                oper = f"[{oper}]"
        except ValueError:
            field = key

        if field == "facet":
            facets = val.split(",")
            try:
                facets.remove("tags")
            except ValueError:
                pass
            new_params["facet"] = ",".join(FACET_MAP[facet] for facet in facets)
        else:
            vals = val.split("|")
            if field in ("slug", "views_count"):
                continue
            if field in ("title", "notes", "tags"):
                q.extend(vals)
                continue
            elif field.startswith("id"):
                if field == "ids":
                    field = "id"
                    oper = "[terms]"
                vals = (f"{model}-{pk}" for pk in vals)
            elif field in ("category", "institution"):
                field = field + "[id]"
            elif field in ("formats", "openness_score"):
                field = field[:-1]
            elif field == "sort":
                if any(val.endswith(suf) for suf in ("id", "views_count")):
                    continue
                elif any(val.endswith(suf) for suf in ("modified", "created", "verified")):
                    vals = ["-date"] if val.startswith("-") else ["date"]
            new_params[field + oper] = ",".join(vals)

    q.append(orig_params.get("q", ""))
    new_params["q"] = " ".join(q)
    return settings.API_URL + f"/search?model={model}&" + "&".join(f"{key}={val}" for key, val in new_params.items())


def convert_subscription_to_search(apps, schema_editor):
    Watcher = apps.get_model("watchers", "Watcher")
    updates = []

    for watcher in Watcher.objects.filter(object_name="query").exclude(object_ident__contains="/search?"):
        converter = convert14 if "/1.4/" in watcher.object_ident else convert10
        updates.append((watcher.pk, converter(watcher.object_ident)))

    for update in updates:
        Watcher.objects.filter(pk=update[0]).update(object_ident=update[1])


def reverse_conversion(apps, schema_editor):
    # there is no way back...
    pass


class Migration(migrations.Migration):

    dependencies = [("watchers", "0014_remove_subscription_enable_notifications")]

    operations = [
        migrations.RunPython(convert_subscription_to_search, reverse_conversion),
    ]
