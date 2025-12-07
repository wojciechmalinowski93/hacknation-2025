import logging

import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from requests.auth import HTTPBasicAuth

from mcod.regions.exceptions import MalformedTerytCodeError

logger = logging.getLogger("mcod")


class BaseApi:
    def __init__(self, url):
        self.url = url
        self.user = settings.GEOCODER_USER
        self.password = settings.GEOCODER_PASS
        self.hierarchy_region_labels = [
            "locality_id",
            "localadmin_id",
            "county_id",
            "region_id",
        ]

    def _send_request(self, api_path, params, err_resp=None):
        url = f"{self.url}{api_path}"
        try:
            resp = requests.get(url, params=params, auth=HTTPBasicAuth(self.user, self.password)).json()
        except requests.exceptions.RequestException as err:
            resp = err_resp if err_resp is not None else []
            logger.error(
                "Error occurred while sending request by {} to url {} with params {} : {}".format(
                    self.__class__.__name__, url, params, err
                )
            )
        return resp

    def add_hierarchy_labels(self, reg_data):
        return reg_data

    def convert_teryt_id(self, teryt_id):
        len_mapping = {2: "region", 4: "county", 7: "admin_or_locality"}
        try:
            region_type = len_mapping[len(teryt_id)]
        except KeyError:
            raise MalformedTerytCodeError(
                _(
                    f"Malformed teryt code: {teryt_id}."
                    f" Provided code does not seems to refer to region, county,"
                    f" localadmin or locality"
                )
            )
        region_type = self.verify_teryt_region(teryt_id) if region_type == "admin_or_locality" else region_type
        return f"teryt:{region_type}:{teryt_id}"

    @staticmethod
    def is_valid_simc_code(teryt_id):
        control_num = teryt_id[-1]
        base_num = teryt_id[:-1]
        id_sum = sum([(i + 2) * int(num) for i, num in enumerate(base_num)])
        check_sum = id_sum % 11
        check_sum = "0" if check_sum == 10 else str(check_sum)
        return check_sum == control_num

    def verify_teryt_region(self, teryt_id):
        return "locality" if self.is_valid_simc_code(teryt_id) else "localadmin"

    def convert_teryt_to_gids(self, ids):
        gids = []
        for reg_id in ids:
            gids.append(self.convert_teryt_id(reg_id))
        return gids

    def get_teryt_name(self, reg):
        try:
            teryt_name = reg["properties"]["addendum"]["terytdata"]["teryt_name"]
        except KeyError:
            teryt_name = None
        return teryt_name

    def get_teryt_area_lineage(self, props):
        try:
            admin_area_id = (
                props["addendum"]["terytdata"].get("teryt_admin_area_id") if props["layer"] == "locality" else props["id"]
            )
        except KeyError:
            admin_area_id = ""
        id_len = len(admin_area_id)
        lineage = {}
        if id_len == 2:
            lineage["region_id"] = admin_area_id
        if id_len == 4:
            lineage["region_id"] = admin_area_id[:2]
            lineage["county_id"] = admin_area_id
        elif id_len == 7:
            lineage["region_id"] = admin_area_id[:2]
            lineage["county_id"] = admin_area_id[:4]
            lineage["localadmin_id"] = admin_area_id
        if props["layer"] == "locality":
            lineage["locality_id"] = props["id"]
        return lineage


