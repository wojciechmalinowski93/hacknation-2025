# CHANGELOG

## Unreleased

______________________________________________________________________

### New

### Changes

### Fixes

### Breaks

## 2.52.2 - (2025-11-28)

______________________________________________________________________

### Changes

- Wykorzystanie biblioteki elasticsearch_dsl do komunikacji z ES podczas generacji raportu uszkodzonych linków - OTD-2171

## 2.52.1 - (2025-11-25)

______________________________________________________________________

### Fixes

- Poprawiono angielskie tłumaczenie pola nagłówka tabeli z uszkodzonymi linkami - zmiana w pliku /translations/system/en/LC_MESSAGES/django.po - OTD-2091

## 2.52.0 - (2025-11-20)

______________________________________________________________________

### New

- Dodano tworzenie indeksu Elasticsearch o nazwie broken-links, w który zawarte są dane z raportu publicznego uszkodzonych linków - OTD-1802
- Dodano testy funkcji pomocniczych i funkcji głównej tworzącej indeks broken-links - OTD-1802
- Dodano nowe typy stron do CMS-a: ReportRootPage,ReportAbstractSubpage, BrokenLinksInfo - OTD-1803
- Dodano endpointy API do pobierania ostatnich plików raportów broken links - OTD-1804
- Dodano testy automatyczne do widoku pobierania plików raportów - OTD-1804
- Dodanie do API endpointu reports/brokenlinks, odpowiedzialnego za zwracanie informacji o ostatnim utworzonym raporcie brokenlinks (wraz z testami endpointu) - OTD-1805
- Dodanie (wraz z testami) pomocniczych funkcji umożliwiających: pobieranie z Elasticsearch liczby wszystkich zaindeksowanych dokumentów oraz pobieranie podstawowych metadanych dla wskazanego pliku (funkcje pomocnicze w osbłudze endpointu reports/brokenlinks) - OTD-1805
- Dodanie do API endpointu reports/brokenlinks/data, odpowiedzialnego za zwracanie informacji o danych z raportu brokenlinks (z obsługą paginacji, sortowania i wyszukiwania), wraz z testami endpointu - OTD-1806, OTD-2067, OTD-2079
- Dodanie (wraz z testami) pomocniczych funkcji umożliwiających: pobieranie z Elasticsearch dokumentów dot. raportu brokenlinks, do wyświetlenia w GUI. - OTD-1806
- Dodano nowe kolumny do raportu broken links w Panelu Administracyjnym - OTD-1809
- Dodano generowanie raportów broken links na potrzeby frontendu - OTD-1810
- Dodano testy automatyczne do procesu generacji raportów o uszkodzonych linkach - OTD-1809, OTD-1810
- Dodano możliwość nieuwzględniania zasobów deweloperów budowlanych w sprawdzeniach uszkodzonych linków (zmienna środowiskowa BROKEN_LINKS_EXCLUDE_DEVELOPERS) - OTD-2055, OTD-2090

### Changes

- Uzupełniono test Check every CMS API's endpoint response for valid status_code o nowe typy stron związane z brokenlinks - OTD-1803
- Zmieniono task update_data_date() o aktualizację w polu dataset.verified (dodatkowo dla zasobu typu plik) - OTD-1831

### Fixes

- Poprawa ikony widgetu kalendarza w widokach Akademia i Laboratorium, Spotkania pełnomocników, Newsletter, Komunikaty - OTD-1550
- Naprawiono API lajkowania propozycji nowych danych (uniemożliwiono lajkowania propozycji nieaktywnych oraz naprawiono obsługę lajkowania propozycji w różnych stanach - kosz, draft itp.) - OTD-1734
- Zmieniono task validate_link, aby usunąć zjawisko wyścigu podczas generacji danych do raportu brokenlinks - OTD-1808

## 2.51.0 - (2025-10-29)

______________________________________________________________________

### New

- Dodana walidacja niezgodnych znaków dla pól title i description dla modeli Organisation i Dataset - OTD-1687
- Dodanie kolumny "utworzono" do widoku Kosza dla Zbiorów danych - OTD-1981
- Dodanie kolumny "utworzono" do widoku Kosza dla Źródeł danych - OTD-1981
- Dodano Dockerfile zbliżony do produkcyjnego, ale dedykowany do uruchamiania testów automatycznych - OTD-947
- Dodano plik docker-compose pozwalający na uruchomienie testów w sposób zbliżony do uruchomienia na CI/CID - OTD-947

### Changes

- Umożliwienie dodawania znaku specjalnego "&" dla pól title i description dla modeli Organisation, Dataset i Resource - OTD-1687
- Usunięto tox w ramach usprawnień lokalnego środowiska - OTD-1063
- Zmieniono konfigurację CI/CD tak, by re-używać customowy obraz przy testach - OTD-947
- Wprowadzenie wewnętrznego oznaczania zarchiwizowanych zasobów, aby uniezależnić się od nazw zasobów wystawianych w źródłach Dostawców - OTD-1853
- Aktualizacja i dodanie nowych testów, dotyczących powyższej zmiany - OTD-1853

### Fixes

- Usunięcie słów typu "amp;" dla widoku obiektu modeli: Resource, Dataset, Organisation, Alerts, Harvester, Newsletter oraz Showcases - OTD-1687
- Dodanie domyślnego sortowania po czasie dla Kosza dla Zbiorów Danych - OTD-1981

## 2.50.0 - (2025-10-10)

______________________________________________________________________

### New

- Dodano komendę django delete_indexes_for_developers do usuwania indeksów ES danych tabelarycznych zasobów dla instytucji o typie developer - OTD-1890
- Dodano testy wykonania komendy delete_indexes_for_developers z różną kombinacją parametrów - OTD-1890

### Fixes

- Naprawiono komunikat błędu przy próbie zapisu formularza zagnieżdżonego dla pola updateNotificationRecipientEmailInput - OTD-1910
- Naprawiono powielanie się komunikatów pomocniczych przy wyborze z listy Częstotliwość aktualizacji - OTD-1910

## 2.49.1 - (2025-09-29)

______________________________________________________________________

### Changes

- Przywrócenie ze względów bezpieczeństwa sposobu sanityzacji danych w backendzie – usunięto ponowne enkodowanie encji HTML - OTD-1861

______________________________________________________________________

## 2.49.0 - (2025-09-26)

______________________________________________________________________

### Fixes

