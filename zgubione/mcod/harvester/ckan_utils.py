from enum import Enum
from typing import Any, Dict, List

from mcod.resources.dga_constants import DGA_COLUMNS


class CKANPartialImportError(Enum):
    INVALID_LICENSE_ID = 1
    ORGANIZATION_IN_TRASH = 2
    DATASET_IN_TRASH = 3
    DATASET_ORG_EC_CONFLICT = 4
    DATASET_HVD_CONFLICT = 5
    RES_ORG_EC_CONFLICT = 6
    RES_HVD_CONFLICT = 7
    RES_DGA_OTHER_METADATA_CONFLICT = 8
    NOT_DGA_INSTITUTION_TYPE = 9
    RES_DGA_URL_NO_FIELD = 10
    RES_DGA_URL_NOT_ACCESSIBLE = 11
    RES_DGA_URL_BAD_REMOTE_FILE_EXTENSION = 12
    RES_DGA_URL_BAD_COLUMNS = 13
    TOO_MANY_DGA_RESOURCES_FOR_ORGANIZATION = 14
    ORGANIZATION_ALREADY_HAS_DGA_RESOURCE = 15
    ORGANIZATION_HAS_MORE_THAN_ONE_DGA_RES = 16


def format_invalid_license_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = "Wartość w polu license_id spoza słownika CC"
    inner_descriptions: List[str] = [
        f"<p><strong>id zbioru danych:</strong> {error['item_id']}</p>"
        f"<p><strong>license_id:</strong> {error['license_id']}</p>"
        for error in errors_data
    ]
    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_organization_in_trash_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = "<p>Instytucja znajduje się w koszu</p>"
    inner_descriptions: List[str] = [
        f"<p><strong>id zbioru danych:</strong> {error['item_id']}</p>"
        f"<p><strong>organization.title:</strong> {error['organization_title']}</p>"
        for error in errors_data
    ]
    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_dataset_in_trash_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = "<p>Zbiór danych znajduje się w koszu</p>"
    inner_descriptions: List[str] = [f"<p><strong>id zbioru danych:</strong> {error['item_id']}</p>" for error in errors_data]
    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


# DATASET HVD
def format_dataset_org_hvd_ec_conflict_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Instytucja typu 'prywatna' lub 'deweloper' nie może wybrać wartości true w polu "
        "'has_high_value_data_from_european_commission_list' zbioru danych.</p>"
    )
    inner_descriptions: List[str] = [f"<p><strong>id zbioru danych:</strong> {error['item_id']}</p>" for error in errors_data]
    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_dataset_hvd_conflict_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Pole zbioru danych 'has_high_value_data' musi mieć wartość równą true, "
        "jeżeli pole 'has_high_value_data_from_european_commission_list' ma wartość true.</p>"
    )
    inner_descriptions: List[str] = [f"<p><strong>id zbioru danych:</strong> {error['item_id']}</p>" for error in errors_data]
    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


# RESOURCE HVD
def format_res_org_hvd_ec_conflict_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Instytucja typu 'prywatna' lub 'deweloper' nie może wybrać wartości true w polu "
        "'has_high_value_data_from_european_commission_list' zasobu.</p>"
    )

    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_res_hvd_conflict_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Pole zasobu 'has_high_value_data' musi mieć wartość równą true, "
        "jeżeli pole 'has_high_value_data_from_european_commission_list' ma wartość true.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_res_dga_other_metadata_conflict_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, to pola 'has_dynamic_data', "
        "'has_research-data', 'has_high_value_data', 'has_high_value_data_from_european_commission_list', "
        "muszą mieć wartość false lub nie występować w ogóle.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_not_dga_institution_type_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Instytucja typu 'prywatna', 'inna' lub 'deweloper' nie może używać wartości true "
        "w polu 'contains_protected_data' zasobu.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_res_dga_url_no_field_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, to pole 'url' musi mieć ustawioną wartość.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_res_dga_url_not_accessible_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Adres w polu 'url' zasobu, który zawiera pole 'contains_protected_data' z wartością równą true, nie odpowiada.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_res_dga_url_remote_file_extension_error_details(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, to musi wskazywać "
        "w polu 'url' na plik w formacie xls, xlsx lub csv.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_res_dga_url_bad_columns_error_details(errors_data: List[Dict[str, Any]]) -> str:
    dga_columns_names: str = ", ".join(DGA_COLUMNS)
    error_desc = (
        f"<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, to plik zasobu musi "
        f"zawierać dokładnie {len(DGA_COLUMNS)} kolumn ułożonych następująco i nazwanych dokładnie: {dga_columns_names}.</p>"
    )

    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources_ids: List[str] = error["resources_ids"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = [f"<p><strong>id zasobu:</strong> {resource_id}</p>" for resource_id in resources_ids]

        inner_descriptions.append(inner_error_desc + "<br>".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_too_many_dga_resources_for_organization(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>W pliku  harvestera  znajduje się więcej niż 1 zasób przypisany do tej samej instytucji "
        "zawierający pole 'contains_protected_data' z wartością równą true.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        resources: List[Dict[str, Any]] = error["resources"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_desc: List[str] = []
        for idx, resource in enumerate(resources, start=1):
            res_ext_ident = resource["ext_ident"]
            res_title = resource["title"]
            resources_desc.append(f"<p>Zasób {idx}: 'title': {res_title}, 'ext_ident': {res_ext_ident}</p>")

        inner_descriptions.append(inner_error_desc + "".join(resources_desc))

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_org_has_more_than_one_dga_resource(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = (
        "<p>Dostawca posiada w portalu więcej niż jeden zasób, "
        "posiadający pole 'contains_protected_data' z wartością równą true.</p>"
    )
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        error_msg: str = error["error_msg"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        inner_error_desc += f"<p>Szczegóły błędu: {error_msg}</p>"

        inner_descriptions.append(inner_error_desc)

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'


def format_org_already_has_dga_resource(errors_data: List[Dict[str, Any]]) -> str:
    error_desc = "<p>Dostawca posiada już w portalu zasób, zawierający pole 'contains_protected_data' z wartością równą true.</p>"
    inner_descriptions: List[str] = []
    for error in errors_data:
        item_id: str = error["item_id"]
        item_dga_resources_ids: List[str] = error["item_dga_resources_ids"]
        db_resource_id: str = error["existing_dga_resource_id"]
        db_resource_title: str = error["existing_dga_resource_title"]

        inner_error_desc: str = f"<p><strong>id zbioru danych:</strong> {item_id}</p>"
        resources_descriptions: List[str] = []
        for idx, resource_id in enumerate(item_dga_resources_ids, start=1):
            resources_descriptions.append(f"<p><strong>Zasób {idx}:</strong> 'ext_ident': {resource_id}</p>")
        resources_desc: str = "<br>".join(resources_descriptions)

        inner_error_desc += resources_desc

        inner_error_desc += f"<p>Zasób istniejący w bazie danych: 'title': {db_resource_title}, 'id': {db_resource_id}</p>"
        inner_descriptions.append(inner_error_desc)

    inner_error_desc: str = "<br>".join(inner_descriptions)
    return f'{error_desc}<div class="expandable">{inner_error_desc}</div>'