class PlaceholderApi(BaseApi):
    def __init__(self):
        super().__init__(settings.PLACEHOLDER_URL)

    def find_by_id(self, ids):
        params = {"ids": ",".join([str(i) for i in ids])}
        resp = self._send_request("/parser/findbyid", params, err_resp={})
        return resp

    def get_all_regions_details(self, ids):
        additional_regions_ids = []
        main_regions_ids = []
        reg_data = self.find_by_id(ids)
        for region in reg_data.values():
            main_regions_ids.append(region["id"])
            place_label = f'{region["placetype"]}_id'
            parent_regions = region["lineage"][0]
            additional_regions_ids.extend(
                [
                    parent_regions[r_type]
                    for r_type in self.hierarchy_region_labels
                    if parent_regions.get(r_type) and r_type != place_label
                ]
            )
        additional_regions_ids = list(frozenset(additional_regions_ids))
        additional_regions_details = self.find_by_id(additional_regions_ids)
        reg_data.update(additional_regions_details)
        self.add_hierarchy_labels(reg_data)
        all_regions_ids = main_regions_ids + additional_regions_ids
        return reg_data, all_regions_ids

    def get_base_names(self, reg_data, parent_id, reg_details, r_type):
        try:
            name_pl = (
                reg_data[parent_id]["names"]["pol"][0] if reg_data[parent_id]["names"].get("pol") else reg_data[parent_id]["name"]
            )
            name_en = (
                reg_data[parent_id]["names"]["eng"][0] if reg_data[parent_id]["names"].get("eng") else reg_data[parent_id]["name"]
            )
        except KeyError:
            name_pl = reg_details["lineage_names"][r_type[:-3]]
            name_en = name_pl
        return name_pl, name_en

    def add_hierarchy_labels(self, reg_data):
        for reg_id, reg_details in reg_data.items():
            parent_regions = reg_details["lineage"][0]
            pl_labels = []
            en_labels = []
            for r_type in self.hierarchy_region_labels:
                parent_id = parent_regions.get(r_type)
                if parent_id:
                    parent_id = str(parent_id)
                    name_pl, name_en = self.get_base_names(reg_data, parent_id, reg_details, r_type)
                    if r_type == "localadmin_id":
                        if not name_pl.startswith("Gmina"):
                            name_pl = f"Gmina {name_pl}"
                        if name_en.startswith("Gmina"):
                            split_name = name_en.split()
                            name_en = f"COMM. {split_name[0]}"
                        else:
                            name_en = f" COMM.{name_en}"
                    elif r_type == "county_id":
                        name_pl = f'pow. {name_pl.replace("powiat ", "")}'
                        name_en = f'COU. {name_en.replace("powiat ", "")}'
                    elif r_type == "region_id":
                        name_pl = f"woj. {name_pl}"
                    pl_labels.append(name_pl)
                    en_labels.append(name_en)
            reg_details["hierarchy_label_pl"] = ", ".join(pl_labels)
            reg_details["hierarchy_label_en"] = ", ".join(en_labels)

    def fill_placeholder_data(self, reg_data, wof_teryt_mapping):
        placeholder_data = self.find_by_id(wof_teryt_mapping.keys())
        for region_id, region_details in placeholder_data.items():
            reg_data[wof_teryt_mapping[region_id]["teryt_id"]]["geom"] = region_details["geom"]
            eng_name = region_details["names"].get("eng")
            if eng_name:
                reg_data[wof_teryt_mapping[region_id]["teryt_id"]]["names"]["eng"] = eng_name

    def convert_to_placeholder_format(self, regions_list, wof_teryt_mapping):
        reg_data = {}
        for region in regions_list:
            props = region["properties"]
            teryt_name = self.get_teryt_name(region)
            name_ = teryt_name if teryt_name is not None and teryt_name.lower() != props["name"].lower() else props["name"]
            lon = region["geometry"]["coordinates"][0]
            lat = region["geometry"]["coordinates"][1]
            reg_data[props["id"]] = {
                "name": name_,
                "placetype": props["layer"],
                "lineage": [self.get_teryt_area_lineage(props)],
                "lineage_names": {
                    r_type[:-3]: props[r_type[:-3]] for r_type in self.hierarchy_region_labels if props.get(r_type[:-3])
                },
                "geom": {"bbox": f"{lon},{lat},{lon},{lat}", "lat": lat, "lon": lon},
                "names": {"pol": [name_]},
            }
        self.fill_placeholder_data(reg_data, wof_teryt_mapping)
        self.add_hierarchy_labels(reg_data)
        return reg_data