- Zmiana zachowania dla Słów Kluczowych na stronie admina, dla użytkowników bez roli admin. Blokada wyświetlania historii i edycji samych tagów. Wyłączenie przycisku "zmiana" na stronie głównej. - OTD-1901
- Zmieniono sposób sanityzacji danych w backendzie – usunięto ponowne enkodowanie encji HTML - OTD-1861

### Changes

- Umożliwienie ustawienia przeszłej daty data_date (Dane na dzień) dla Zasobów importowanych - OTD-1845

## 2.48.0 - (2025-09-19)

______________________________________________________________________

### New

- Dodano brak walidacji danych, a tym samym tworzenia indeksu danych tabelarycznych, dla zasobów dodawanych przez instytucje typu deweloper - OTD-1888

### Changes

- Usunięto testy dot. walidacji plików kml - OTD-1888

## 2.47.0 - (2025-09-15)

______________________________________________________________________

### New

- Dodano w Panelu Administracyjnym obsługę nowego typu instytucji dedykowanego dla deweloperów budowlanych - OTD-1791
- Dodano w procesie harwestacji CKAN i XML obsługę nowego typu instytucji dedykowanego dla deweloperów budowlanych - OTD-1792
- Nowy typ instytucji (deweloper) w raportach w PA oraz generowanych z frontendu - OTD-1791 i OTD-1792

### Changes

- Zmieniono reguły walidacji Zawiera wykaz chronionych danych (zasoby) oraz Zawiera dane wysokiej wartości z wykazu KE (zasoby i zbiory) uwzględniające nowy typ instytucji - OTD-1792

## 2.46.0 - (2025-08-27)

______________________________________________________________________

### New

- Dodano flagę, kontrolującą uruchamianie generacji dziennego raportu w formacie XML - OTD-1769
- Dodano zmienną środowiskową, pozwalającą kontrolować czas startu tasków periodycznych - OTD-1769

### Changes

- Zmniejszono liczbę indeksacji zasobu w Elasticsearch - OTD-1727

### Fixes

- Naprawiono błąd przy kalkulacji openness score - OTD-1678
- Naprawiono błąd polegający na przypisaniu typu 'date' dla 'datetime' z godziną 00:00:00 - OTD-1715
- Naprawiono błąd 504 oraz długiego czasu renderowania się formularzy Użytkownika i Organizacji w Panelu Administracyjnym - OTD-1730
- Naprawiono błąd w pipeline `invalid value for parameter "log_timezone": "Poland"` - OTD-1773
- Naprawiono problem plików nietabelarycznych fałszywie pozytywnie przechodzących walidacje tabelaryczne - OTD-1722
- Zmieniono logikę wywoływania funkcji `user_sync_task`, wywołującej się w momencie dodawania, edycji i usuwania użytkownika w celu usunięcia błędów Discourse - OTD-1724

## 2.45.0 - (2025-08-08)

______________________________________________________________________

### New

- Dodano cache'owanie endpointa wyciągającego dane tabelaryczne dla Zasobu - OTD-1641
- Oflagowano mechanizm cache'owania - flaga `S66_falcon_caching_operate.be` - OTD-1641
- Dodano tagowanie eventów w Sentry emitowanych z tasków Celery - OTD-1671
- Dodano middleware dla FalconAPI `DjangoDBConnectionMiddleware` zamykający połączenia po zakończeniu odpytywania endpointa - OTD-1658
- Ustawiono zmienną dla ustawień bazy danych: `CONN_MAX_AGE` - OTD-1658

### Changes

- Uproszczono funkcję middleware cache - usunięto nadmiarową logikę - OTD-1641
- Zmieniono funkcję generacji klucza redis dla cache - teraz zawiera w sobie informacje o query params - OTD-1641
- Usunięto historyczne flagi - S61 i S63 - OTD-1641
- Przeniesiono ładowanie middleware'ów Falcona do osobnego modułu, `middleware_loader.py` - OTD-1658
- Health check systemów jest uruchamiany na podstawie zmiennej środowiskowej - OTD-1658
- Przeniesiono Falcon Limiter (api) do osobnego modułu - OTD-1658
- Uporządkowano przypisanie zadań do kolejek Celery oraz dodano nowe testy pilnujące routingu kolejek - OTD-1653

### Fixes

- Poprawiono walidację plików JSON, tak aby błędnie nie były rozpoznawane jako JSONLD - OTD-1699
- Naprawa niewydajnych formularzy Użytkownika i Instytucji w Panelu Administracyjnym - OTD-1581
- Uporządkowano kolejki Celery - OTD-1653

## 2.44.1 - (2025-07-30)

______________________________________________________________________

### Fixes

- Poprawiono błąd w CI przy instalacji zależności. Pakiety z repozytoriów Debian Buster nie istnieją w standardowej lokalizacji. - OTD-1651
- Zwiększono dopuszczalną długość z 5 do 13 znaków TLD dla adresu URL źródła XML po stronie frontendowej w PA. - OTD-1630
- Naprawiono błędy w odczycie wersji z API. - OTD-1351
- Poprawka obsługi z len(queryset) vs bool(queryset). - OTD-1570
- Naprawiono błąd formularza Instytucji w Panelu Administracyjnym dla Edytorów. - OTD-1580
- Zoptymalizowano zbyt długie czasy odpowiedzi dla żądań API. - OTD-1551

## 2.44.0 - (2025-07-03)

______________________________________________________________________

### New:

- Dodano bibliotekę do zbierania metryk: prometheus_client - OTD-1475
- Dodano metryki dla Prometheusa - OTD-1475
- Dodano middleware dla FalconAPI zbierający metryki dla Prometheusa - OTD-1475
- Dodano health check systemów CMS i admin - OTD-1475
- Dodano nowe endpointy dla CMS (/health), API (/metrics), admin (/health, /metrics) - OTD-1475

### Changes

- Zmieniono usuwanie w Panelu Administracyjnym harvestowanych zasobów oraz zbiorów danych na usuwanie trwałe - OTD-1427
- Dodano "Zawiera dane o wysokiej wartości z wykazu KE" do pól wypełnianych przy kopiowaniu Zasobu - OTD-1573
- Zmieniono CI/CD - na gałęziach release'owych uruchamia się tylko linter - OTD-1513
  - Umożliwiono deploy na `pre-devel` z MR manualnie
- Usztywnienie wersji biblioteki xmlsec z powodu błędu `xmlsec.Error: (100, 'lxml & xmlsec libxml2 library version mismatch')` - OTD-1475

### Fixes

