from datetime import datetime, timedelta
from typing import List
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import QuerySet
from django.utils import timezone

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.datasets.factories import DatasetFactory
from mcod.harvester.factories import DataSourceFactory
from mcod.resources.factories import AggregatedDGAInfoFactory, ResourceFactory
from mcod.resources.models import Chart, Resource, TaskResult


class TestResourceModel:
    def test_forced_api_type_toggle(self, resource_of_type_website):
        resource = resource_of_type_website
        assert resource.type == "website"
        resource.forced_api_type = True
        resource.save()
        assert resource.type == "api"
        resource.revalidate()
        resource.refresh_from_db()
        assert resource.type == "api"
        resource.forced_api_type = False
        resource.save()
        assert resource.type == "website"
        resource.revalidate()
        resource.refresh_from_db()
        assert resource.type == "website"

    def test_forced_file_type_toggle(self, remote_file_resource_of_api_type):
        resource = remote_file_resource_of_api_type
        assert resource.type == "api"
        resource.forced_file_type = True
        resource.save()
        resource.revalidate()
        resource.refresh_from_db()
        assert resource.type == "file"
        resource.forced_file_type = False
        resource.save()
        resource.revalidate()
        resource.refresh_from_db()
        assert resource.type == "api"

    def test_resource_fields(self, resource):
        r_dict = resource.__dict__
        fields = [
            "uuid",
            "format",
            "description",
            "position",
            "old_customfields",
            "title",
            "id",
            "dataset_id",
            "link",
            "is_removed",
            "created",
            "modified",
            "status",
            "modified_by_id",
            "created_by_id",
            "contains_protected_data",
            "has_high_value_data",
            "has_high_value_data_from_ec_list",
            "has_research_data",
            "has_dynamic_data",
        ]

        for f in fields:
            assert f in r_dict

    def test_default_resource_metadata_values(self, resource):
        """
        Check new `Resource` metadata default values.
        """
        assert resource.has_high_value_data is None
        assert resource.has_high_value_data_from_ec_list is None
        assert resource.has_research_data is None
        assert resource.has_dynamic_data is None

        assert resource.contains_protected_data is False

    def test_resource_safe_delete(self, resource):
        assert resource.status == "published"
        resource.delete()
        assert resource.is_removed is True
        assert Resource.trash.get(id=resource.id)
        assert Resource.raw.get(id=resource.id)
        with pytest.raises(ObjectDoesNotExist):
            Resource.objects.get(id=resource.id)

    def test_resource_unsafe_delete(self, resource):
        assert resource.status == "published"
        resource.delete(soft=False)
        with pytest.raises(ObjectDoesNotExist):
            Resource.raw.get(id=resource.id)
        with pytest.raises(ObjectDoesNotExist):
            Resource.trash.get(id=resource.id)

    @pytest.mark.parametrize(
        "resource_to_delete, expected_is_permanently_removed",
        [("imported_xml_resource", True), ("imported_ckan_resource", True), ("another_resource", False)],
    )
    def test_imported_and_not_imported_resource_delete(
        self, request, resource_to_delete: Resource, expected_is_permanently_removed: bool
    ):
        """Checks if deleting only the harvested resource results in permanent deletion."""

        # GIVEN
        resource: Resource = request.getfixturevalue(resource_to_delete)
        # WHEN
        resource.delete()
        # THEN
        assert resource.is_removed
        # AND THEN
        assert resource.is_permanently_removed is expected_is_permanently_removed

    def test_file_url_and_path(self, resource, mocker):
        mocker.patch("mcod.resources.link_validation.download_file", return_value=("file", {}))
        resource = Resource.objects.get(pk=resource.pk)
        assert resource.main_file
        date_folder = timezone.now().date().isoformat().replace("-", "")
        file_name = resource.main_file.name
        assert resource.main_file.url == f"/media/resources/{file_name}"
        assert resource.main_file.path == f"{settings.RESOURCES_MEDIA_ROOT}/{file_name}"
        assert date_folder in resource.main_file.url
        assert date_folder in resource.main_file.path
        k = len(TaskResult.objects.all())
        assert k > 0
        resource.revalidate()
        run_on_commit_events()
        assert len(TaskResult.objects.all()) > k

    def test_title_and_description_content_validation(self, resource_of_type_website: Resource):
        """
        Validates Resource object content: checks invalid description content
        raises ValidationError.

        Sets an invalid description value ('\x02') for a Resource object and expects a
        ValidationError when calling full_clean() on the object.
        """
        resource_of_type_website.description = "\x02"
        with pytest.raises(ValidationError):
            resource_of_type_website.full_clean()

    def test_is_dga_in_db_added_by_harvester_with_source_id(self):
        """
        Tests method is_dga_in_db_added_by_harvester_with_source_id.
        """

        # 1 case - resource added by Administration Panel
        resource_dga_in_db: Resource = ResourceFactory.create()

        assert resource_dga_in_db.is_added_by_harvester_with_id(source_id=1000) is False

        # 2 case - resource added by harvester which pk = source_id
        _source = DataSourceFactory.create(source_type="xml", name="harv_1", portal_url="https://some.url")
        source_id = _source.pk
        _dataset = DatasetFactory.create(source=_source)
        resource_dga_in_db = ResourceFactory.create(dataset=_dataset)

        assert resource_dga_in_db.is_added_by_harvester_with_id(source_id=source_id) is True

        # 3 case - resource added by harvester which pk is not equal source_id
        _source = DataSourceFactory.create(source_type="xml", name="harv_1", portal_url="https://some.url")
        _other_source = DataSourceFactory.create(source_type="xml", name="harv_2", portal_url="https://some.other.url")
        _dataset = DatasetFactory.create(source=_other_source)
        resource_dga_in_db = ResourceFactory.create(contains_protected_data=True, dataset=_dataset)
        source_id = _source.pk

        assert resource_dga_in_db.is_added_by_harvester_with_id(source_id=source_id) is False

    def test_data_date_is_filled(self):
        """System ensures that imported resources have data_date set to a not null value."""
        _today = datetime.now().date()
        # When Resource is created manually without data_date
        manual: Resource = ResourceFactory.create(
            data_date=None,
        )
        # Then it stays as none
        assert manual.data_date is None

        # Given Resource is imported without data_date
        _source = DataSourceFactory.create()
        _dataset = DatasetFactory.create(source=_source)
        imported: Resource = ResourceFactory.create(
            dataset=_dataset,
            data_date=None,
        )
        # Then we set it to today
        assert imported.data_date == _today

        # Given Resource is imported with data_date in the past
        _source = DataSourceFactory.create()
        _dataset = DatasetFactory.create(source=_source)
        imported: Resource = ResourceFactory.create(
            dataset=_dataset,
            data_date=_today - timedelta(days=100),
        )
        # Then we use the upstream value
        assert imported.data_date == _today - timedelta(days=100)

        # Given Resource is imported with data_date in the future
        _source = DataSourceFactory.create()
        _dataset = DatasetFactory.create(source=_source)
        imported: Resource = ResourceFactory.create(
            dataset=_dataset,
            data_date=_today + timedelta(days=100),
        )
        # Then we use the upstream value
        assert imported.data_date == _today + timedelta(days=100)