class PeliasApi(BaseApi):
    def __init__(self, size=25):
        self.size = size
        super().__init__(settings.GEOCODER_URL + "/v1/")

    def autocomplete(self, text, lang="pl", layers=None):
        params = {"text": text, "lang": lang, "sources": "teryt", "size": self.size}
        if layers:
            params["layers"] = layers
        resp = self._send_request("autocomplete", params)
        self.add_hierarchy_labels(resp)
        return resp

    def place(self, ids):
        params = {"ids": ",".join(ids), "lang": "pl"}
        return self._send_request("place", params, err_resp={})

    def add_hierarchy_labels(self, reg_data):
        for reg in reg_data["features"]:
            labels = []
            for r_type in self.hierarchy_region_labels:
                type_label = r_type[:-3]
                name = reg["properties"].get(type_label)
                try:
                    teryt_name = reg["properties"]["addendum"]["terytdata"]["teryt_name"]
                except KeyError:
                    teryt_name = None
                if name:
                    area_type_mapping = {
                        "localadmin_id": "Gmina ",
                        "county_id": "pow. ",
                        "region_id": "woj. ",
                    }
                    area_type = area_type_mapping.get(r_type, "")
                    if type_label == "locality" and teryt_name is not None and teryt_name.lower() != name.lower():
                        name = teryt_name
                    area_type = "" if r_type == "localadmin_id" and "gmina" in name.lower() else area_type
                    labels.append(f"{area_type}{name}")
                elif not name and reg["properties"]["layer"] == "locality" and teryt_name:
                    name = teryt_name
                    labels.append(name)
            reg["properties"]["hierarchy_label"] = ", ".join(labels)

    def translate_teryt_to_wof_ids(self, teryt_codes):
        wof_ids = []
        if teryt_codes:
            gids = self.convert_teryt_to_gids(teryt_codes)
            places_details = self.place(gids)
            for reg in places_details["features"]:
                teryt_gid = reg["properties"]["gid"]
                gid_elems = teryt_gid.split(":")
                wof_gid = f"{gid_elems[1]}_gid"
                region_id = reg["properties"][wof_gid].split(":")[2]
                wof_ids.append(region_id)
        return wof_ids

    def get_regions_details_by_teryt(self, ids):
        main_regions_ids = []
        teryt_gids = self.convert_teryt_to_gids(ids)
        places_details = self.place(teryt_gids)
        regions_list = places_details.get("features", [])
        additional_teryt_gids = []
        for place in regions_list:
            props = place["properties"]
            main_regions_ids.append(props["id"])
            lineage = self.get_teryt_area_lineage(props)
            lineage.pop(f'{props["layer"]}_id')
            parent_regions = list(lineage.values())
            additional_teryt_gids.extend(self.convert_teryt_to_gids(parent_regions))
        additional_regions_details = self.place(list(frozenset(additional_teryt_gids)))
        additional_regions_list = additional_regions_details.get("features", [])
        all_regions_list = regions_list + additional_regions_list
        wof_teryt_mapping = self.get_wof_teryt_mapping(all_regions_list)
        return all_regions_list, wof_teryt_mapping

    def get_wof_teryt_mapping(self, all_regions):
        wof_teryt_mapping = {}
        for place in all_regions:
            props = place["properties"]
            wof_gid = props.get(f"{props['layer']}_gid")
            if wof_gid:
                wof_id = wof_gid.split(":")[-1]
                wof_teryt_mapping[wof_id] = {
                    "teryt_id": props["id"],
                    "layer": props["layer"],
                }
        return wof_teryt_mapping

    def fill_geonames_data(self, reg_data, wof_teryt_mapping):
        wof_gids = [f'whosonfirst:{region_data["layer"]}:{wof_id}' for wof_id, region_data in wof_teryt_mapping.items()]
        wof_data = self.place(wof_gids)
        geonames_ids = {
            feat["properties"]["id"]: feat["properties"]["addendum"]["concordances"]["gn:id"]
            for feat in wof_data.get("features", [])
            if feat["properties"].get("addendum") and feat["properties"]["addendum"]["concordances"].get("gn:id")
        }
        for wof_id, gn_id in geonames_ids.items():
            teryt_id = wof_teryt_mapping[wof_id]["teryt_id"]
            reg_data[teryt_id]["geonames_id"] = gn_id