- Poprawiono serializację błędów w API - OTD-1584
- Naprawiono błąd 500 występujący przy dodawaniu zbioru z zasobem bez wybranej instytucji - OTD-1548

## 2.43.0 - (2025-05-20)

______________________________________________________________________

### New

- Nowe wartości `irregular` i `notPlanned` częstotliwości aktualizacji w formularzu tworzenia i edycji Datasetu - OTD-1239, OTD-1240, OTD-1241
- Usunięto wartość `notApplicable` częstotliwości aktualizacji w formularzu twrozenia Datasetu - OTD-1240
- Wprowadzono inne zbiory wartości częstotliwości aktualizacji dla formularza tworzenia i edycji Datasetu - UPDATE_FREQUENCY_FOR_CREATE, UPDATE_FREQUENCY_FOR_UPDATE - OTD-1240, OTD-1241
- Dodano walidację uniemożliwiającą zapis Datasetu z update_fequency równym `notApplicable` - OTD-1241
- Nowa wersja (1.13) schematu XSD - `xml_import_otwarte_dane_1_13.xsd` oraz jego obsługa w procesie harwestacji XML - OTD-1242
- Nowe wartości `update_frequency` oraz wszystkie wartości z wielkich liter w raportach CSV generowanych z frontendu i PA - OTD-1244
- Obsługa nowych wartości `update_frequency` w raporcie RDF - OTD-1251
- Dodano testy konfiguracji celery, walidacji oraz STO dla plików RDF - OTD-1456
- Dodano formatter markdown do pre-commit dla plików `README.md` i `CHANGELOG.md` - OTD-1468
- Dodano ponowne podłączanie funkcji javascript powodujących dynamiczne dodawanie sekcji dot. powiadomień o koniecznej aktualizacji zbioru danych - OTD-1481
- Dodano testy na proces harwestowania z CKAN - OTD-1473

### Changes

- Zmieniono małe na wielkie pierwsze litery w wartościach `update_frequency` - OTD-1243
- Zmieniono sposób walidacji dla plików CSV wykorzystujących średnik jako znak separatora - OTD-1282
- Naprawa rozpoznawania plików nquads - OTD-1438
- Naprawa rozpoznawania plików RDF/XML - OTD-1465

## 2.42.2 - (2025-04-28)

______________________________________________________________________

### Fixes

- Naprawiono problem uruchamiania tasków periodycznych celery z modułu mcod/resources/tasks OTD-1446

## 2.42.1 - (2025-04-18)

______________________________________________________________________

### New

- Dodano blokowanie niechcianych plików podczas harvestowania zasobów CKAN i XML. OTD-1203 OTD-1204
  - zmiana kontrolowana feature flagą `harvester_file_validation.be`
- Dodano testy procesu harvestowania, moduł schema_utils.py, wyjątki ResourceFormatValidation, NoResponseException

### Changes

- Przeniesiono generowanie formatu plików harvestowanych do modułu `schema_utils.py`.
- Refaktoring i poprawa funkcji w module `file_format_from_response.py`.
- Przeniesiono zmienne związane z "supported_formats" do base.py.
- Aktualizacja testów w module `mcod/datasets/tests/test_dataset_verified_date.py`

### Fixes

- Poprawa wyliczania daty aktualizacji zbioru dla zasobów importowanych: usunięcie Zasobu nie zmienia daty aktualizacji. OTD-1352
  - poprawa funkcji `handle_resource_post_save`
- Obsługa błędnej wersji oraz braku wersji w kodzie error handlera API. OTD-1351

## 2.42.0 - (2025-04-15)

______________________________________________________________________

### New

- Dodano format `rdfa` do mapowania STO z domyślną wartością 4 oraz do kalkulatora dla rozszerzeń RDF OTD-1323
- Komenda uzupełniająca pole `format` dla zasobów importowanych z CKAN, które nie mają ustawionego formatu OTD-1341
  - `set_format_for_ckan_resources`
- Komenda przeliczająca ponownie stopnie otwartości wg zaktualizowanych reguł OTD-1166
  - `calculate_openness_score`

### Changes

- Zmieniono reguły przypisania stopni otwartości dla archiwów OTD-1152
- Zmieniono zachowanie importera CKAN, tak by uzupełniał pole `format` oraz nadawał stopien otwartości zaimportowanych danych OTD-1193
- Usunięto nadmiarowe informacje o pozostałych możliwych Stopniach Otwartości z mapowania `SUPPORTED_CONTENT_TYPES` (pozostawiono tylko domyślne) OTD-1323, OTD-1324
- Aktualizacja informacji kontaktowych na stronach portalu niedostępnych w CMS OTD-1279

### Fixes

- Refactor (decoupling) tasków `process_resource_from_url_task`, `process_resource_res_file_task`, `process_resource_file_data_task` OTD-1199. Kluczowe zmiany:
- utworzenie dwóch entrypointów będących procesami, które zarządzają przepływem i uruchamianiem w/w tasków (nie wywołują już siebie wzajemnie),
- pozbycie się niepotrzebnych handlerów dla w/w tasków
- ustawienie zmiennej `CELERY_TASK_STORE_EAGER_RESULT` w settings na `True`
- rozbicie na osobne moduły pliku mcod/resources/tasks.py
- Refactor pakietu liczącego Stopnie otwartości danych (STO) OTD-1162
- Oznaczenie pola "Poziom otwartości danych" jako nieklikalne w Panelu Administracyjnym OTD-1311

## 2.41.1 - (2025-03-26)

______________________________________________________________________

### New

- Dodano test sprawdzający, czy istnieje możliwość edycji danych tabelarycznych, w przypadku pól required dla formularza oraz pustych dla resource.
- Dodano nowe metody dla ChangeResourceForm: \_set_fields_required_attribute_to_false, \_modify_data_for_imported
- Dodano zmienna środowiskowa do lokalnego testowania: INTERNAL_IPS
- Dodano funkcję pomocnicza date_at_midnight() w mcod/lib/date_utils.py (z testem w mcod/lib/tests/test_date_utils.py)
- Dodano testy w mcod/datasets/tests/test_dataset_verified_date.py
- Dodano handler update_dataset_verified_after_restoring_from_trash() z aktualizacją dataset.verified zgodnie z OTD-1132
- Dodano metodę update_dataset_verified() do klasy Resource.

### Changes