class TestTaskResultModel:
    def test_result_parser(self):
        exc_message = [
            {
                "code": "sth-gone-wrong",
                "delta": "triangle",
                "other_message": "it's a trap",
                "'code'": "another trap",
                "test": "test",
                "message": "Coś się nie udało",
            },
            {"code": "second-error", "message": "second error message", "test": "boom"},
        ]
        result = {
            "exc": "some_value",
            "message": "Try to break this",
            "alpha": "romeo",
            "bravo": "fiat",
            "exc_message": str(exc_message),
            "charlie": "chaplin",
        }
        for key in ["message", "code", "test"]:
            count = 0
            for msg in TaskResult.values_from_result(result, key):
                assert msg == exc_message[count].get(key)
                count += 1
            assert count == len(exc_message)

        with pytest.raises(KeyError):
            for msg in TaskResult.values_from_result(result, "other_message"):
                pass

    def test_result_parser_elastic_search_mapping_error(self):
        tr = TaskResult()
        tr.result = "{\"exc_type\": \"BulkIndexError\", \"exc_message\": \"('500 document(s) failed to index.', [{'index': {'_index': 'resource-16652', '_type': 'doc', '_id': '1b632e0f-e7e2-5cc5-89e9-60e19acf63f6', 'status': 400, 'error': {'type': 'mapper_parsing_exception', 'reason': \\\"failed to parse field [col2] of type [scaled_float] in document with id '1b632e0f-e7e2-5cc5-89e9-60e19acf63f6'\\\", 'caused_by': {'type': 'number_format_exception', 'reason': 'For input string: \\\"102\\\\xa0944\\\"'}}, 'data': {'col1': 'NOWAK', 'col2': '102\\\\xa0944', 'updated_at': datetime.datetime(2020, 2, 17, 10, 29, 22, 936871), 'row_no': 1, 'resource': {'id': 16652, 'title': '123'}}}}])\", \"uuid\": \"5bb6ff28-3542-4fe4-ab67-986c13c80b82\", \"link\": \"http://api.mcod.local/media/resources/20200217/Wykaz_nazwisk__%C5%BCe%C5%84skich_os__%C5%BCyj%C4%85ce_2020-01-22.csv\", \"format\": \"csv\", \"type\": \"file\"}"  # noqa
        assert tr.message == ["Błąd indeksacji. Wartości z kolumny [col2] nie mogą być typu [Liczba zmiennoprzecinkowa]."]
        assert tr.recommendation == ["Zmień typ kolumny [col2] na [Dane tekstowe]."]

    def test_result_parser_unhandled_elasticsearch_error(self):
        tr = TaskResult()
        tr.result = """{"exc_type": "BulkIndexError", "exc_message": "(\'1 document(s) failed to index.\', [{\'index\': {\'_index\': \'resource-16656\', \'_type\': \'doc\', \'_id\': \'62284d2e-a6ac-5978-b62a-855e97e0dd7b\', \'status\': 400, \'error\': {\'type\': \'illegal_argument_exception\', \'reason\': \'Document contains at least one immense term in field=\\"col10.keyword\\" (whose UTF8 encoding is longer than the max length 32766), all of which were skipped.  Please correct the analyzer to not produce such terms.  The prefix of the first immense term is: \\\\\'[65, 77, 66, 82, 65, 39, 32, 83, 80, -61, -109, -59, -127, 75, 65, 32, 65, 75, 67, 89, 74, 78, 65, 59, 87, 97, 114, 115, 122, 97]...\\\\\', original message: bytes can be at most 32766 in length; got 44871\', \'caused_by\': {\'type\': \'max_bytes_length_exceeded_exception\', \'reason\': \'bytes can be at most 32766 in length; got 44871\'}}, \'data\': {\'col1\': \'385925\', \'col2\': \'249524\', \'col3\': \'2011-05-27\', \'col4\': \'18/2011\', \'col5\': \'2011-08-29\', \'col6\': \'02/2013\', \'col7\': \'2013-02-28\', \'col8\': \'Joseph`s WINE & FOOD Restauracja \\u2022 Winebar \\u2022 Sklep\', \'col9\': \'SG\', \'col10\': \'AMBRA\\\\\' SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Dorota Rz\\u0105\\u017cewska;NIC: 32 33 35 41 43 ;VIE: 241725 260402 270501 290113 ;Udzielenie prawa;\\\\n385926;251409;2011-05-27;18/2011;2011-08-29;04/2013;2013-04-30;ekselent;SG;NARDION HOLDING LIMITED;Nikozja;CY;Marek Passowicz KANCELARIA PATENTOWA;NIC: 16 35 ;VIE: 050520 260115 270501 ;Udzielenie prawa;\\\\n385927;;2011-05-27;18/2011;2011-08-29;;;CALOFORT;S;Minteq UK Limited;Londyn;GB;Jan Bucyk POLSERVICE KANCELARIA RZECZNIK\\u00d3W PATENTOWYCH SP. Z O. O.;NIC: 01 ;;Umorzenie post\\u0119powania;\\\\n385928;248465;2011-05-27;18/2011;2011-08-29;12/2012;2012-12-31;HBL;SG;ALUPOL PACKAGING SP\\u00d3\\u0141KA AKCYJNA;Tychy;PL;Janusz Go\\u0142da KANCELARIA PATENTOWA 3;NIC: 06 16 ;VIE: 270501 290104 ;Udzielenie prawa;\\\\n385929;248466;2011-05-27;18/2011;2011-08-29;12/2012;2012-12-31;HBL;SG;ALUPOL PACKAGING SP\\u00d3\\u0141KA AKCYJNA;Tychy;PL;Janusz Go\\u0142da KANCELARIA PATENTOWA 3;NIC: 06 16 ;VIE: 270501 ;Udzielenie prawa;\\\\n385930;248975;2011-05-27;18/2011;2011-08-29;01/2013;2013-01-31;APARTS BED & BREAKFAST;SG;RR OFFICE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;Bo\\u017cydar Piotrowski  KANCELARIA PATENTOWA;NIC: 43 ;VIE: 070108 070109 070124 070311 270501 290112 ;Udzielenie prawa;\\\\n385931;;2011-05-27;18/2011;2011-08-29;;;APTEKA PRIMA;SG;GAP KM - TARGET SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 I WSP\\u00d3LNICY SP\\u00d3\\u0141KA JAWNA;Konin;PL;;NIC: 05 35 44 ;VIE: 270501 290112 241301 250720 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385932;;2011-05-27;18/2011;2011-08-29;;;FachowaEkipa ...polecamy lepiej ni\\u017c znajomi;SG;\\u0141ANIAK \\u0141UKASZ;Przecisz\\u00f3w;PL;;NIC: 35 38 42 ;VIE: 270501 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385933;;2011-05-27;18/2011;2011-08-29;;;SELENE;S;SELENE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Sopot;PL;;NIC: 10 20 24 35 ;;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385934;;2011-05-27;18/2011;2011-08-29;;;;G;SELENE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Sopot;PL;;NIC: 10 20 24 35 ;VIE: 010706 020305 020317 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385935;249115;2011-05-27;18/2011;2011-08-29;01/2013;2013-01-31;Almette;SG;Hochland SE;Heimenkirch;DE;Karol Gajek SO\\u0141TYSI\\u0143SKI KAWECKI & SZL\\u0118ZAK;NIC: 29 ;VIE: 270501 290113 ;Udzielenie prawa;\\\\n385936;249116;2011-05-27;18/2011;2011-08-29;01/2013;2013-01-31;Almette puszysty serek twarogowy;SG;Hochland SE;Heimenkirch;DE;Karol Gajek SO\\u0141TYSI\\u0143SKI KAWECKI & SZL\\u0118ZAK;NIC: 29 ;VIE: 071505 260104 270501 290115 ;Udzielenie prawa;\\\\n385937;249648;2011-05-27;18/2011;2011-08-29;02/2013;2013-02-28;Platinum max expert;S;ORLEN OIL SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Katarzyna Tabor-Kmiecik KANCELARIA PATENTOWA DR W. TABOR SP.J.;NIC: 01 04 ;;Udzielenie prawa;\\\\n385938;248265;2011-05-27;18/2011;2011-08-29;12/2012;2012-12-31;Colgate ADVANCED WHITE GoPure;SG;COLGATE-PALMOLIVE COMPANY, A DELAWARE COMPANY;New York;US;Adrianna Zi\\u0119cik AOMB POLSKA SP\\u00d3\\u0141KA Z O.O.;NIC: 03 ;VIE: 011509 011515 260402 270501 290115 ;Udzielenie prawa;\\\\n385939;;2011-05-28;18/2011;2011-08-29;;;Tradycyjnie warzone JASNE PE\\u0141NE KRESOWE Browar Po\\u0142udnie Piwo z browaru regionalnego;SG;KALINA TADEUSZ, KALINA PAWE\\u0141 BROWAR PO\\u0141UDNIE SP\\u00d3\\u0141KA CYWILNA;Krak\\u00f3w;PL;Andrzej Grz\\u0105ka KANCELARIA PATENTOWA;NIC: 32 ;VIE: 020115 050702 051115 240110 250101 270501 290115 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385940;249764;2011-05-28;18/2011;2011-08-29;02/2013;2013-02-28;ETNO;SG;R2 CENTER SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Suchy Las;PL;Micha\\u0142 \\u017bukowski;NIC: 03 14 25 35 ;VIE: 260104 270501 ;Udzielenie prawa;\\\\n385941;;2011-05-28;18/2011;2011-08-29;;;arte;SG;INWEST AP SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Suchy Las;PL;Anna Cybulka PORAJ KANCELARIA PRAWNO-PATENTOWA SP. Z O.O.;NIC: 03 14 25 35 ;VIE: 270501 ;Odmowa;\\\\n385942;248266;2011-05-28;18/2011;2011-08-29;12/2012;2012-12-31;Eden COLLECTION;SG;R2 CENTER SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Suchy Las;PL;Micha\\u0142 \\u017bukowski;NIC: 03 14 25 35 ;VIE: 270501 ;Udzielenie prawa;\\\\n385943;249282;2011-05-28;18/2011;2011-08-29;01/2013;2013-01-31;Fun fun collection;SG;R2 CENTER SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Suchy Las;PL;Micha\\u0142 \\u017bukowski;NIC: 03 14 25 35 ;VIE: 270501 ;Udzielenie prawa;\\\\n385944;248721;2011-05-28;18/2011;2011-08-29;01/2013;2013-01-31;BABY BULLET;S;CAPBRAN HOLDINGS, LLC;Los Angeles;US;;NIC: 07 ;;Udzielenie prawa;\\\\n385945;;2011-05-28;18/2011;2011-08-29;;;PARIS PINK 1982 STYLE IN THE USA;SG;NINES ENTERPRISES LLC;Maspeth;US;Anna Cybulka PORAJ KANCELARIA PRAWNO - PATENTOWA SP. Z O.O.;NIC: 25 ;VIE: 030106 050502 260101 260115 270501 270701 ;Umorzenie post\\u0119powania;\\\\n385946;249765;2011-05-27;18/2011;2011-08-29;02/2013;2013-02-28;Ted Zarebski`s THE POWERPIT GYM;SG;ZAR\\u0118BSKI TADEUSZ ALKIS;Kamienicki M\\u0142yn;PL;Katarzyna Czabajska TRASET BIURO PATENTOWE S.C. JACEK CZABAJSKI, KATARZYNA CZABAJSKA;NIC: 28 35 41 ;VIE: 030108 030109 030117 210313 270501 290115 ;Udzielenie prawa;\\\\n385947;;2011-05-27;18/2011;2011-08-29;;;HIT ZA HITEM;S;MULTIMEDIA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Anna G\\u00f3rska KANCELARIA PATENTOWA;NIC: 09 16 35 38 41 ;;Odmowa;\\\\n385949;249649;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;Platinum max EXPERT;SG;ORLEN OIL SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Katarzyna Tabor-Kmiecik KANCELARIA PATENTOWA DR W. TABOR SP.J.;NIC: 01 04 ;VIE: 011521 250101 261503 270501 290115 ;Udzielenie prawa;\\\\n385950;;2011-05-30;19/2011;2011-09-12;;;HEZNER;S;HEZNER KRZYSZTOF;Jaworzno;PL;Katarzyna Tabor-Kmiecik KANCELARIA PATENTOWA DR W. TABOR SP. J.;NIC: 37 39 ;;Umorzenie post\\u0119powania;\\\\n385951;263845;2011-05-29;18/2011;2011-08-29;07/2014;2014-07-31;tygryski;S;TBM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Kun\\u00f3w;PL;Ryszard Ros\\u00f3\\u0142;NIC: 30 ;;Udzielenie prawa;\\\\n385952;;2011-05-30;19/2011;2011-09-12;;;GREENPOL system;SG;GREENPOL SYSTEM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Toru\\u0144;PL;;NIC: 11 37 ;VIE: 011503 050313 270501 290115 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385953;271023;2011-05-30;19/2011;2011-09-12;04/2015;2015-04-30;HEVELIUS;S;GRUPA \\u017bYWIEC SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Dorota Rz\\u0105\\u017cewska JWP RZECZNICY PATENTOWI DOROTA RZ\\u0104\\u017bEWSKA SP.J.;NIC: 32 35 ;;Udzielenie prawa;\\\\n385954;;2011-05-30;19/2011;2011-09-12;;;A;SG;MI\\u0118DZYNARODOWE TARGI \\u0141\\u00d3DZKIE SP\\u00d3\\u0141KA TARGOWA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;Katarzyna Kwestarz;NIC: 35 38 41 ;VIE: 210114 250505 270501 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385955;;2011-05-30;19/2011;2011-09-12;;;THE GOLDEN THREAD;SG;MI\\u0118DZYNARODOWE TARGI \\u0141\\u00d3DZKIE SP\\u00d3\\u0141KA TARGOWA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;Katarzyna Kwestarz;NIC: 35 38 41 ;VIE: 261113 270501 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385956;252175;2011-05-30;19/2011;2011-09-12;05/2013;2013-05-31;;G;EXPO-\\u0141\\u00d3D\\u0179 SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;Katarzyna Kwestarz;NIC: 35 38 41 ;VIE: 020914 260104 ;Udzielenie prawa;\\\\n385957;248267;2011-05-30;19/2011;2011-09-12;12/2012;2012-12-31;TRAMAPAR;S;POLFARMEX SP\\u00d3\\u0141KA AKCYJNA;Kutno;PL;;NIC: 05 ;;Udzielenie prawa;\\\\n385958;248268;2011-05-30;19/2011;2011-09-12;12/2012;2012-12-31;opaliSUN;S;POLFARMEX SP\\u00d3\\u0141KA AKCYJNA;Kutno;PL;;NIC: 05 ;;Udzielenie prawa;\\\\n385959;;2011-05-30;19/2011;2011-09-12;;;Eurolift;SG;EUROLIFT BOGACCY, LECH SP\\u00d3\\u0141KA JAWNA;Kalety;PL;;NIC: 12 37 ;VIE: 270501 ;Umorzenie post\\u0119powania;\\\\n385960;;2011-05-30;19/2011;2011-09-12;;;FB Millton;SG;FB MILLTON SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Koszalin;PL;Aneta Balwierz-Michalska KANCELARIA PATENTOWA;NIC: 35 36 ;VIE: 260418 270501 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385961;248269;2011-05-30;19/2011;2011-09-12;12/2012;2012-12-31;VENA lingerie;SG;ZALEWSKI MARIUSZ VENA;Bia\\u0142ystok;PL;;NIC: 25 ;VIE: 170202 260416 270501 290113 ;Udzielenie prawa;\\\\n385962;249525;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;JUHAS;SG;LACH ANDRZEJ, LACH DAWID FABRYKA DOM\\u00d3W Z DREWNA JUHAS SP\\u00d3\\u0141KA CYWILNA;Rajcza;PL;;NIC: 19 37 ;VIE: 050101 060708 270501 290113 ;Udzielenie prawa;\\\\n385963;249592;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;Tu i Teraz;S;ROZMYS\\u0141OWSKI TOMASZ;Ostrowiec \\u015awi\\u0119tokrzyski;PL;Eleonora Rozbicka INTERPAT, BIURO OCHRONY W\\u0141ASNO\\u015aCI INTELEKTUALNEJ;NIC: 10 11 35 37 44 ;;Udzielenie prawa;\\\\n385964;;2011-05-30;19/2011;2011-09-12;;;MYPO;SG;NGUYEN QUOC TAI;Raszyn;PL;;NIC: 30 33 35 ;VIE: 261105 270501 ;Umorzenie post\\u0119powania;\\\\n385965;;2011-05-30;19/2011;2011-09-12;;;Pegasus;S;WAWER AGATA;Kie\\u0142pin;PL;;NIC: 41 ;;Umorzenie post\\u0119powania;\\\\n385966;;2011-05-30;19/2011;2011-09-12;;;Green Bridge;S;WAWER AGATA;Kie\\u0142pin;PL;;NIC: 41 ;;Umorzenie post\\u0119powania;\\\\n385967;;2011-05-30;19/2011;2011-09-12;;;PATRIA;S;UZDROWISKO KRYNICA-\\u017bEGIEST\\u00d3W SP\\u00d3\\u0141KA AKCYJNA;Krynica-Zdr\\u00f3j;PL;J\\u00f3zef Guba\\u0142a BIURO PATENT\\u00d3W I ZNAK\\u00d3W TOWAROWYCH FAKTOR Q;NIC: 43 ;;Umorzenie post\\u0119powania;\\\\n385968;248976;2011-05-30;19/2011;2011-09-12;01/2013;2013-01-31;BAJGIEL;S;PPHU BAJGIEL WIES\\u0141AW REICHERT, JAN WODECKI SP\\u00d3\\u0141KA JAWNA;B\\u0119dzino;PL;Danuta Hryszkiewicz KANCELARIA PATENTOWA;NIC: 16 20 21 ;;Udzielenie prawa;\\\\n385969;253159;2011-05-30;19/2011;2011-09-12;06/2013;2013-06-28;z porywu serca;SG;ENEA SP\\u00d3\\u0141KA AKCYJNA;Pozna\\u0144;PL;Romuald Suszczewicz KANCELARIA PATENTOWA PATENTBOX ROMUALD SUSZCZEWICZ;NIC: 09 16 35 36 38 41 ;VIE: 020901 270501 290113 ;Udzielenie prawa;\\\\n385970;253160;2011-05-30;19/2011;2011-09-12;06/2013;2013-06-28;NIE TAKI PR\\u0104D STRASZNY;SG;ENEA SP\\u00d3\\u0141KA AKCYJNA;Pozna\\u0144;PL;Romuald Suszczewicz KANCELARIA PATENTOWA PATENTBOX ROMUALD SUSZCZEWICZ;NIC: 09 16 38 41 ;VIE: 150901 150910 270501 290114 ;Udzielenie prawa;\\\\n385971;250805;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;HEZNER;S;HEZNER KRZYSZTOF;Jaworzno;PL;Katarzyna Tabor-Kmiecik KANCELARIA PATENTOWA DR W. TABOR SP\\u00d3\\u0141KA JAWNA;NIC: 37 39 41 ;;Udzielenie prawa;\\\\n385972;249798;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;Ku\\u017ania Pa\\u0142ysz;SG;JASTRZ\\u0104BEK KRZYSZTOF KU\\u0179NIA PA\\u0141YSZ;Konopiska;PL;Anna Korbela AAK KANCELARIA PATENTOWA S.C. ANNA KORBELA, ARTUR KORBELA;NIC: 06 08 19 35 40 ;VIE: 261113 270501 290101 ;Udzielenie prawa;\\\\n385973;249799;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;MultiBac;S;KVAM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Ogorzele;PL;;NIC: 31 ;;Udzielenie prawa;\\\\n385974;249800;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;Absorbic;S;KVAM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Ogorzele;PL;;NIC: 31 ;;Udzielenie prawa;\\\\n385975;248929;2011-05-30;19/2011;2011-09-12;01/2013;2013-01-31;DigiOffice Group;SG;US\\u0141UGI TELETECHNICZNE PAWE\\u0141 KOZ\\u0141OWSKI;Warszawa;PL;\\u0141ukasz Sommer KANCELARIA PATENTOWA \\u0141UKASZ SOMMER;NIC: 37 ;VIE: 261106 261112 270501 290112 ;Udzielenie prawa;\\\\n385976;248822;2011-05-30;19/2011;2011-09-12;01/2013;2013-01-31;MIZENSA;S;ETOREBKA.PL JOANNA DORULA;Krak\\u00f3w;PL;\\u0141ukasz Sommer KANCELARIA PATENTOWA \\u0141UKASZ SOMMER;NIC: 18 25 35 ;;Udzielenie prawa;\\\\n385977;251356;2011-05-30;19/2011;2011-09-12;04/2013;2013-04-30;Tarasy Tynieckie;SG;ADAMUS ZENON;Krak\\u00f3w;PL;Leokadia Korga KANCELARIA RZECZNIKA PATENTOWEGO LEOKADIA KORGA;NIC: 29 30 43 ;VIE: 250722 251225 270501 290113 ;Udzielenie prawa;\\\\n385978;;2011-05-30;19/2011;2011-09-12;;;Polubisz za warto\\u015b\\u0107;S;GREEN FACTORY HOLDING SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Za\\u0142uski;PL;\\u0141ukasz Sommer KANCELARIA PATENTOWA \\u0141UKASZ SOMMER;NIC: 29 30 31 32 ;;Odmowa;\\\\n385979;265711;2011-05-30;19/2011;2011-09-12;09/2014;2014-09-30;Z gruntu najlepsze;S;GREEN FACTORY HOLDING SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Zdunowo;PL;\\u0141ukasz Sommer KANCELARIA PATENTOWA \\u0141UKASZ SOMMER;NIC: 29 30 31 32 ;;Udzielenie prawa;\\\\n385980;249803;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;bake baza;S;FARUTEX SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Szczecin;PL;;NIC: 29 30 35 39 42 43 ;;Udzielenie prawa;\\\\n385981;249804;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;bake baza;SG;FARUTEX SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Szczecin;PL;;NIC: 29 30 35 39 42 43 ;VIE: 080109 270501 290113 ;Udzielenie prawa;\\\\n385982;252063;2011-05-30;19/2011;2011-09-12;05/2013;2013-05-31;BZK KAPITA\\u0141;S;BZK TM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;;NIC: 16 35 36 38 41 45 ;;Udzielenie prawa;\\\\n385983;256670;2011-05-30;19/2011;2011-09-12;10/2013;2013-10-31;DOMEL;S;DOMEL MEBLE POD\\u0141OGI SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;K\\u0119pno;PL;Tomasz Szelwiga;NIC: 19 20 35 37 ;;Udzielenie prawa;\\\\n385984;249959;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;DOMEL;SG;DOMEL MEBLE POD\\u0141OGI SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;K\\u0119pno;PL;Tomasz Szelwiga;NIC: 19 20 35 37 ;VIE: 070108 260401 270501 290113 ;Udzielenie prawa;\\\\n385985;;2011-05-30;19/2011;2011-09-12;;;CALOFORT;S;Minteq UK Limited;Rawmarsh;GB;Jan Bucyk POLSERVICE KANCELARIA RZECZNIK\\u00d3W PATENTOWYCH SP. Z O. O.;NIC: 01 ;;Odmowa;\\\\n385986;252176;2011-05-30;19/2011;2011-09-12;05/2013;2013-05-31;SHIELD;S;WRZESI\\u0143SKI MAREK FIRMA HANDLOWA LEGEND;Wroc\\u0142aw;PL;Jan A. Bucyk POLSERVICE KANCELARIA RZECZNIK\\u00d3W PATENTOWYCH SP. Z O.O.;NIC: 28 ;;Udzielenie prawa;\\\\n385987;249650;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;GForce;S;RAIFFEISEN BANK POLSKA SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Jan A. Bucyk POLSERVICE KANCELARIA RZECZNIK\\u00d3W PATENTOWYCH SP. Z O.O.;NIC: 36 ;;Udzielenie prawa;\\\\n385988;249593;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;SKOWRON;SG;SKOWRON BEATA F.H.U POKRYCIA DACHOWE;Stasz\\u00f3w;PL;;NIC: 06 35 37 ;VIE: 070108 270101 270501 290112 ;Udzielenie prawa;\\\\n385989;250624;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;GBS Bank Do\\u0142\\u0105cz do znajomych;SG;GOSPODARCZY BANK SP\\u00d3\\u0141DZIELCZY W BARLINKU;Barlinek;PL;Aneta Balwierz-Michalska;NIC: 36 ;VIE: 261101 270101 270501 290103 ;Udzielenie prawa;\\\\n385990;;2011-05-30;19/2011;2011-09-12;;;FRIENDS;S;GO\\u0179DZICKA KRYSTYNA;Warszawa;PL;;NIC: 09 35 41 ;;Umorzenie post\\u0119powania;\\\\n385991;250625;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;GBS Bank Do\\u0142\\u0105cz do znajomych;SG;GOSPODARCZY BANK SP\\u00d3\\u0141DZIELCZY W BARLINKU;Barlinek;PL;Aneta Balwierz-Michalska;NIC: 36 ;VIE: 261101 270101 270501 290112 ;Udzielenie prawa;\\\\n385992;272184;2011-05-30;19/2011;2011-09-12;05/2015;2015-05-29;K&L;SG;K&L INWESTYCJE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Sopot;PL;Agnieszka Przyborska-Bojanowska KANCELARIA PRAWNO-PATENTOWA;NIC: 35 36 37 42 ;VIE: 260409 260418 270501 2819 290113 ;Udzielenie prawa;\\\\n385993;250626;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;GBS Bank Do\\u0142\\u0105cz do znajomych;SG;GOSPODARCZY BANK SP\\u00d3\\u0141DZIELCZY W BARLINKU;Barlinek;PL;Aneta Balwierz-Michalska;NIC: 36 ;VIE: 261101 270101 270501 290103 ;Udzielenie prawa;\\\\n385994;255415;2011-05-30;19/2011;2011-09-12;09/2013;2013-09-30;K&L. Nowoczesne domy i mieszkania w Tr\\u00f3jmie\\u015bcie;S;K&L INWESTYCJE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Sopot;PL;Agnieszka Przyborska-Bojanowska;NIC: 35 36 37 42 ;;Udzielenie prawa;\\\\n385995;251013;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;YORK Prestige;SG;YORK PL SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Bolechowo;PL;El\\u017cbieta Pi\\u0105tkowska KANCELARIA PATENTOWA;NIC: 16 20 21 24 35 ;VIE: 251225 260401 260402 270501 290113 ;Udzielenie prawa;\\\\n385996;;2011-05-30;19/2011;2011-09-12;;;AsTON;S;ASPEL SP\\u00d3\\u0141KA AKCYJNA;Zabierz\\u00f3w;PL;;NIC: 09 10 ;;Odmowa;\\\\n385997;;2011-05-30;19/2011;2011-09-12;;;KAREX P.P.H.U. Karol B\\u0119ben www.karex.agro.pl;SG;B\\u0118BEN KAROL PRZEDSI\\u0118BIORSTWO PRODUKCYJNO-HANDLOWO-US\\u0141UGOWE KAREX;Posmykowizna;PL;;NIC: 35 ;VIE: 051325 260102 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n385998;251234;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;powerauditing;S;MICZKA GABRIEL;Gliwice;PL;Leokadia Korga KANCELARIA RZECZNIKA PATENTOWEGO;NIC: 35 38 42 ;;Udzielenie prawa;\\\\n385999;251235;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;yourthermo;S;MICZKA GABRIEL;Gliwice;PL;Leokadia Korga KANCELARIA RZECZNIKA PATENTOWEGO;NIC: 35 38 42 ;;Udzielenie prawa;\\\\n386000;;2011-05-30;19/2011;2011-09-12;;;TYSAND;SG;TYSAND SP\\u00d3\\u0141KA JAWNA J. KRAWCZYKIEWICZ, K. RZEWUSKI;Gda\\u0144sk;PL;Wojciech Gierszewski BG Kancelaria prawno-patentowa;NIC: 01 19 35 37 39 42 ;VIE: 260402 270101 270501 290112 ;Umorzenie post\\u0119powania;\\\\n386001;252848;2011-05-30;19/2011;2011-09-12;05/2013;2013-05-31;Bajkowa Kraina PRZEDSZKOLE J\\u0118ZYKOWE;SG;MA\\u0141YSA MAGDALENA, RENATA KOPE\\u0106 PRZEDSZKOLE J\\u0118ZYKOWE BAJKOWA KRAINA;Warszawa;PL;;NIC: 41 43 44 ;VIE: 020704 270501 290112 ;Udzielenie prawa;\\\\n386002;254043;2011-05-30;19/2011;2011-09-12;07/2013;2013-07-31;YASUMI epil;SG;YASUMI SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Kalisz;PL;Jolanta Justy\\u0144ska;NIC: 35 44 ;VIE: 260402 270501 2807 290113 ;Udzielenie prawa;\\\\n386003;254044;2011-05-30;19/2011;2011-09-12;07/2013;2013-07-31;YASUMI slim;SG;YASUMI SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Kalisz;PL;Jolanta Justy\\u0144ska;NIC: 35 44 ;VIE: 270501 2807 290113 ;Udzielenie prawa;\\\\n386004;;2011-05-30;19/2011;2011-09-12;;;przyjaciel piekarz;SG;KIEDROWSCY SP\\u00d3\\u0141KA AKCYJNA;Lipusz;PL;Andrzej Grabowski BIURO PATENT\\u00d3W, LICENCJI I ZNAK\\u00d3W TOWAROWYCH;NIC: 30 ;VIE: 080101 080107 110304 260101 270501 290115 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386005;258108;2011-05-30;19/2011;2011-09-12;12/2013;2013-12-31;NATURAL COLA;SG;OSHEE POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Gra\\u017cyna Padee;NIC: 32 ;VIE: 251225 270501 ;Udzielenie prawa;\\\\n386006;251269;2011-05-30;19/2011;2011-09-12;04/2013;2013-04-30;Y;SG;YASUMI SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Kalisz;PL;Jolanta Justy\\u0144ska;NIC: 03 35 44 ;VIE: 260101 270101 2807 290112 ;Udzielenie prawa;\\\\n386007;258109;2011-05-30;19/2011;2011-09-12;12/2013;2013-12-31;OSHEE vitamin COLA;SG;OSHEE POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Gra\\u017cyna Padee;NIC: 32 ;VIE: 270501 ;Udzielenie prawa;\\\\n386008;;2011-05-30;19/2011;2011-09-12;;;cashcomeback;SG;CASH COME BACK SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Sierpc;PL;Piotr Kowalski KANCELARIA PATENTOWA INVENTIX SP. Z O.O.;NIC: 35 36 42 ;VIE: 270501 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386009;;2011-05-31;19/2011;2011-09-12;;;BRACKIE MASTNE 165-lecie JUBILEUSZ 165-LECIA BROWARU BRACKI BROWAR ZAMKOWY;SG;GRUPA \\u017bYWIEC SP\\u00d3\\u0141KA AKCYJNA;\\u017bywiec;PL;;NIC: 32 ;VIE: 051325 070108 250115 261103 270501 290113 050109 051307 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386010;258110;2011-05-30;19/2011;2011-09-12;12/2013;2013-12-31;OSHEE vitamin ICE TEA;SG;OSHEE POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Gra\\u017cyna Padee;NIC: 32 ;VIE: 270501 ;Udzielenie prawa;\\\\n386011;;2011-05-30;19/2011;2011-09-12;;;SENSEOF Bio;SG;SZUSTER WOJCIECH;Katowice;PL;;NIC: 03 ;VIE: 261101 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386012;250951;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;MOTIVE GLASS;SG;MOTIVEGLASS SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;;NIC: 37 40 ;VIE: 250725 270501 290114 ;Udzielenie prawa;\\\\n386013;249766;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;KOHLMAN;SG;DG SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Straszyn;PL;Jacek Kwapisz;NIC: 11 ;VIE: 290113 260402 270501 ;Udzielenie prawa;\\\\n386014;249526;2011-07-20;22/2011;2011-10-24;02/2013;2013-02-28;DOMOWA ZE WSI;S;ALL SPICE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Nowy Dziekan\\u00f3w;PL;Aneta Chmura;NIC: 30 ;;Udzielenie prawa;\\\\n386015;250518;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;PREFIX;SG;SIG SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;Katarzyna Tabor-Kmiecik KANCELARIA PATENTOWA DR. W. TABOR;NIC: 01 02 03 06 17 19 20 35 ;VIE: 260409 261509 270501 290114 ;Udzielenie prawa;\\\\n386016;;2011-05-30;19/2011;2011-09-12;;;Grzaniec kawowy;S;ZAWI\\u015aLAK HENRYK;Dziwn\\u00f3wek;PL;;NIC: 21 30 33 ;;Odmowa;\\\\n386017;;2011-05-30;19/2011;2011-09-12;;;Condensa;SG;ROTR SP\\u00d3\\u0141DZIELNIA MLECZARSKA W RYPINIE;Rypin;PL;;NIC: 29 ;VIE: 261101 270501 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386018;254277;2011-05-30;19/2011;2011-09-12;07/2013;2013-07-31;i Intelgraf systems;SG;INTELGRAF SYSTEMS SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Grodzisk Mazowiecki;PL;Micha\\u0142 J\\u0119drzejewski JARZYNKA I WSP\\u00d3LNICY KANCELARIA PRAWNO-PATENTOWA SP\\u00d3\\u0141KA JAWNA;NIC: 37 42 ;VIE: 260205 270501 290113 ;Uniewa\\u017cnienie prawa ochronnego;\\\\n386019;;2011-05-30;19/2011;2011-09-12;;;FOTOMODA;S;KASPERSKI OLAF S\\u0141AWOMIR-OLAF KASPERSKI;Warszawa;PL;;NIC: 35 38 41 42 ;;Odmowa;\\\\n386020;;2011-05-30;19/2011;2011-09-12;;;Delik MLEKO DO CAPPUCCINO;SG;ROTR SP\\u00d3\\u0141DZIELNIA MLECZARSKA W RYPINIE;Rypin;PL;;NIC: 29 ;VIE: 270501 290115 010302 050519 110304 190303 261101 ;Umorzenie post\\u0119powania;\\\\n386021;250891;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;Sweat Lodge Daj sobie wycisk;S;OLSZEWSKA BARBARA STUDIO KREATYWNO\\u015aCI;Warszawa;PL;;NIC: 35 38 39 41 43 44 ;;Udzielenie prawa;\\\\n386022;250892;2011-05-30;19/2011;2011-09-12;03/2013;2013-03-29;SWEAT LODGE www.dajsobiewycisk.pl;SG;OLSZEWSKA BARBARA STUDIO KREATYWNO\\u015aCI;Warszawa;PL;;NIC: 35 38 39 41 43 44 ;VIE: 020108 020308 261102 270501 ;Udzielenie prawa;\\\\n386023;;2011-05-30;19/2011;2011-09-12;;;ROTR Blanco MLEKO DLA BARIST\\u00d3W BARISTA MILK;SG;ROTR SP\\u00d3\\u0141DZIELNIA MLECZARSKA W RYPINIE;Rypin;PL;;NIC: 29 ;VIE: 050311 110304 190303 260401 261101 270501 290115 ;Umorzenie post\\u0119powania;\\\\n386024;;2011-05-30;19/2011;2011-09-12;;;Slim - Tw\\u00f3j styl. Delik Slim mleko 0,0 %;SG;ROTR SP\\u00d3\\u0141DZIELNIA MLECZARSKA W RYPINIE;Rypin;PL;;NIC: 29 ;VIE: 190303 241705 270501 270701 290115 010302 020305 020921 050311 ;Umorzenie post\\u0119powania;\\\\n386025;249594;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;A MINCER Pharma SUPER MEN ENERGY ANTYPERSPIRANT;SG;MINCER JANINA MCR CORPORATION JANINA MINCER, MINCER CORPORATION MONA-LIZA COSMETIC FRANCE;Micha\\u0142owice;PL;;NIC: 03 ;VIE: 011509 031101 031103 240903 261103 270501 290115 ;Udzielenie prawa;\\\\n386026;;2011-05-30;19/2011;2011-09-12;;;A MINCER Pharma With Vit. A,e,F VICTORIA beauty NIGHT REGENERATION REGENERATING CREAM for hands & nails with vitamins & lanolin R\\u00c9G\\u00c9N\\u00c9RATION CR\\u00c8ME pour les mains & ongles de nuit avec les witamines & lanoline KREM REGENERACYJNY do r\\u0105k i paznokci na noc z witaminami i lanolin\\u0105 SECURITY - TOTAL;SG;MINCER JANINA MCR CORPORATION JANINA MINCER, MINCER CORORPORATION MONA-LIZA COSMETIC FRANCE;Micha\\u0142owice;PL;;NIC: 03 ;VIE: 011515 020914 261101 270501 290115 ;Odmowa;\\\\n386027;249595;2011-05-30;19/2011;2011-09-12;02/2013;2013-02-28;A MINCER Pharma Anti CARE allergique PROFILAKTYCZNY \\u017bEL DO HIGIENY INTYMNEJ i mycia cia\\u0142a do sk\\u00f3ry wra\\u017cliwej ALOES I K\\u0141\\u0104CZA PI\\u0118CIORNIKA LEKARSKIEGO GEL FOR INTIMATE HYGIENE and Body Wash for sensitive skin ALOE VERA and POTENTILLA ERECTA kwas mlekowy + d-Panthenol + alantoina COMPANY PRIZE-WINNER;SG;MINCER JANINA MCR CORPORATION - JANINA MINCER, MINCER CORPORATION MONA - LIZA COSMETIC FRANCE;Micha\\u0142owice;PL;;NIC: 03 ;VIE: 050519 051117 260402 270501 290114 ;Udzielenie prawa;\\\\n386028;;2011-08-17;24/2011;2011-11-21;;;MACARONI CARTONI;SG;PARNAS TOMASZ;Warszawa;PL;;NIC: 43 ;VIE: 240701 270501 290114 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386029;;2011-05-31;19/2011;2011-09-12;;;POMARA\\u0143CZA;S;AGRO-BIZNES SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Bielsko-Bia\\u0142a;PL;Joanna Kuli\\u0144ska KANCELARIA RZECZNIKA PATENTOWEGO;NIC: 41 43 ;;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386030;249527;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;Volric;SG;ZAK\\u0141ADY FARMACEUTYCZNE POLPHARMA SP\\u00d3\\u0141KA AKCYJNA;Starogard Gda\\u0144ski;PL;;NIC: 05 ;VIE: 270501 280500 ;Wyga\\u015bni\\u0119cie prawa ochronnego;\\\\n386031;;2011-05-31;19/2011;2011-09-12;;;Mementis.pl ZADBAMY O WSZYSTKO;SG;MEMENTIS SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Wroc\\u0142aw;PL;Ryszard Surma;NIC: 35 36 38 41 42 45 ;VIE: 050103 260401 260416 261301 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386032;;2011-05-31;19/2011;2011-09-12;;;Valsa combi;SG;ZAK\\u0141ADY FARMACEUTYCZNE POLPHARMA SP\\u00d3\\u0141KA AKCYJNA;Starogard Gda\\u0144ski;PL;;NIC: 05 ;VIE: 280500 270501 ;Zg\\u0142oszenie opublikowane;\\\\n386033;249528;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;PRO ASSISTANCE;SG;PRO ASSISTANCE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;Grzegorz M\\u0142oczkowski KANCELARIA RZECZNIKA PATENTOWEGO PATENT-SERVICE;NIC: 36 ;VIE: 261325 270501 290114 ;Udzielenie prawa;\\\\n386034;251236;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;GOORES;SG;SPORT ONLY SP\\u00d3\\u0141KA CYWILNA JAWORSKI ARTUR SZYMANOWSKI WOJCIECH;\\u015arem;PL;Pawe\\u0142 G\\u00f3rnicki  BIURO OCHRONY W\\u0141ASNO\\u015aCI INTELEKTUALNEJ PATENT-SERVICE;NIC: 25 ;VIE: 260102 260118 270501 ;Udzielenie prawa;\\\\n386035;;2011-05-31;19/2011;2011-09-12;;;COFFEE BY COFFEE;S;BOBA PIOTR;Szczecin;PL;Grzegorz Psiorz;NIC: 38 41 42 43 ;;Umorzenie post\\u0119powania;\\\\n386036;;2011-05-31;19/2011;2011-09-12;;;YOGO FRUIT;S;BOBA PIOTR;Szczecin;PL;Grzegorz Psiorz;NIC: 29 30 38 42 ;;Umorzenie post\\u0119powania;\\\\n386037;;2011-05-31;19/2011;2011-09-12;;;ENJOY YOUR COFFEE;S;BOBA PIOTR;Szczecin;PL;Grzegorz Psiorz;NIC: 38 41 42 43 ;;Umorzenie post\\u0119powania;\\\\n386038;;2011-05-31;19/2011;2011-09-12;;;MR. BROWN;SG;MARCINKOWSKI PAWE\\u0141 VICTOR;Bielany Wroc\\u0142awskie;PL;Magdalena Drozd-Rudnicka KANCELARIA PATENTOWA PATENT-DROZD;NIC: 30 32 35 ;VIE: 270501 ;Odmowa;\\\\n386039;251071;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;ESSETIL COMPLEX;S;NORD FARM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;;NIC: 05 ;;Udzielenie prawa;\\\\n386040;251072;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;CALCIPREV;S;SUN-FARM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141omianki;;Hanna Dreszer-Licha\\u0144ska;NIC: 05 ;;Udzielenie prawa;\\\\n386041;250952;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;colorovo;SG;ABC DATA MARKETING SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;Magdalena Pietrosiuk JAN WIERZCHO\\u0143 & PARTNERZY - BIURO PATENT\\u00d3W I ZNAK\\u00d3W TOWAROWYCH SP.J.;NIC: 02 09 16 ;VIE: 260401 260409 270501 290115 ;Udzielenie prawa;\\\\n386042;;2011-05-31;19/2011;2011-09-12;;;Wy\\u017csza Szko\\u0142a Nauk Spo\\u0142ecznych im. Ks. J\\u00f3zefa Majki;S;WY\\u017bSZA SZKO\\u0141A NAUK SPO\\u0141ECZNYCH IM. KS. J\\u00d3ZEFA MAJKI W MI\\u0143SKU MAZOWIECKIM;Mi\\u0144sk Mazowiecki;PL;;NIC: 35 41 45 ;;Umorzenie post\\u0119powania;\\\\n386043;257495;2011-05-31;19/2011;2011-09-12;11/2013;2013-11-29;R KS RUCH 1919 RADZIONK\\u00d3W;SG;KLUB SPORTOWY RUCH RADZIONK\\u00d3W;Radzionk\\u00f3w;PL;Justyna Duda;NIC: 35 41 43 ;VIE: 210301 241118 250503 270101 270501 290114 ;Udzielenie prawa;\\\\n386044;251199;2011-06-01;19/2011;2011-09-12;03/2013;2013-03-29;RUNO Melton SP\\u00d3\\u0141KA Z O.O.;SG;PRZEDSI\\u0118BIORSTWO PRODUKCYJNO-HANDLOWE RUNO JAN WIDZ;Przybor\\u00f3w;PL;Alicja Rumpel RUMPEL Sp\\u00f3\\u0142ka Komandytowa;NIC: 24 ;VIE: 260102 260402 270501 290113 ;Udzielenie prawa;\\\\n386045;;2011-06-01;19/2011;2011-09-12;;;Netia, wspieramy Tw\\u00f3j biznes;S;NETIA SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Miros\\u0142aw Zdu\\u0144czuk NETIA S.A.;NIC: 38 ;;Umorzenie post\\u0119powania;\\\\n386046;253353;2011-05-31;19/2011;2011-09-12;06/2013;2013-06-28;SPIKE NEW GENERATION OF MUSIC;SG;KLIM ROBERT;Kowale;PL;Agnieszka Iwaniuk KANCELARIA PRAWNO-PATENTOWA RZECZNICY PATENTOWI DOBKOWSKA IWANIUK SP\\u00d3\\u0141KA PARTNERSKA;NIC: 35 ;VIE: 270501 290112 ;Umorzenie post\\u0119powania;\\\\n386047;249529;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;HUMANA MEDICA OMEDA;SG;HUMANA MEDICA OMEDA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Bia\\u0142ystok;PL;Agnieszka Iwaniuk KANCELARIA PRAWNO-PATENTOWA RZECZNICY PATENTOWI DOBKOWSKA IWANIUK SP\\u00d3\\u0141KA PARTNERSKA;NIC: 39 42 44 ;VIE: 040505 270501 290112 ;Udzielenie prawa;\\\\n386048;;2011-05-31;19/2011;2011-09-12;;;WY\\u017bSZA SZKO\\u0141A NAUK SPO\\u0141ECZNYCH WSNS im. ks. J\\u00f3zefa Majki;SG;WY\\u017bSZA SZKO\\u0141A NAUK SPO\\u0141ECZNYCH IM. KS. J\\u00d3ZEFA MAJKI W MI\\u0143SKU MAZOWIECKIM;Mi\\u0144sk Mazowiecki;PL;;NIC: 35 41 45 ;VIE: 010101 010105 010706 260402 270501 290114 ;Odmowa;\\\\n386049;;2011-05-31;19/2011;2011-09-12;;;WSGE;S;WY\\u017bSZA SZKO\\u0141A GOSPODARKI EUROREGIONALNEJ IM. ALCIDE DE GASPERI;J\\u00f3zef\\u00f3w;PL;;NIC: 16 35 41 42 45 ;;Umorzenie post\\u0119powania;\\\\n386050;;2011-05-31;19/2011;2011-09-12;;;Wy\\u017csza Szko\\u0142a Gospodarki Euroregionalnej;S;WY\\u017bSZA SZKO\\u0141A GOSPODARKI EUROREGIONALNEJ IM. ALCIDE DE GASPERI;J\\u00f3zef\\u00f3w;PL;;NIC: 16 35 41 42 45 ;;Odmowa;\\\\n386051;249531;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;FSM Forum Sp\\u00f3\\u0142dzielczo\\u015bci Mleczarskiej;SG;FIRST COMMUNICATIONS AGNIESZKA MALISZEWSKA;Bia\\u0142ystok;PL;Agnieszka Iwaniuk;NIC: 16 35 41 42 ;VIE: 200511 200515 260101 261102 270501 290112 ;Udzielenie prawa;\\\\n386052;;2011-05-31;19/2011;2011-09-12;;;WY\\u017bSZA SZKO\\u0141A GOSPODARKI EUROREGIONALNEJ im. Alcide De Gasperi w J\\u00f3zefowie;SG;WY\\u017bSZA SZKO\\u0141A GOSPODARKI EUROREGIONALNEJ IM. ALCIDE DE GASPERI;J\\u00f3zef\\u00f3w;PL;;NIC: 16 35 41 42 45 ;VIE: 010101 260101 261102 270501 290115 ;Odmowa;\\\\n386053;249651;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;Naturell, producent preparatu Iskial, wzmacniaj\\u0105cego i podnosz\\u0105cego odporno\\u015b\\u0107;S;Unilab, LP;Rockville;US;Mariusz Kondrat;NIC: 35 ;;Udzielenie prawa;\\\\n386054;251643;2011-05-31;19/2011;2011-09-12;04/2013;2013-04-30;estolik.pl REZERWUJ ON-LINE;SG;SOUTH ISLAND PLACE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;;NIC: 35 41 43 ;VIE: 110101 270501 290101 ;Udzielenie prawa;\\\\n386055;;2011-05-31;19/2011;2011-09-12;;;FANCLUB;SG;PUHIT SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Anna Rowi\\u0144ska Agencja Ochrony W\\u0142asno\\u015bci Intelektualnej ANIPAT;NIC: 03 04 09 14 15 16 18 20 21 24 25 28 29 30 32 33 34 35 36 38 39 41 43 ;VIE: 020125 040502 270501 290115 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386056;;2011-05-31;19/2011;2011-09-12;;;HAPPY Baby;SG;WITOS ANETA EUROGAL;Nowy S\\u0105cz;PL;Cezary Radecki KANCELARIA PATENTOWA RADECKI;NIC: 12 20 28 ;VIE: 260102 270501 290114 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386057;;2011-05-31;19/2011;2011-09-12;;;FANCLUB;SG;PUHIT SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Anna Rowi\\u0144ska Agencja Ochrony W\\u0142asno\\u015bci Intelektualnej ANIPAT;NIC: 30 33 34 ;VIE: 040502 270501 290115 020104 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386058;249652;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;Naturell, producent preparatu Silica wzmacniaj\\u0105cego w\\u0142osy, sk\\u00f3r\\u0119 i paznokcie;S;NATURELL POLSKA SP\\u00d3\\u0141KA AKCYJNA;Krak\\u00f3w;PL;;NIC: 35 ;;Udzielenie prawa;\\\\n386059;;2011-05-31;19/2011;2011-09-12;;;FANCLUB;SG;PUHIT SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Anna Rowi\\u0144ska Agencja Ochrony W\\u0142asno\\u015bci Intelektualnej ANIPAT;NIC: 30 33 34 ;VIE: 020104 040502 270501 290115 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386060;249283;2011-05-31;19/2011;2011-09-12;01/2013;2013-01-31;Monumenta;S;B\\u0141OCHOWIAK WIES\\u0141AW TOPVIT;Swarz\\u0119dz;PL;;NIC: 16 41 ;;Udzielenie prawa;\\\\n386061;251014;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;TechnoBoard;SG;TECHNOBOARD SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;;NIC: 36 ;VIE: 160106 261515 270501 290115 ;Udzielenie prawa;\\\\n386062;249653;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;Naturell, producent preparatu Omega-3 wzmacniaj\\u0105cego serce i uk\\u0142ad kr\\u0105\\u017cenia;S;NATURELL POLSKA SP\\u00d3\\u0141KA AKCYJNA;Krak\\u00f3w;PL;;NIC: 35 ;;Udzielenie prawa;\\\\n386063;249530;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;Xpresso;S;MAZOWIECKA WYTW\\u00d3RNIA W\\u00d3DEK I DRO\\u017bD\\u017bY POLMOS SP\\u00d3\\u0141KA AKCYJNA;J\\u00f3zef\\u00f3w k/B\\u0142onia;PL;;NIC: 33 ;;Umorzenie post\\u0119powania;\\\\n386064;248930;2011-05-31;19/2011;2011-09-12;01/2013;2013-01-31;MEGACHEMIE Research & Technologies;S;MEGACHEMIE RESEARCH & TECHNOLOGIES SP\\u00d3\\u0141KA AKCYJNA;Krak\\u00f3w;PL;Katarzyna Tabor-Kmiecik Kancelaria Patentowa Dr W. Tabor Sp\\u00f3\\u0142ka Jawna;NIC: 02 17 19 35 37 42 45 ;;Udzielenie prawa;\\\\n386065;;2011-05-31;19/2011;2011-09-12;;;alkoholowy zawr\\u00f3t g\\u0142owy;SG;BRUKNER MICHA\\u0141 A.B.M SYSTEM;Warszawa;PL;ARKADIUSZ BRUKNER;NIC: 35 ;VIE: 260301 260401 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386066;249284;2011-05-31;19/2011;2011-09-12;01/2013;2013-01-31;megachemie;SG;MEGACHEMIE Research & Technologies Sp\\u00f3\\u0142ka Akcyjna;Krak\\u00f3w;PL;Katarzyna Tabor-Kmiecik Kancelaria Patentowa Dr W. Tabor Sp\\u00f3\\u0142ka Jawna;NIC: 02 17 19 35 37 42 45 ;VIE: 270501 290101 ;Udzielenie prawa;\\\\n386067;;2011-05-31;19/2011;2011-09-12;;;\\u017bYCIE PISZE HISTORIE PRIMA NADAJE IM SMAK;S;PRIMA POLAND SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Pozna\\u0144;PL;Pawe\\u0142 Wac POLSERVICE KANCELARIA RZECZNIK\\u00d3W PATENTOWYCH SP. Z O.O.;NIC: 30 ;;Odmowa;\\\\n386068;250953;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;M\\u0142yn;SG;KARCZMA M\\u0141YN s.r.o.;Ko\\u0161ice;SK;Barbara Wdowicka GROSSTECHMED;NIC: 33 35 43 ;VIE: 020901 270501 ;Udzielenie prawa;\\\\n386069;251074;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;Gamander;SG;NOZDERKA ANNA WYDAWNICTWO GAMANDER;Konstancin-Jeziorna;PL;Micha\\u0142 J\\u0119drzejewski JARZYNKA I WSP\\u00d3LNICY KANCELARIA PRAWNO-PATENTOWA SP\\u00d3\\u0141KA JAWNA;NIC: 09 16 20 41 ;VIE: 050520 260401 270501 290113 ;Udzielenie prawa;\\\\n386070;249532;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;MC MISTERS CONSULTING;SG;LUBI\\u0143SKA-STASIAK BARBARA;Warszawa;PL;;NIC: 35 36 ;VIE: 240301 270501 290112 ;Udzielenie prawa;\\\\n386071;;2011-05-31;19/2011;2011-09-12;;;job abroad;SG;KBM INVEST SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Pozna\\u0144;PL;;NIC: 35 41 ;VIE: 260402 260418 270501 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386072;;2011-05-31;19/2011;2011-09-12;;;WARSAW STUDY CENTRE;SG;WARSAW STUDY CENTRE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104 SP\\u00d3\\u0141KA KOMANDYTOWA;Warszawa;PL;;NIC: 16 41 ;VIE: 260101 260401 260409 260418 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386073;;2011-05-31;19/2011;2011-09-12;;;replika;SG;INVEST-PLUS BIURO INWESTYCYJNE BUDOWNICTWA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Bydgoszcz;PL;Zenon Ko\\u0142odziejczyk KANCELARIA PATENTOWA;NIC: 35 37 42 44 ;VIE: 260401 260503 261101 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386074;;2011-05-31;19/2011;2011-09-12;;;FUNKY FRESH;S;EKOSMAKI, BIENCZYK, KILIAN SP\\u00d3\\u0141KA JAWNA;Siemianowice \\u015al\\u0105skie;PL;Renata Sobajda KANCELARIA PATENTOWA \\u0141UKASZYK;NIC: 43 ;;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386075;251937;2011-05-31;19/2011;2011-09-12;04/2013;2013-04-30;CULTUROVO;S;ART MEDIA \\u0141ASKAWIEC SP\\u00d3\\u0141KA JAWNA;Wroc\\u0142aw;PL;;NIC: 35 36 41 45 ;;Udzielenie prawa;\\\\n386076;250468;2011-05-31;19/2011;2011-09-12;03/2013;2013-03-29;GD TRADE;SG;G.D. TRADE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;P\\u0142ock;PL;Bart\\u0142omiej Tomaszewski KANCELARIA PATENTOWA;NIC: 01 03 04 12 35 ;VIE: 270501 290113 ;Udzielenie prawa;\\\\n386077;250014;2011-05-31;19/2011;2011-09-12;02/2013;2013-02-28;ApiKid;S;FARMINA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Krak\\u00f3w;PL;;NIC: 05 ;;Udzielenie prawa;\\\\n386078;252018;2011-05-31;19/2011;2011-09-12;04/2013;2013-04-30;1995 ABIIT NON OBIIT G\\u00f3rno\\u015bl\\u0105ska Wy\\u017csza Szko\\u0142a Pedagogiczna im. Kardyna\\u0142a Augusta Hlonda;SG;G\\u00d3RNO\\u015aL\\u0104SKA WY\\u017bSZA SZKO\\u0141A PEDAGOGICZNA IM. KARDYNA\\u0141A AUGUSTA HLONDA;Mys\\u0142owice;PL;;NIC: 41 ;VIE: 240105 240109 240120 270501 270701 290115 ;Udzielenie prawa;\\\\n386079;;2011-05-31;19/2011;2011-09-12;;;EQUIP wholesale system;SG;PFLEIDERER PROSPAN SP\\u00d3\\u0141KA AKCYJNA,  PFLEIDERER GRAJEWO SP\\u00d3\\u0141KA AKCYJNA,  PFLEIDERER MDF SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Wierusz\\u00f3w, Grajewo, Grajewo;PL, PL, PL;;NIC: 35 42 ;VIE: 260402 260418 270501 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386080;250015;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;CONSILIO;S;OLYMPUS POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;Jaros\\u0142aw Rawa KANCELARIA PATENTOWA RAWA & RAWA SP\\u00d3\\u0141KA JAWNA;NIC: 05 09 10 35 38 41 42 44 ;;Udzielenie prawa;\\\\n386081;250016;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;CONSILIO;SG;OLYMPUS POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;Jaros\\u0142aw Rawa KANCELARIA PATENTOWA RAWA & RAWA SP\\u00d3\\u0141KA JAWNA;NIC: 05 09 10 35 38 41 42 44 ;VIE: 270501 290104 ;Udzielenie prawa;\\\\n386082;251606;2011-06-01;19/2011;2011-09-12;04/2013;2013-04-30;embajador;S;ATLANTIC SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Magdalena Pietrosiuk JWP Rzecznicy Patentowi Dorota Rz\\u0105\\u017cewska sp.j.;NIC: 03 18 25 ;;Udzielenie prawa;\\\\n386083;256922;2011-06-01;19/2011;2011-09-12;10/2013;2013-10-31;ATLANTIC;S;VIA MODA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;Jakub Skrzypczak;NIC: 03 18 ;;Udzielenie prawa;\\\\n386084;;2011-06-01;19/2011;2011-09-12;;;KLIXI MIXI;S;EPEE POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Szczecin;PL;Grzegorz Psiorz;NIC: 16 28 ;;Umorzenie post\\u0119powania;\\\\n386085;;2011-06-01;19/2011;2011-09-12;;;Prehistoryczne OCEANARIUM;S;MOSKA\\u0141A \\u0141UKASZ, SZWERYN MOSKA\\u0141A AGATA BUDGAST SP\\u00d3\\u0141KA CYWILNA;Skocz\\u00f3w;PL;Walter Caputa ZAK\\u0141AD US\\u0141UG OCHRONY W\\u0141ASNO\\u015aCI PRZEMYS\\u0141OWEJ I WDRO\\u017bE\\u0143;NIC: 35 ;;Odmowa;\\\\n386086;;2011-06-01;19/2011;2011-09-12;;;Prehistoryczne AKWARIUM;S;MOSKA\\u0141A \\u0141UKASZ, SZWERYN MOSKA\\u0141A AGATA BUDGAST SP\\u00d3\\u0141KA CYWILNA;Skocz\\u00f3w;PL;Walter Caputa ZAK\\u0141AD US\\u0141UG OCHRONY W\\u0141ASNO\\u015aCI PRZEMYS\\u0141OWEJ I WDRO\\u017bE\\u0143;NIC: 35 ;;Odmowa;\\\\n386087;250017;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;Budgast;SG;MOSKA\\u0141A \\u0141UKASZ, SZWERYN MOSKA\\u0141A AGATA BUDGAST SP\\u00d3\\u0141KA CYWILNA;Skocz\\u00f3w;PL;Walter Caputa ZAK\\u0141AD US\\u0141UG OCHRONY W\\u0141ASNO\\u015aCI PRZEMYS\\u0141OWEJ I WDRO\\u017bE\\u0143;NIC: 41 ;VIE: 290114 250501 260404 270501 ;Udzielenie prawa;\\\\n386088;250018;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;COCOFAN;S;POLMOS J\\u00d3ZEF\\u00d3W SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;J\\u00f3zef\\u00f3w;PL;;NIC: 33 ;;Udzielenie prawa;\\\\n386089;250019;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;THIOMUCASE;S;ALMIRALL S.A.;BARCELONA;ES;Marek \\u0141azewski LDS \\u0141AZEWSKI, DEPO I WSP\\u00d3LNICY SP. K.;NIC: 03 05 ;;Udzielenie prawa;\\\\n386090;250020;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;Altacet Ice. I szybciej wracasz do gry.;S;LEK SP\\u00d3\\u0141KA AKCYJNA;Stryk\\u00f3w;PL;Marek \\u0141azewski LDS \\u0141AZEWSKI, DEPO I WSP\\u00d3LNICY SP. K.;NIC: 05 ;;Udzielenie prawa;\\\\n386091;;2011-06-01;19/2011;2011-09-12;;;blubird.;SG;GREGORCZUK MARCIN;Siedlce;PL;;NIC: 28 ;VIE: 030721 030724 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386092;251938;2011-06-01;19/2011;2011-09-12;04/2013;2013-04-30;MABAU;SG;MABAU POLSKA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Szyman\\u00f3w;PL;;NIC: 19 37 39 ;VIE: 260401 260418 270501 290112 ;Udzielenie prawa;\\\\n386093;;2011-06-01;19/2011;2011-09-12;;;OWOCOWA EXPLOZJA SMAKU;SG;SKRZESI\\u0143SKI KAMIL, SKRZESI\\u0143SKI KRZYSZTOF VIJAY DISTRIBUTION SP\\u00d3\\u0141KA CYWILNA;\\u017bory;PL;Joanna Marek KANCELARIA PATENTOWA WIMA-PATENT;NIC: 30 ;VIE: 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386094;252019;2011-06-01;19/2011;2011-09-12;04/2013;2013-04-30;Z\\u0141OTA NITKA;SG;EXPO-\\u0141\\u00d3D\\u0179 SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;\\u0141\\u00f3d\\u017a;PL;Katarzyna Kwestarz;NIC: 35 38 41 ;VIE: 090101 090501 261103 261107 261109 ;Udzielenie prawa;\\\\n386095;;2011-06-01;19/2011;2011-09-12;;;NC NATURA CENTRUM;SG;NATURA CENTRUM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Warszawa;PL;;NIC: 41 43 44 ;VIE: 030707 030724 270501 290103 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386096;250021;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;PSPN Polskie Stowarzyszenie P\\u0142ywania Niemowl\\u0105t www.pspn.org;SG;POLSKIE STOWARZYSZENIE P\\u0141YWANIA NIEMOWL\\u0104T;\\u0141\\u00f3d\\u017a;PL;;NIC: 35 41 45 ;VIE: 011521 020501 260101 260124 270501 290113 ;Udzielenie prawa;\\\\n386097;249285;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;BERYL;S;FABRYKA BRONI \\u0141UCZNIK - RADOM SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Radom;PL;Gra\\u017cyna Basa KANCELARIA PATENTOWA BASA GRA\\u017bYNA;NIC: 13 ;;Udzielenie prawa;\\\\n386098;250347;2011-06-01;19/2011;2011-09-12;03/2013;2013-03-29;;G;WIELKOPOLSKIE STOWARZYSZENIE WOLONTARIUSZY OPIEKI PALIATYWNEJ HOSPICJUM DOMOWE;Pozna\\u0144;PL;;NIC: 44 ;VIE: 020723 020725 290112 ;Udzielenie prawa;\\\\n386099;;2011-06-01;19/2011;2011-09-12;;;BAM BAM STUDIO;S;NAPI\\u00d3RKOWSKA KAROLINA BAM BAM STUDIO;Warszawa;PL;;NIC: 41 43 45 ;;Odmowa;\\\\n386100;249960;2011-06-02;19/2011;2011-09-12;02/2013;2013-02-28;ALARMMONIT ELEKTRONICZNE SYSTEMY ZABEZPIECZE\\u0143;SG;MUSIA\\u0141 JACEK, MRUKOT MATEUSZ ALARMMONIT ELEKTRONICZNE SYSTEMY ZABEZPIECZE\\u0143 AGENCJA OCHRONY VIP SP\\u00d3\\u0141KA CYWILNA;Wola Zabierzowska;PL;Magdalena Filipek-Marzec KANCELARIA PRAWNO-PATENTOWA RZECZNIK PATENTOWY MAGDALENA FILIPEK-MARZEC;NIC: 09 37 38 42 ;VIE: 260105 261102 261112 270501 290113 ;Udzielenie prawa;\\\\n386101;263100;2011-06-02;19/2011;2011-09-12;06/2014;2014-06-30;VIP AGENCJA OCHRONY;SG;MUSIA\\u0141 JACEK, MRUKOT MATEUSZ ALARMMONIT ELEKTRONICZNE SYSTEMY ZABEZPIECZE\\u0143 AGENCJA OCHRONY VIP SP\\u00d3\\u0141KA CYWILNA;Wola Zabierzowska;PL;Magdalena Filipek-Marzec KANCELARIA PRAWNO-PATENTOWA;NIC: 41 45 ;VIE: 010101 010105 010110 260504 260518 270501 290114 ;Udzielenie prawa;\\\\n386102;249654;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;MISTRALL THE BEST FOR FISHING;SG;PRZEDSI\\u0118BIORSTWO PRODUKCYJNO-HANDLOWE LESZCZ TOMASZ ST\\u0118PIE\\u0143, WOJCIECH ST\\u0118PIE\\u0143 SP\\u00d3\\u0141KA JAWNA;Radom;PL;;NIC: 08 28 ;VIE: 030901 030924 270501 290112 ;Udzielenie prawa;\\\\n386103;249286;2011-06-01;19/2011;2011-09-12;01/2013;2013-01-31;SHIRO;SG;PRZEDSI\\u0118BIORSTWO PRODUKCYJNO-HANDLOWE LESZCZ TOMASZ ST\\u0118PIE\\u0143, WOJCIECH ST\\u0118PIE\\u0143 SP\\u00d3\\u0141KA JAWNA;Radom;PL;;NIC: 08 28 ;VIE: 270501 290113 030901 030924 ;Udzielenie prawa;\\\\n386104;249287;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;BUDUJ\\u0104CE POMYS\\u0141Y DLA DOMU;S;GRUPA PSB HANDEL SP\\u00d3\\u0141KA AKCYJNA;We\\u0142ecz;PL;Gra\\u017cyna Basa;NIC: 35 ;;Udzielenie prawa;\\\\n386105;249288;2011-06-01;19/2011;2011-09-12;01/2013;2013-01-31;CARTE D\\\\\'OR;S;UNILEVER N.V.;Rotterdam;NL;Marcin Fija\\u0142kowski BAKER & MCKENZIE GRUSZCZY\\u0143SKI I WSP\\u00d3LNICY KANCELARIA PRAWNA SP\\u00d3\\u0141KA KOMANDYTOWA;NIC: 43 ;;Udzielenie prawa;\\\\n386106;249289;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;BUDUJ\\u0104CE POMYS\\u0141Y;S;GRUPA PSB HANDEL SP\\u00d3\\u0141KA AKCYJNA;We\\u0142ecz;PL;Gra\\u017cyna Basa;NIC: 35 ;;Udzielenie prawa;\\\\n386107;249290;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;BUDUJ\\u0104CE POMYS\\u0141Y NA BIZNES;S;GRUPA PSB HANDEL SP\\u00d3\\u0141KA AKCYJNA;We\\u0142ecz;PL;Gra\\u017cyna Basa;NIC: 35 ;;Udzielenie prawa;\\\\n386108;249767;2011-06-01;19/2011;2011-09-12;02/2013;2013-02-28;rDs 2009;SG;I\\u017bAKIEWICZ LUCJAN RDS;Gdynia;PL;Zofia Krystyna Radoman BIURO PATENTOWE I OCHRONY ZNAK\\u00d3W TOWAROWYCH BINEK, RADOMAN SP\\u00d3\\u0141KA PARTNERSKA;NIC: 35 39 ;VIE: 010101 010104 010110 260105 260124 270501 270701 290112 ;Udzielenie prawa;\\\\n386109;;2011-06-01;19/2011;2011-09-12;;;DeeZee WE SHOES;SG;\\u017bAK DOMINIKA DEE-ZEE;Krak\\u00f3w;PL;;NIC: 16 25 ;VIE: 020901 260402 270501 290113 ;Umorzenie post\\u0119powania;\\\\n386110;249291;2011-06-01;19/2011;2011-09-12;01/2013;2013-01-31;FUNDACJA nowoczesna Polska;SG;FUNDACJA NOWOCZESNA POLSKA;Warszawa;PL;;NIC: 36 41 45 ;VIE: 011711 261102 261112 270501 290113 ;Udzielenie prawa;\\\\n386111;;2011-06-01;19/2011;2011-09-12;;;ALPIN SPORT Outdoor Wear & Equipment Alpin sport Since 1989;SG;ALP SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Miko\\u0142\\u00f3w;PL;Grzegorz Bogacki KANCELARIA PATENTOWA PATENTINVENT S.C.;NIC: 06 09 18 20 22 24 25 28 ;VIE: 260410 270501 290113 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386112;;2011-06-01;19/2011;2011-09-12;;;KPRM ASPEKT GRUPA MOSTOWA;SG;ASPEKT SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Jaworzno;PL;Grzegorz Bogacki KANCELARIA PATENTOWA  PATENTINVENT  S. C.;NIC: 06 19 37 42 ;VIE: 071101 260112 270501 290113 ;Odmowa;\\\\n386113;249292;2011-06-01;19/2011;2011-09-12;01/2013;2013-01-31;SED-Ja;SG;SED-JA SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Mi\\u0119dzyrzecze G\\u00f3rne;PL;;NIC: 20 35 ;VIE: 120101 120109 260412 260424 270501 290113 ;Udzielenie prawa;\\\\n386114;249293;2011-06-01;19/2011;2011-09-12;01/2013;2013-01-31;Klinika Duszy i Cia\\u0142a;SG;WOLSKA EWA KLINIKA DUSZY I CIA\\u0141A;Sosnowiec;PL;Agnieszka \\u015anie\\u017cko WTS RZECZNICY PATENTOWI - WITEK, \\u015aNIE\\u017bKO I PARTNERZY;NIC: 44 ;VIE: 060301 270501 290115 ;Udzielenie prawa;\\\\n386115;255891;2011-06-02;19/2011;2011-09-12;09/2013;2013-09-30;open life LIFE & PENSION;SG;OPEN LIFE TOWARZYSTWO UBEZPIECZE\\u0143 \\u017bYCIE SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Agnieszka Woszczak-Kami\\u0144ska KAMI\\u0143SKI & PARTNERZY KANCELARIA PATENTOWA;NIC: 16 35 36 38 41 42 ;VIE: 020914 050519 050520 270501 290115 ;Udzielenie prawa;\\\\n386116;250893;2011-06-02;19/2011;2011-09-12;03/2013;2013-03-29;;G;OPEN LIFE TOWARZYSTWO UBEZPIECZE\\u0143 \\u017bYCIE SP\\u00d3\\u0141KA AKCYJNA;Warszawa;PL;Agnieszka Woszczak-Kami\\u0144ska KAMI\\u0143SKI SOBAJDA i PARTNERZY SP.P.;NIC: 16 35 36 38 41 42 ;VIE: 020914 050519 050520 290115 ;Udzielenie prawa;\\\\n386117;250167;2011-06-02;19/2011;2011-09-12;02/2013;2013-02-28;KOMODUS;S;\\u015aMIECH ANNA;\\u0141\\u0119czna;PL;;NIC: 37 40 42 ;;Udzielenie prawa;\\\\n386118;249294;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;KurJerzy.pl;S;ITBROSS RICHERT SP\\u00d3\\u0141KA JAWNA;Gda\\u0144sk;PL;;NIC: 35 39 ;;Udzielenie prawa;\\\\n386119;249295;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;PETRA;S;ELTECO POLAND SP\\u00d3\\u0141KA AKCYJNA;Krak\\u00f3w;PL;;NIC: 04 07 40 ;;Udzielenie prawa;\\\\n386120;249296;2011-06-02;19/2011;2011-09-12;01/2013;2013-01-31;KATJA;S;ELTECO POLAND SP\\u00d3\\u0141KA AKCYJNA;Krak\\u00f3w;PL;;NIC: 04 07 40 ;;Udzielenie prawa;\\\\n386121;;2011-06-02;19/2011;2011-09-12;;;spOko;SG;OFFICE LINE PETER BOUE SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;W\\u0142oc\\u0142awek;PL;Agnieszka Woszczak-Kami\\u0144ska KAMI\\u0143SKI I PARTNERZY KANCELARIA PATENTOWA;NIC: 35 ;VIE: 260401 260414 270501 290112 ;Wyga\\u015bni\\u0119cie decyzji warunkowej;\\\\n386122;;2011-06-02;19/2011;2011-09-12;;;king size outdoor;S;RBX SP\\u00d3\\u0141KA Z OGRANICZON\\u0104 ODPOWIEDZIALNO\\u015aCI\\u0104;Rybnik;PL;Jerzy Lampart KANCELARIA PATENTOWA DR IN\\u017b. JERZY LAMPART;NIC: 06 36 37 ;;Umorzenie post\\u0119powania;\\\\n386123;253061;2011-06-02;19/2011;2011-09-12;06/2013;2013-06-28;DOM zaczyna si\\u0119 od... dobrego projektu!;SG;MENDEL BARBARA MENDEL BARBARA ARCHON+ BIURO PROJEKT\\u00d3W;My\\u015blenice;PL;Izabela Sikora PATENTOWY.COM KANCELARIA PRAWA W\\u0141ASNO\\u015aCI PRZEMYS\\u0141OWEJ;NIC: 35 41 42 ;VIE: 270501 290112 ;Udzielenie prawa;\\\\n386124;259603;2011-06-02;19/2011;2011-09-12;02/2014;2014-02-28;DOM ZACZYNA SI\\u0118 OD DOBREGO PROJEKTU;S;MENDEL BARBARA ARCHON+ BIURO PROJEKT\\u00d3W;My\\u015blenice;PL;Izabela Sikora PATENTOWY.COM KANCELARIA PRAWA W\\u0141ASNO\\u015aCI PRZEMYS\\u0141OWEJ IZABELA SIKORA;NIC: 35 41 42 ;;Udzielenie prawa;\\\\n386125;;2011-06-02;19/2011;2011-09-12;;;PROJEKTY DOM\\u00d3W Nowoczesnych;SG;MENDEL BARBARA ARCHON+\\" BIURO PROJEKT\\u00d3W\', \'col11\': \'My\\u015blenice\', \'col12\': \'PL\', \'col13\': \'Izabela Sikora PATENTOWY.COM KANCELARIA PRAWA W\\u0141ASNO\\u015aCI PRZEMYS\\u0141OWEJ IZABELA SIKORA\', \'col14\': \'NIC: 09 16 41 42 \', \'col15\': \'VIE: 270501 \', \'col16\': \'Wyga\\u015bni\\u0119cie decyzji warunkowej\', \'updated_at\': datetime.datetime(2020, 2, 18, 11, 16, 42, 360181), \'row_no\': 320130, \'resource\': {\'id\': 16656, \'title\': \'123\'}}}}])", "uuid": "cbbc3f56-6b2c-42b0-9475-d72ff414e98e", "link": "http://api.mcod.local/media/resources/20200218/2020_02_18_listaZnakowTowarowych1_Dcila7E.zip", "format": "csv", "type": "file"}"""  # noqa
        assert tr.message == ["Nierozpoznany błąd walidacji"]
        assert tr.recommendation == ["Skontaktuj się z administratorem systemu."]
        tr = TaskResult()
        tr.result = """{"exc_type": "SomeUnknownError", "exc_message":""}"""
        assert tr.message == ["Nierozpoznany błąd walidacji"]
        assert tr.recommendation == ["Skontaktuj się z administratorem systemu."]

    def test_error_code_finding(self):
        result = {"exc_type": "TestError", "exc_message": ""}
        assert TaskResult._find_error_code(result) == "TestError"

        result["exc_type"] = "OperationalError"
        result["exc_message"] = "could not connect to server: Connection refused, cośtam cośtam"
        assert TaskResult._find_error_code(result) == "connection-error"
        result["exc_message"] = "Lorem ipsum remaining connection slots are reserved cośtam dalej"
        assert TaskResult._find_error_code(result) == "connection-error"

        result["exc_type"] = "Exception"
        result["exc_message"] = "unknown-file-format"

        assert TaskResult._find_error_code(result) == "unknown-file-format"

        result = {
            "exc_type": "InvalidResponseCode",
            "exc_message": "Invalid response code: 404",
        }
        assert TaskResult._find_error_code(result) == "404-not-found"

        result = {
            "exc_type": "ConnectionError",
            "exc_message": "HTTPSConnectionPool(host='knmiof.mac.gov.pl', port=443): Max retries exceeded with url: "
            "/kn/aktualnosci/6159,Nowy-wykaz-urzedowych-nazw-miejscowosci.html (Caused by "
            "NewConnectionError('<urllib3.connection.VerifiedHTTPSConnection object at 0x7f1418374dd8>: "
            "Failed to establish a new connection: [Errno -2] Name or service not known',))",
        }
        assert TaskResult._find_error_code(result) == "failed-new-connection"