- Zmieniono fixture testową (def dataset), w której zlikwidowano run_on_commit_events() dla dataset.
- Usunięto metodę modify_change_form_for_imported w ResourceAdmin.
- Naprawiono błąd w metodzie \_validate_related_resource (ResourceForm): AttributeError.
- Zmieniono sposób wyświetlania błędów w change_form.html.
- Zmieniono handler handle_resource_post_save() o aktualizację w polu dataset.verified zgodnie z OTD-1132
- Zmieniono task update_data_date() o aktualizację w polu dataset.verified zgodnie z OTD-1132 (dla zasobów api i website)

### Fixes

- Usunięto błąd 500 w przypadku zmiany typu danych tabelarycznych dla zasobów harvestowanych: OTD-805, OTD-1259
- Poprawa ustawiania daty aktualizacji zbioru: OTD-1132

## 2.41.0 - (2025-03-11)

______________________________________________________________________

### New

- Akcja w PA związana z źródłami danych - Eksportuj zaznaczone do CSV - OTD-1169, OTD-1171
- Akcja w PA związana z źródłami danych - Eksportuj ostatni import do CSV - OTD-1170
- Zakładka Źródła danych w sekcji Raporty w PA - OTD-1155, OTD-1156, OTD-1157
- Serializer DataSourceImportsCSVSchema - OTD-1168
- Serializer DataSourceLastImportDatasetCSVSchema - OTD-1167
- Task asynchroniczny - generate_harvesters_imports_report przygotowujący dane do raportu i generujący raport w importów - OTD-1167
- Task asynchroniczny - generate_harvesters_last_imports_report przygotowujący dane do raportu i generujący raport z ostatnich importów - OTD-1168
- Pole openness_score w widoku edycji Resource - OTD-1140
- Pole source_type w widoku edycji Resource - OTD-1141
- Pole source_type w widoku edycji Dataset - OTD-1142
- Kolumna openness_score w raporcie Zasobów - OTD-1143
- Kolumna source_type w raporcie Zasobów - OTD-1143
- Kolumna openness_score w raporcie Zbiory Danych - OTD-1144
- Kolumna source_type w raporcie Zbiory Danych - OTD-1144

### Changes

- Zmiana etykiety pola openness_score w raporcie - katalogu wszystkich Zbiorów - OTD-1249
- Zmiana etykiety pola openness_score w raporcie - katalogu dla pojedynczego Zbioru - OTD-1250

## 2.40.2 - (2025-02-20)

______________________________________________________________________

### Fixes

- Zmniejszono wersję biblioteki django-admin-rangefilter do stabilnej i działającej wersji 0.4.0 (OTD-1222)

## 2.40.1 - (2025-02-19)

______________________________________________________________________

### Fixes

- Przywrócono bibliotekę goodtables do stabilnej i działającej wersji 2.1.4 (OTD-1215)
- Naprawa błędu z nieprzechodzącym testem w związku z tłumaczeniami django (OTD-1111)

## 2.40.0 - (2025-02-14)

______________________________________________________________________

### New

- Podniesiono wersję Falcona do 4.0.2, co spowodowało aktualizację kodu: Należało dodać argumenty pozycyjne dla Exceptionów (api/handlers.py, watchers/views.py) oraz zmienić metodę get_http_status na code_to_http_status. Należało również zmienić error handlery: nazwa parametrów w funkcji zwracała warningi, Falcon prosił o ich zmianę (przestawienie parametrów w errors.py).
- Podniesiono wersję django-admin-rangefilter do 0.13.2. Zmiana spowodowała zmianę modułu w pliku reports/admin.py z rangefilter.filter na rangefilter.filters
- Usunięto bibliotekę django-vault-helpers (nie była używana) co spowodowało zmianę w ustawieniach projektu (settings/base.py).
- Usunięto bibliotekę wand, co spowodowało zmiany w Dockerfile i gitlab-ci.yml.
- Przeniesiono hypereditor z gitlaba do projektu (.whl).

## 2.39.0 - (2024-12-13)

______________________________________________________________________

### New

- Dodano nową wersję schematu XSD - xml_import_otwarte_dane_1_12.xsd (OTD-869)
- Harwestacja metadanej contains_protected_data przez harwester XML wraz z walidacjami (OTD-870, OTD-871, OTD-872, OTD-873, OTD-874)
- Harwestacja metadanej contains_protected_data przez harwester CKAN wraz z walidacjami (OTD-1026, OTD-1027, OTD-1028, OTD-1029, OTD-1030, OTD-1031)
- Uwzględnienie w wykazie głównym DGA zasobów harwestowanych przez CKAN (OTD-1032)
- Wartości domyślne równe None dla pól has_dynamic_data, has_high_value_data, has_research_data w serializerach zasobu i zbioru danych (OTD-870)
- Wartość domyślną równą False dla pola contains_protected_data serializerach zasobu (OTD-870, OTD-1026)
- Tłumaczenia komentarzy błędów walidacji
- Testy rozwiązania

## 2.38.1 - (2024-11-28)

______________________________________________________________________

### Fixes

- Poprawki w angielskich tłumaczeniach w pliku `translations/system/en/LC_MESSAGES/django.po` (OTD-1037)

## 2.38.0 - (2024-10-30)

______________________________________________________________________

### New

- Dodanie w metadanej `Zawiera dane o wysokiej wartości z wykazu KE` dla zasobu oraz zbioru danych (OTD-496)
- Dodanie reguł sanityzacji do formularzy - BEZP Cross-Site Scripting (OTD-397)
- Dodanie cyklicznego tasku generującego raport spójności stanu BD oraz indeksów ES (OTD-824)
- Dodanie usuwania indeksów ES danych tabelarycznych zasobów, przy usuwaniu zasobu z kosza (OTD-881)

### Changes

- Zmiana w skrypcie start-api.sh umożliwiająca parametryzację czasu timeoutu gunicorna, w celu umożliwienia downloadu plików powyżej 1 GB (OTD-820)
- Wyłączenie w CI testów na środowisku DEV (gałąź pre-devel) (OTD-846)
- Zmiana typów pól w ES fields.StringField() na fields.TextField(), w celu wyeliminowania DeprecationWarning dot. typów danych (OTD-891)

### Fixes

- Poprawa obsługi zmiennej środowiskowej DEBUG (OTD-391)

## 2.37.1 - (2024-10-22)

______________________________________________________________________

### Fixes:

- Naprawa niedeterministycznych testów związanych ze współdzieleniem cache dla sesji przez workery testowe (OTD-899)
- Naprawa niepodejmowania cyklicznych tasków - celery beat (OTD-930)

## 2.37.0 - (2024-10-04)

______________________________________________________________________

### New:

- Dodano możliwość logowania do Panelu Administracyjnego z wykorzystaniem węzła krajowego
- Nowy blok w base.html generujacy dropdown userów powiązanych z WK.
- Nowy blok w login.html do logowania przez WK.
- Nowe pole w bazie dla modelu User: last_logged_method
- Nowe pola w formularzu użytkowników w panelu admina: is_gov_linked
- Nowa stałą typu Enum: PORTAL_TYPE definiujący z jakiego portalu został wykonany request związany z Węzłem Krajowym.
- Nowa metoda dla modelu User update_last_logging_method(), aktualizująca pole w bazie last_logged_method definujące jak użytkownik się zalogował do serwisu (WK, Formularz).
- Nowa metoda w modelu User definiująca, czy użytkownik ma dostęp do panelu admina has_access_to_admin_panel().
- Nowe property dla modelu User connected_gov_users_for_admin_page zwracajace konta użytkowników powiązanych z WK.
- Nowe pola dla raportu użytkowników: wk_linked, last_logged_method

### Changes

- Zwiekszenie liczby obrazkow w stopce dla wersji angielskiej (OTD-829)
- Usunieto biblioteke corsheaders
- Sposób generowania linków do przekierowań dla frontendu (get_redirect_url())
- Zmiany css dla login.html, base.html.
- Podniesienie wersji Celery z 5.0.2 na 5.3.0
- Dostosowanie testu sprawdzającego sortowanie zasobów DGA po tytule organizacji (OTD-819)

## 2.36.0 - (2024-08-14)

______________________________________________________________________

### New

- Pola pesel, \_pesel, is_gov_auth dla modelu User
- Bibliotekę django-logingovpl (plik .whl) oraz django-encrypted-model-fields.
- Zmienne środowiskowe niezbędne do działania funkcjonalności: USERS_TEST_LOGINGOVPL, LOGINGOVPL_ISSUER, LOGINGOVPL_SSO_URL,LOGINGOVPL_ASSERTION_CONSUMER_URL, LOGINGOVPL_ENC_KEY,
  LOGINGOVPL_ENC_CERT, LOGINGOVPL_ARTIFACT_RESOLVE_URL, LOGINGOVPL_SL_URL, FIELD_ENCRYPTION_KEYS, FRONTEND_BASE_URL
- Interfejs (budowanie adresów URL dla przekierowań - klasa LOGINGOVPL_ACTION) związany z komunikacją backend - frontend.
- Endpointy: /logingovpl, /logingovpl/idp, /logingovpl/switch, /logingovpl/unlink.
- Uniwersalną klasę (MethodsNotAllowedTestMixin) do testowania metod zezwolonych dla testowanego API.
- Serwisy odpowiedzialne za wykonywanie różnych zadań dla funkcjonalności Węzła Krajowego (LoginGovPlService) jak i związanych z użytkownikiem (UserService).
- Testowy formularz do logowania przez Węzeł Krajowy - Django Template.
- Dodanie dodatkowego atrybutu (connected_gov_users) do zwrotnego wyniku w formacie JSON w endpoincie /auth/user
- Nowe właściwości dla modelu User: is_gov_linked, connected_gov_users.
- Moduł contants oraz exceptions dla aplikacji users.

## 2.35.2 - (2024-07-19)

______________________________________________________________________

### New

- Komenda do masowej re-walidacji Zasobów (Resource) tabelarycznych (OTD-592)

### Changes

- Sposób organizacji danych Wykazu Głównego - od teraz zasoby będą posortowane po kolumnie "Nazwa dysponenta zasobu" (OTD-688)
- Stylowanie w pliku xlsx Wykazu Głównego (OTD-689)
- Zawartość pliku Wykazu Głównego - usunięto wiersze, które nie zawierają informacji w kolumnie "Zasób chronionych danych" (OTD-690)
- Rozluźnienie polityki sprawdzania certyfikatów "self signed certificate" przy imporcie pliku XML za pomocą Harvestera (OTD-691)

### Fixes

- Naprawa błędów spowodowanych umieszczeniem znaków '{', '}' w opisie komunikatów (Alert) oraz opisie instytucji (Organization) (OTD-601)

## 2.35.1 - (2024-07-01)

______________________________________________________________________

### New

- Dostosowanie kodu do stylu: plik `.git-blame-ignore-revs` dokumentujący zmiany masowe (OTD-672)

### Changes

- Harvester: walidacja URL wysyła żądanie pobrania pliku z nagłówkiem `User-Agent` popularnych przeglądarek zamiast `python-requests` (OTD-560)
- Dostosowanie kodu do stylu: formatowanie we wszystkich plikach na zgodne z ustawieniami `pre-commit` (black, end-of-lines) (OTD-672)
- Dostosowanie kodu do stylu: testy formatowania muszą przejść w CI (`allow_failure: false`) (OTD-672)

## 2.35.0 - (2024-06-18)

______________________________________________________________________

### New

- Dodano model `AggregatedDGAInfo` przechowujący informacje o zasobie zbiorczym DGA (OTD-438)
- Dodano endpoint `/dga-aggregated` zwracający informacje o zasobie zbiorczym DGA (OTD-439)
- Dodano task celery `create_main_dga_resource_task` tworzący zasób zbiorczy DGA (OTD-441) i (OTD-587)

### Changes

- zmieniono komunikaty walidacji pola `electronic_delivery_address` dla przypadku błędnej sumy kontrolnej (OTD-555)

### Removed

- Usunięto unique z walidacji pola `electronic_delivery_address` (OTD-554)

## 2.34.2 - (2024-05-22)

______________________________________________________________________

### New

- Dodano nowy job w CI w celu wydzielenia środowiska DEV do wdrażania dowolnych nieautoryzowanych przez biznes zmian na potrzeby testów (OTD-415-444)
- Dodano wywołanie black w `pre-commit` (OTD-344)
- Dodano job w CI, lint, który wywołuje `pre-commit` na wszystkich plikach (OTD-344)
- Dodano plik `.git-blame-ignore-revs` dokumentujący zmiany masowe (OTD-344)

### Fixes

- Aktualizacja Pipfile.lock (OTD-408)
- Podbicie Python w `docker/app/Dockerfile` do wersji obrazu `python:3.8.16` (OTD-408)
- Podbicie Node.js w `docker/app/Dockerfile` do wersji 16.x (OTD-408)

### Removed