class TestResourcesChart:
    def test_chart_create(self, buzzfeed_fakenews_resource, active_editor):
        chart = Chart()
        chart.chart = {"x": "col1", "y": "col2"}
        chart.resource = buzzfeed_fakenews_resource
        chart.created_by = active_editor
        chart.modified_by = active_editor
        chart.save()
        assert chart.id
        assert chart.is_default is False
        assert chart.chart == {"x": "col1", "y": "col2"}


class TestAggregatedDGAInfo:

    def test_create_aggregated_dga_info_with_statistic(self):
        dga_info = AggregatedDGAInfoFactory.create(views_count=100, downloads_count=50)
        assert dga_info.id

    def test_create_aggregated_dga_info_without_statistic(self):
        dga_info = AggregatedDGAInfoFactory.create()
        assert dga_info.id
        assert dga_info.views_count == 0
        assert dga_info.downloads_count == 0

    def test_create_second_instance_aggregated_dga(self):
        AggregatedDGAInfoFactory.create()

        with pytest.raises(ValidationError, match="'There can be only one AggregatedDGAInfo instance'"):
            AggregatedDGAInfoFactory.create()


class TestRemoveTabularDataIndex:
    def test_delete_resource_in_two_steps(self):
        """
        GIVEN a resource
        WHEN remove resource soft
        AND remove again remove resource - permanent remove
        THEN only during second remove call, task `delete_es_resource_tabular_data_index` will be called.
        """
        resource: Resource = ResourceFactory()
        resource_id = resource.id

        with patch("mcod.resources.models.delete_es_resource_tabular_data_index.s") as mocked_task_signature:

            # first delete (soft delete) - task deleting tabular data not called
            resource.delete()
            mocked_task_signature.assert_not_called()

            mock_task = mocked_task_signature.return_value
            with patch.object(mock_task, "apply_async_on_commit") as mock_apply_async:

                # second delete (permanent delete) - task deleting tabular data will be called
                resource.delete()
                mocked_task_signature.assert_called_once_with(resource_id)
                mock_apply_async.assert_called_once()

    def test_delete_resource_with_permanent_parameter(self):
        """
        GIVEN a resource
        WHEN remove resource with `permanent=True` parameter
        THEN task `delete_es_resource_tabular_data_index` for this resource will be called.
        """
        resource: Resource = ResourceFactory()
        resource_id = resource.id

        with patch("mcod.resources.models.delete_es_resource_tabular_data_index.s") as mocked_task_signature:
            mock_task = mocked_task_signature.return_value
            with patch.object(mock_task, "apply_async_on_commit") as mock_apply_async_on_commit:
                # permament delete - task deleting tabular data will be called
                resource.delete(permanent=True)
                mocked_task_signature.assert_called_once_with(resource_id)
                mock_apply_async_on_commit.assert_called_once()

    def test_delete_resources_by_trash(self):
        """
        GIVEN resources
        WHEN remove these resources from trash
        THEN task `delete_es_resource_tabular_data_index` for these resources.
        """
        resource_1: Resource = ResourceFactory()
        resource_2: Resource = ResourceFactory()
        resource_1_id = resource_1.id
        resource_2_id = resource_2.id

        # put resources into trash
        resource_1.delete()
        resource_2.delete()

        qs: QuerySet = Resource.trash.filter(id__in=[resource_1.id, resource_2.id])

        with patch("mcod.resources.managers.delete_es_resource_tabular_data_index.s") as mocked_task_signature:
            mock_task = mocked_task_signature.return_value
            with patch.object(mock_task, "apply_async_on_commit") as mock_apply_async_on_commit:
                # delete resources from trash
                qs.delete()
                called_arguments: List[int] = sorted(mocked_task_signature.call_args[0][0])
                expected_called_arguments: List[int] = sorted([resource_1_id, resource_2_id])

                assert called_arguments == expected_called_arguments
                mocked_task_signature.assert_called_once()
                mock_apply_async_on_commit.assert_called_once()