- Usunięcie starych plików budowania zależności `requirements-common.txt` na rzecz `Pipfile.lock` (OTD-408)
- Usunięcie zakomentowanych linii z `.gitlab-ci.yml` (OTD-408)
- Usunięcie z `docker/app/Dockerfile` środowiska wirtualnego (OTD-408)

## 2.34.1 - (2024-05-13)

______________________________________________________________________

### Fixes

- Poprawiono komunikaty błędów - dodano kropki (OTD-492, OTD-493)

## 2.34.0 - (2024-05-08)

______________________________________________________________________

### New

- Dodanie pola `electronic_delivery_address` do modelu `Organization` oraz pliku migracji bazodanowej - US.01 (OTD-315)
- Dodanie pola `electronic_delivery_address` do dokumentu ES `InstitutionDocument` - US.01 (OTD-315)
- Funkja walidująca ADE pod kątem schematu oraz zgodności z sumą kontrolną - US.01 (OTD-315)
- Dodanie pola `electronic_delivery_address` do serializera instytucji - US.02 (OTD-316)
- Dodanie pola `adres do doręczeń elektronicznych` do formularza tworzenia/edycji Instytucji - US.01 (OTD-315)
- Pole `adres do doręczeń elektronicznych` w zakładce do przeglądania usuniętych Instytucji (OrganizationTrashAdmin) - US.01 (OTD-315)
- Dodanie pola `Address for electronic delivery` do raportu CSV metadata - US.03 (OTD-317)
- Dodanie pola `Id Institution` do raportu CSV metadata - US.03 (OTD-317)
- Dodanie pola `Id Institution` do raportu wywoływanego z PA (raport "Zasoby" sekcji "Raporty") - US.04 (OTD-318)
- Dodanie pola `Id dataset` do raportu wywoływanego z PA (raport "Zasoby" sekcji "Raporty") - US.04 (OTD-318)

### Changes

- Zwiększono szerokość pól epuap, electronic_delivery_address, regon i website do 245 px - US.01 (OTD-315)

### Fixes

- Poprawiono komunikaty błędów oraz obsługę przypadku zwrócenia None przez funkcję zwracającą rozszerzenie pliku (OTD-404, OTD-419)
- Poprawiono help_text dla pola `contains_protected_data` w formie (OTD-471)

## 2.33.1 - (2024-03-27)

______________________________________________________________________

### Fixes

- Naprawa błędu związanego z aktualizacją zasobu utworzonego jako szkic z flagą `Zawiera chronione dane` na zasób opublikowany
- Poprawa tłumaczenia komunikatu o błędnym formacie pliku

## 2.33.0 - (2024-03-21)

______________________________________________________________________

### New

- Dodanie w Panelu Administracyjnym pola `Zawiera chronione dane` - US.01 (OTD-159)
- Dodanie możliwości filtracji zasobów po polu `Zawiera chronione dane` - US.02 (OTD-167)
- Dodanie migracji DGA - US.03 (OTD-168)
- Dodanie w CMS podstrony `Informacje` dotyczącej DGA - US.05 (OTD-170)
- Dodanie w CMS podstrony `Wykaz danych chronionych` dotyczącej DGA - US.06 (OTD-171)
- Dodanie w CMS podstrony `Wniosek o dostęp do chronionych danych` dotyczącej DGA - US.07 (OTD-172)
- Dodanie metadanej dotyczącej DGA w raportach - US.08 (OTD-227)
- Dodanie możliwości tworzenia podstron DGA oraz dostosowanie narzędzi CMS do podstron dot. DGA - US.11 (OTD-314)

### Changes

- Aktualizacja `README.md` w zakresie dodania informacji o kompilacji tłumaczeń

## 2.32.0 - (2024-03-12)

______________________________________________________________________

### New

- Instalacja pakietów za pomocą pipenv lokalnie oraz w dokerze. (OTD-27)
- Testy uruchamiane przez pipenv. (OTD-27)
- Dokładne odwzorowanie środowiska w Pipfile.lock. (OTD-27)
- Skrypt `redefine_datasets_symlink` do aktualizacji symlink'ów w folderze datasets archive. (OTD-303)
- Fixture dla dataset. (OTD-303)
- Logger'y dla cyklicznych zadań. (OTD-303)
- Testy dla komendy `redefine_datasets_symlink`. (OTD-303)
- Dodanie metody dla modelu datasets generującej nazwę folderu dla archiwum zbiorów. (OTD-303)

### Changes

- Aktualizacja `README.md`. (OTD-27, OTD-140)
- Konfiguracje aplikacji dla Nginx'a. (OTD-140)
- Nowy certyfikat (data ważności: 10 lat) dla Nginx\`a. (OTD-140)
- Dodanie pliku konfiguracyjnego dla Postgres'a `configs/postgresql`. (OTD-140)
- Zmiany w `docker compose`. (OTD-140)
- Aktualizacja `.gitlab-ci.yml` związana z bezpieczeństwem. (OTD-140)

### Fixes

- Przeniesiono fixture dataset'ów z modułu BBD do nowego `datasets_fixtures`. (OTD-140)
- Zmiana funkcji `archives_upload_to`. (OTD-140)
- Poprawka umożliwiająca zmiany typów danych w Panelu Admina, dla zasobów importowanych Harvesterem ze źródła typu XML. (OTD-270)

### Removed

- Nie wymagane `requirements-devel.txt` oraz `requirements-test.txt` na rzecz Pipenv. (OTD-27)

## 2.31.10 - (2024-01-08)

______________________________________________________________________

### Fixes

- Naprawienie problemu z błędnym generowaniem pliku symlink do archiwum plików zbiorów danych podczas zmiany nazwy zbioru. (OTD-155)
- Poprawiono aktualizowanie archiwum zbioru danych o wszystkie zasoby. (OTD-155, OTD-196)
- Wprowadzenie walidacji zasobów (tytułu i opisu) pod względem niedozwolonych znaków. (OTD-131)
- Rozbicie taska odpowiedzialnego za tworzenie raportów CSV oraz XML na dwa osobne taski. (OTD-131)

## 2.31.9 - (2023-10-26)

______________________________________________________________________

### Fixes

- Uodpornienie asynchronicznych zadań na chwilową niedostępność infrastruktury (OTD-95)
- Rozbudowa procedury walidacji linku zasobu (OTD-127)

## 2.31.8 - (2023-08-03)

______________________________________________________________________

### Fixes

- Poprawka budowania pipeline - freeze wersji zależności jupyter (OTD-99)

## 2.31.7 - (2023-07-12)

______________________________________________________________________

### Fixes

- Zmiana strefy czasowej na lokalną w raportach csv użytkowników (OTD-55)
- Aktualizacja pakietów oraz repozytorium dla narzędzia pre-commit (OTD-59)

## 2.31.6 - (2023-05-09)

______________________________________________________________________

### Fixes

- Modyfikacja formularza profilu instytucji - pole website niewymagane (OTD-37)

## 2.31.5 - (2023-03-30)

______________________________________________________________________

### Fixes

- Poprawa walidacji serializera w zakresie warunków ponownego wykorzystania informacji (OTD-39)

## 2.31.4 - (2023-03-21)

______________________________________________________________________

### Fixes

- Blokada dodawania warunków - incydent krytyczny (OTD-28)
- Poprawa walidacji formularza oraz serializera w zakresie warunków ponownego wykorzystania informacji (OTD-30)
- Poprawki zgłoszone przez administratorów po wydaniu na produkcję (OTD-34)

## 2.31.3 - (2023-02-27)

______________________________________________________________________

### Fixes

- Naprawa createsuperuser (OTD-11)
- Naprawa błędów testów uruchamianych lokalnie (PBR-106)
- Naprawa błędów budowania CI (PBR-123)
- Podniesienie wersji paczek Pythonowych (PBR-123)

## 2.31.2 - (2022-08-30)

______________________________________________________________________

## 2.31.1 - (2022-08-30)

______________________________________________________________________

## 2.31.0 - (2022-08-25)

______________________________________________________________________

## 2.30.0 - (2022-08-17)

______________________________________________________________________

## 2.29.0 - (2022-08-02)

______________________________________________________________________

## 2.28.0 - (2022-07-21)

______________________________________________________________________

## 2.27.0 - (2022-06-29)

______________________________________________________________________

## 2.26.0 - (2022-06-01)

______________________________________________________________________

## 2.25.0 - (2022-05-12)

______________________________________________________________________

## 2.24.0 - (2022-04-21)

______________________________________________________________________

## 2.23.0 - (2022-03-28)

______________________________________________________________________

## 2.22.0 - (2022-03-10)

______________________________________________________________________

## 2.21.0 - (2022-02-15)

______________________________________________________________________

## 2.20.0 - (2022-01-17)

______________________________________________________________________

## 2.19.0 - (2021-12-08)

______________________________________________________________________

## 2.18.0 - (2021-11-16)

______________________________________________________________________

## 2.17.0 - (2021-10-26)

______________________________________________________________________

## 2.16.0 - (2021-09-07)

______________________________________________________________________

## 2.15.0 - (2021-06-14)

______________________________________________________________________

## 2.14.0 - (2021-05-24)

______________________________________________________________________

## 2.13.0 - (2021-05-05)

______________________________________________________________________

## 2.12.0 - (2021-04-13)

______________________________________________________________________

## 2.11.1 - (2021-03-17)

______________________________________________________________________

## 2.11.0 - (2021-03-15)

______________________________________________________________________

## 2.10.0 - (2021-02-24)

______________________________________________________________________

## 2.9.0 - (2021-02-01)

______________________________________________________________________

## 2.8.1 - (2020-12-29)

______________________________________________________________________

## 2.8.0 - (2020-12-15)

______________________________________________________________________

## 2.7.0 - (2020-12-01)

______________________________________________________________________

## 2.6.0 - (2020-10-18)

______________________________________________________________________

## 2.5.0 - (2020-09-30)

______________________________________________________________________

## 2.4.0 - (2020-09-07)

______________________________________________________________________

## 2.3.1 - (2020-08-11)

______________________________________________________________________

## 2.3.0 - (2020-07-29)

______________________________________________________________________

## 2.2.1 - (2020-07-03)

______________________________________________________________________

## 2.2.0 - (2020-06-29)

______________________________________________________________________

## 2.1.1 - (2020-06-17)

______________________________________________________________________

## 2.1.0 - (2020-05-28)

______________________________________________________________________

## 2.0.0 - (2020-05-11)

______________________________________________________________________

## 1.18.0 - (2020-05-04)

______________________________________________________________________

## 1.17.0 - (2020-03-16)

______________________________________________________________________

## 1.16.0 - (2020-03-09)

______________________________________________________________________

## 1.15.1 - (2020-02-18)

______________________________________________________________________

## 1.15.0 - (2020-02-18)

______________________________________________________________________

## 1.14.0 - (2020-01-22)

______________________________________________________________________

## 1.13.0 - (2019-12-18)

______________________________________________________________________

## 1.12.1 - (2019-11-28)

______________________________________________________________________

## 1.12.0 - (2019-11-25)

______________________________________________________________________

## 1.11.0 - (2019-09-25)

______________________________________________________________________

### New

- Możliwość zmiany statusu wszystkim notyfikacjom (MCOD-1605, MCOD-1632)
- Migracja końcówek artykułów na API 1.4 (MCOD-1641)
- Migracja strony gównej do API 1.4 (MCOD-1630)
- Narzędzie do modyfikacji schematu zasobu (MCOD-1591, MCOD-1617)
- Raporty mailowe z aktywności w obserwowanych obiektach (MCOD-824, MCOD-1631)
- Newsletter (MCOD-1280, MCOD-1645, MCOD-1673, MCOD-1629, MCOD-1670, MCOD-1671)

### Changes

- Zmiana koloru przycisku "Zgłoś uwagi" (MCOD-1573)
- Zmiany tekstów związanych z rejestracją użytkownika (MCOD-1654)

### Fixes

- Poprawki w dokumentacji API (MCOD-1323)
- Usunięcie nieużywanych końcówek typu autocomplete (MCOD-1675)
- Poprawki związane z przyszłym wdrożeniem modułu CMS
- Inne drobne poprawki w PA

## 1.10.1 - (2019-09-05)

______________________________________________________________________

## 1.10.0 - (2019-09-04)

______________________________________________________________________

## 1.9.0 - (2019-06-14)

______________________________________________________________________

### New

- Implementacja w API 1.4 obsługi użytkownika (konto, zmiana hasła, logowanie i tp) (MCOD-1481)
- Konwersja plików  SHP do GeoJSON (MCOD-1469)
- Indeksowanie danych geograficznych w Elasticsearchu (MCOD-1470)

### Changes

- Weryfikacja pierwszej kolumny zasobu na zgodność z formatem numerycznym (MCOD-1489)
- Rozszerzenie historii wyszukiwania użytkownika o instytucje, materiały edukacyjne, pomoc. (MCOD-1505)

### Fixes

- Poprawka do zasobów spakowanych zawierajacych więcej niż jeden plik (MCOD-1507)
- Poprawka do wyświetlania formatu .ods jako True (MCOD-1406)
- Poprawka tekstu w treści maila (MCOD-1494)
- Poprawka wyników wyszukiwania w API 1.4 (MCOD-1530)

## 1.8.0 - (2019-06-14)

______________________________________________________________________

### New

- Obsługa slug'ów we wszystkich obiektach API (MCOD-1325)
- Nowa końcówka API do pobierania zasobu (MCOD-1428)
- (WIP) Narzędzie dla dostawców do walidacji zasobów (MCOD-1455)
- Rozszerzenie mechanizmu walidacji zasobów o nowe komunikaty o błędach (MCOD-1501)
-

### Changes

- migracja kolejnych końcówek API do wersji 1.4
- dostosowanie formatu odpowiedzi w przypadku błędów do Json:API

### Fixes

- Poprawki związane z błędnym działanie liczników wyświetleń oraz pobrań (MCOD-1510, MCOD-1518)
- Poprawki związane z błędnym generowaniem slug'ów dla zbiorów danych

## 1.7.0 - (2019-05-30)

______________________________________________________________________

### New

- Nowy mechanizm synchronizacji danych po walidacji zasobów (MCOD-1042)
- Podstawowa obsługa plików SHP (MCOD-1276)
- Prezentacja wyników walidacji zasobów ze szczegółową informacją o błędach (MCOD-1281)
- Prezentacja wyników walidacji danych tabelarycznych (MCOD-1344)
- Możliwość zgłaszania uwag do zasobu (MCOD-1359)
- Możliwość zgłaszania zapotrzebowania na nowe zasoby (MCOD-1360)
- Obsługa slug'ów objektu po stronie API (MCOD-1364)

### Changes

- Zmiany w prezentacji wyników walidacji linku do zasobu (MCOD-1414)
- Zmiany w prezentacji wyników walidacji pliku zasobu (MCOD-1413)
- Aktualizacja modułów i komponentów backendu do nowszych wersji (m. innymi Falcon 2.0)
- Aktualizacje końcówek API do wersji 1.4

### Fixes

- Poprawki do wyświetlania zbiorów bez przydzielonej kategorii (MCOD-1368)
- Optymalizacja zapytań do bazy (MCOD-1422)
- Inne drobne poprawki

## 1.6.0 - (2019-04-24)

______________________________________________________________________

### New

- Nowy zestaw pól z datami w zasobie oraz zbiorze (MCOD-1192)
- Integracja z Hashocorp Vault (MCOD-1207)
- Obsługa skompresowanych archiwów (MCOD-1072)
- Obsługa plików DBF (MCOD-1343)
- Obsługa wielojęzyczności w zasobach, zbiorach i innych (MCOD-1303)
- Obsługa wersjonowania API za pomocą ścieżki (MCOD-1324)
- Integracja z ElasticAPM (MCOD-1210)

### Changes

- Zmiany wyświetlania numerów telefonów poprzez końcówkę API (MCOD-1320)
- Migracja na Django 2.2 (MCOD-1210)

### Fixes

- Poprawki do nawigacji w PA (MCOD-855)
- Zbyt restrykcyjna walidacja na nr telefonu organizacji (MCOD-1337)
- Poprawki w wyświetlaniu wyników walidacji zasobów (MCOD-1335)
- Różne drobne poprawki końcówek API (MCOD-1323)
- Poprawki w szablonach wyświetlających listę zasobów (MCOD-1324, MCOD-1356)
- Poprawki błędów 500 w sortowaniu wyników na końcówkach API (MCOD-1348)
- Poprawki błędów 500 podczas zgłaszania uwag do zbioru (MCOD-1397)

## 1.5.0 - (2019-03-12)

______________________________________________________________________

### New

- Narzędzia do obsługi dziennika wersji
- Dodatkowe filtry wyszukiwania w panelu administratora (MCOD-993)
- Eksport zasobów wraz z powiazanymi danymi do pliku CSV (MCOD-1261)
- Rozdzielenie bazy wiedzy oraz aktualności (MCOD-1200)

### Changes

- Usunięcie możliwości edycji dla pola licencji (MCOD-1012)
- Brakujące tłumaczenia w formularzu do dodawania użytkownika (MCOD-1016)
- Usunięcie kolumny name na liście instytucji (MCOD-1221)

### Fixes

- Poprawki literówek w panelu administracyjnym (MCOD-1334)
- Poprawki w historii wyszukiwania (MCOD-933)
- Poprawki do wyświetlania liczby aktualnych zasobów na końcówce /stats (MCOD-1208)

## 1.4.1 - (2019-02-20)

______________________________________________________________________

### New

- Wersjonowanie API
- Wprowadzenie wersji 1.4 API (niektóre widoki)
- Wyszukiwarka dla danych tabelarycznych
- Indywidualne API dla każadego zasobu tabelarycznego
- Mechanizm tłumaczeń na bazie danych
- Obsługa wyszukiwania przybliżonego (tzw. literówki)
- Obsługa wyszukiwania po fragmencie fraz
- Obsługa wyszukiwania wyrazów bez polskich znaków
- Tłumaczenie kategorii
- Walidacja numerów telefonu i faxu w formularzach
- Komunikaty techniczne
- Obsługa sortowania zbiorów po popularności
- Możliwość pobrania danych tabelarycznych w formacie JSON

### Changes

- Udoskonalony mechanizm indeksowania danych tabelarycznych
- Poprawki wydajnościowe w mechanizmie indeksowania danych tabelarycznych

### Fixes

- Błędne działanie filtrów wyszukiwarki :
  - IDS
  - CONTAINS
  - STARTSWITH
  - ENDSWITH
  - EXCLUDE
- Poprawka do sortowania alfaberycznego wyników wyszukiwania dla języka polskiego
- Bład typu 500 podczas wyświetlania dokumentacji
- Poprawka dotycząca właściwego rozpoznawania typu skompresowanego XLSX
- Poprawka do zunifikowanego mechanizmu logowania
- Poprawka komunikatu o błedzie wyświetlanego podczas logowania
- Różne poprawki związane z generowaniem raportów CSV
- Dodanie wymagalności na polu "słowa kluczowe"
- Dodanie ID użytkownika w raportach CSV
- Dodawanie zasobu z linki
- Obsługa nierozpoznanego kodowania znaków w pliku zasobu
