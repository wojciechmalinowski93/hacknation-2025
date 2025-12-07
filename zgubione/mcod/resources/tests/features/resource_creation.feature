@elasticsearch
Feature: Resource from link creation

# Testy wywalają się losowo za każdym razem inny mimo że mają tą samą strukturę. Czasem nie tworzy się zasób.
#  Scenario: Creation of resource with link to html content
#    Given resource is created for link http://example.com/index.html with html content
#    Then admin's response status code is 200
#    And resource field link is http://example.com/index.html
#    And resource field type is website
#
#  Scenario: Creation of resource with link to file content
#    Given resource is created for link http://example.com/index.php with zip content
#    Then admin's response status code is 200
#    And resource field link is http://example.com/index.php
#    And resource field type is file
#
#  Scenario: Creation of resource with link to xml content
#    Given resource is created for link http://example.com/index.xml with xml content
#    Then admin's response status code is 200
#    And resource field link is http://example.com/index.xml
#    And resource field type is file
#
#  Scenario: Creation of resource with link to json content
#    Given resource is created for link http://example.com/index.json with json content
#    Then admin's response status code is 200
#    And resource field link is http://example.com/index.json
#    And resource field type is file
#
#  Scenario: Creation of resource with link to xls content
#    Given resource is created for link http://example.com/index.xls with xls content
#    Then admin's response status code is 200
#    And resource field link is http://example.com/index.xls
#    And resource field type is file

  Scenario: Resource creation is ok
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test</a>" został pomyślnie dodany.

  Scenario: Resource creation with docx supplement file is ok
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test supplements", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published", "supplements-TOTAL_FORMS": "1", "supplements-0-id": "", "supplements-0-name": "test", "supplements-0-name_en": "", "supplements-0-language": "pl", "supplements-0-resource": "", "supplements-0-order": "0"}
    And admin's request posted files {"supplements-0-file": "doc_img.docx"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test supplements</a>" został pomyślnie dodany.
    And latest supplement attribute name is test

  Scenario: Resource creation with odt supplement file is ok
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test supplements", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published", "supplements-TOTAL_FORMS": "1", "supplements-0-id": "", "supplements-0-name": "test", "supplements-0-name_en": "", "supplements-0-language": "pl", "supplements-0-resource": "", "supplements-0-order": "0"}
    And admin's request posted files {"supplements-0-file": "example_odt_file.odt"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test supplements</a>" został pomyślnie dodany.
    And latest supplement attribute name is test

  Scenario: Resource creation with pdf supplement file is ok
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test supplements", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published", "supplements-TOTAL_FORMS": "1", "supplements-0-id": "", "supplements-0-name": "test", "supplements-0-name_en": "", "supplements-0-language": "pl", "supplements-0-resource": "", "supplements-0-order": "0"}
    And admin's request posted files {"supplements-0-file": "example.pdf"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test supplements</a>" został pomyślnie dodany.
    And latest supplement attribute name is test

  Scenario: Resource creation with txt supplement file is ok
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test supplements", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published", "supplements-TOTAL_FORMS": "1", "supplements-0-id": "", "supplements-0-name": "test", "supplements-0-name_en": "", "supplements-0-language": "pl", "supplements-0-resource": "", "supplements-0-order": "0"}
    And admin's request posted files {"supplements-0-file": "example.txt"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test supplements</a>" został pomyślnie dodany.
    And latest supplement attribute name is test

  Scenario: Adding of supplement to resource is visible in history
    Given resource with id 999
    And supplement created with params {"id": 999, "resource_id": 999, "file": "example.txt", "name": "supplement 999 added to resource 999", "language": "pl"}
    When admin's page /resources/resource/999/history is requested
    Then admin's response page contains supplement 999 added to resource 999
    And admin's response page contains example.txt

  Scenario: Resource creation with invalid supplement file
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test supplements", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published", "supplements-TOTAL_FORMS": "1", "supplements-0-id": "", "supplements-0-name": "test", "supplements-0-name_en": "", "supplements-0-language": "pl", "supplements-0-resource": "", "supplements-0-order": "0"}
    And admin's request posted files {"supplements-0-file": "simple.csv"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response page contains Dokonano wyboru niewłaściwego formatu dokumentu!

  Scenario: Resource creation fails if provided link starts with http:
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "http://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wymagany format protokołu to https://

  Scenario: Resource creation fails without title in form
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "", "description": "Opis zasobu", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains required id="id_title"></textarea><span class="help-inline"><ul class="errorlist"><li>To pole jest obowiązkowe.</li></ul>

# TODO (sto): This scenario checks if restored api resource does not run `process_resource_res_file_task`. 3rd step of refactor will cover this scenario, so for now, there is no need to rewrite this test to work without success handler on eager mode
#  Scenario: Restored draft api resource doesnt validate local file
#    Given draft remote file resource of api type with id 998
#    Then set status to published on resource with id 998
#    And resource with id 998 attributes are equal {"file_tasks_last_status": "", "link_tasks_last_status": "SUCCESS", "type": "api"}

  Scenario: Resource creation with regions is ok and regions are imported from api
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "switcher": "link", "file": "", "link": "https://test.to.resource.pl/1.xls", "dataset": 999, "data_date": "22.05.2020", "status": "published", "regions": ["0005084", "0918123"]}
    And admin's page with mocked geo api /resources/resource/add/ is requested
    Then admin's response status code is 200
    And resource has assigned main and additional regions
    And admin's response page contains /change/">test</a>" został pomyślnie dodany.

  Scenario: No Copy to new resource button creation page
    Given admin's request logged user is active user
    When admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page not contains Kopiuj do nowego
    And admin's response page not contains <a href="/resources/resource/add/?from_id=

@elasticsearch
Feature: Resource with file creation
  Scenario: Resource with file creation is ok
    Given dataset with id 999
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test resource title", "description": "more than 20 characters", "switcher": "file", "link": "", "dataset": 999, "data_date": "22.05.2020", "status": "published"}
    And request resource posted data contains simple file
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test resource title</a>" został pomyślnie dodany.
    And resource has assigned file

@otd_1152
Scenario Outline: Password protected archives are not allowed in file widget
    Given dataset with id 10000
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test resource title", "description": "more than 20 characters", "switcher": "file", "link": "", "dataset": 10000, "data_date": "22.05.2020", "status": "published"}
    And admin's request posted files <req_post_files>
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains <contained_value>
    And admin's response page not contains <value>

    Examples:
    | req_post_files                                 | contained_value                                             | value                                                        |
    | {"file": "regular.zip"}                        | /change/">test resource title</a>" został pomyślnie dodany. | Pliki archiwum zabezpieczone hasłem nie są dozwolone.        |
    | {"file": "encrypted_content.zip"}              | Pliki archiwum zabezpieczone hasłem nie są dozwolone.       | /change/">test resource title</a>" został pomyślnie dodany.  |

    | {"file": "regular.rar"}                        | /change/">test resource title</a>" został pomyślnie dodany. | Pliki archiwum zabezpieczone hasłem nie są dozwolone.        |
    | {"file": "encrypted_content.rar"}              | Pliki archiwum zabezpieczone hasłem nie są dozwolone.       | /change/">test resource title</a>" został pomyślnie dodany.  |
    | {"file": "encrypted_content_and_headers.rar"}  | Pliki archiwum zabezpieczone hasłem nie są dozwolone.       | /change/">test resource title</a>" został pomyślnie dodany.  |

    | {"file": "regular.7z"}                         | /change/">test resource title</a>" został pomyślnie dodany. | Pliki archiwum zabezpieczone hasłem nie są dozwolone.        |
    | {"file": "encrypted_content.7z"}               | Pliki archiwum zabezpieczone hasłem nie są dozwolone.       | /change/">test resource title</a>" został pomyślnie dodany.  |
    | {"file": "encrypted_content_and_headers.7z"}   | Pliki archiwum zabezpieczone hasłem nie są dozwolone.       | /change/">test resource title</a>" został pomyślnie dodany.  |

  Scenario Outline: Password protected archives added by link fail file validation
    Given dataset with id 10001
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test resource title", "description": "more than 20 characters", "switcher": "link", "dataset": 10001, "data_date": "22.05.2020", "status": "published"}
    And admin's request posted links <req_post_links>
    And admin's request save and continue will be chosen
    And 'mcod.resources.admin.ResourceAdmin' creation page is requested
    Then admin's response status code is 200
    And admin's response page contains <added message>

    Then admin's request method is GET
    And 'mcod.resources.admin.ResourceAdmin' edition page is requested for created object
    Then admin's response status code is 200
    And admin's response page contains <status>
    And admin's response page contains <message>
    And admin's response page contains <recommendation>

    Examples:
    | req_post_links                                 | status                                               | message                                                         | recommendation                                                                                      | added message                                                 |
    | {"link": "encrypted_content.zip"}              | <span class="label label-important">FAILURE</span>   | <td>Pliki archiwum zabezpieczone hasłem nie są dozwolone.</td>  | <td><p>Upewnij się, że podany link prowadzi do pliku archiwum niezabezpieczonego hasłem.</p></td>   | /change/">test resource title</a>" został pomyślnie dodany.   |
    | {"link": "encrypted_content.rar"}              | <span class="label label-important">FAILURE</span>   | <td>Pliki archiwum zabezpieczone hasłem nie są dozwolone.</td>  | <td><p>Upewnij się, że podany link prowadzi do pliku archiwum niezabezpieczonego hasłem.</p></td>   | /change/">test resource title</a>" został pomyślnie dodany.   |
    | {"link": "encrypted_content_and_headers.rar"}  | <span class="label label-important">FAILURE</span>   | <td>Pliki archiwum zabezpieczone hasłem nie są dozwolone.</td>  | <td><p>Upewnij się, że podany link prowadzi do pliku archiwum niezabezpieczonego hasłem.</p></td>   | /change/">test resource title</a>" został pomyślnie dodany.   |
    | {"link": "encrypted_content.7z"}               | <span class="label label-important">FAILURE</span>   | <td>Pliki archiwum zabezpieczone hasłem nie są dozwolone.</td>  | <td><p>Upewnij się, że podany link prowadzi do pliku archiwum niezabezpieczonego hasłem.</p></td>   | /change/">test resource title</a>" został pomyślnie dodany.   |
    | {"link": "encrypted_content_and_headers.7z"}   | <span class="label label-important">FAILURE</span>   | <td>Pliki archiwum zabezpieczone hasłem nie są dozwolone.</td>  | <td><p>Upewnij się, że podany link prowadzi do pliku archiwum niezabezpieczonego hasłem.</p></td>   | /change/">test resource title</a>" został pomyślnie dodany.   |

  Scenario Outline: Simple archives with single csv file added by link succeed file validation
    Given dataset with id 10002
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test resource title", "description": "more than 20 characters", "switcher": "link", "dataset": 10002, "data_date": "22.05.2020", "status": "published"}
    And admin's request posted links <req_post_links>
    And admin's request save and continue will be chosen
    And 'mcod.resources.admin.ResourceAdmin' creation page is requested
    Then admin's response status code is 200
    And admin's response page contains <added message>

    Then admin's request method is GET
    And 'mcod.resources.admin.ResourceAdmin' edition page is requested for created object
    Then admin's response status code is 200
    And admin's response page contains <status>
    And admin's response page not contains <failure status>

    Examples:
    | req_post_links                       | status                                               | added message                                                 | failure status                                      |
    | {"link": "regular.zip"}              | <span class="label label-success">SUCCESS</span>     | /change/">test resource title</a>" został pomyślnie dodany.   | <span class="label label-important">FAILURE</span>  |
    | {"link": "regular.rar"}              | <span class="label label-success">SUCCESS</span>     | /change/">test resource title</a>" został pomyślnie dodany.   | <span class="label label-important">FAILURE</span>  |
    | {"link": "regular.7z"}               | <span class="label label-success">SUCCESS</span>     | /change/">test resource title</a>" został pomyślnie dodany.   | <span class="label label-important">FAILURE</span>  |

  Scenario: Resource created with compressed xlsx has converted csv file
    Given dataset with id 9000
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test_zipped_xlsx", "description": "more than 20 characters", "switcher": "file", "link": "", "dataset": 9000, "data_date": "22.05.2020", "status": "published"}
    And admin's request posted files {"file": "xlsx_in_archive.zip"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And resource with title test_zipped_xlsx has zipped xlsx converted to csv

  @feat_dga
  Scenario Outline: DGA Resource creation
    Given dataset with pk 9000 for state institution
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020", "status": "published", "contains_protected_data": "True"}
    And admin's request posted files {"file": <file>}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains <added message>

    Examples:
    | file                                            | added message                                    |
    | "example_dga_xls_file.xls"                      | /change/">test dga</a>" został pomyślnie dodany. |
    | "example_dga_xlsx_file.xlsx"                    | /change/">test dga</a>" został pomyślnie dodany. |
    | "example_dga_comma_separated_csv_file.csv"      | /change/">test dga</a>" został pomyślnie dodany. |
    | "example_dga_semicolons_separated_csv_file.csv" | /change/">test dga</a>" został pomyślnie dodany. |

  @feat_dga
  Scenario Outline: Failed DGA Resource creation when invalid flags
    Given dataset with pk 9000 for state institution
    When admin's request method is POST
    And admin's request posted resource data is <req_data>
    And admin's request posted files {"file": "example_dga_comma_separated_csv_file.csv"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response page contains <error_message>

    Examples:
    | req_data                                                                                                                                                                                                                                | error_message                                                                                                                               |
    | {"status": "published", "contains_protected_data": "True", "has_dynamic_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}                   | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "published", "contains_protected_data": "True", "has_high_value_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}                | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "published", "contains_protected_data": "True", "has_high_value_data_from_ec_list": "True", "has_high_value_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}   | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "published", "contains_protected_data": "True", "has_research_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}                  | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "draft", "contains_protected_data": "True", "has_dynamic_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}                       | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "draft", "contains_protected_data": "True", "has_high_value_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}                    | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "draft", "contains_protected_data": "True", "has_high_value_data_from_ec_list": "True", "has_high_value_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}       | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |
    | {"status": "draft", "contains_protected_data": "True", "has_research_data": "True", "title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020"}                      | Aby tu wybrać TAK, w polach dotyczących danych dynamicznych, o wysokiej wartości, o wysokiej wartości z wykazu KE i badawczych zaznacz NIE. |

  @feat_dga
  Scenario Outline: Failed DGA Resource creation when invalid file type
    Given dataset with pk 9000 for state institution
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020", "status": "published", "contains_protected_data": "True"}
    And admin's request posted files {"file": <file>}
    And admin's page /resources/resource/add/ is requested
    Then admin's response page contains Wybierz plik z dysku w formacie xls, xlsx lub csv, jeśli poniżej oznaczasz zasób jako wykaz chronionych danych.

    Examples:
    | file                    |
    | "example_odt_file.odt"  |
    | "example_ods_file.ods"  |
    | "example.txt"           |
    | "example.pdf"           |

  @feat_dga
  Scenario Outline: Failed DGA Resource creation for not allowed institution
    Given dataset with pk 9000 for <institution_type> institution
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020", "status": "published", "contains_protected_data": "True"}
    And admin's request posted files {"file": "example_dga_comma_separated_csv_file.csv"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response page contains Wybierz zbiór instytucji rządowej lub samorządowej, jeśli poniżej oznaczasz zasób jako wykaz chronionych danych.
    And admin's response page contains Aby tu wybrać TAK, powyżej wybierz zbiór danych instytucji rządowej lub samorządowej.

    Examples:
    | institution_type |
    | private          |
    | other            |

  @feat_dga
  Scenario Outline: DGA Resource creation for allowed institution
    Given dataset with pk 9000 for <institution_type> institution
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020", "status": "published", "contains_protected_data": "True"}
    And admin's request posted files {"file": "example_dga_comma_separated_csv_file.csv"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains <added_message>

    Examples:
    | institution_type | added_message                                    |
    | local            | /change/">test dga</a>" został pomyślnie dodany. |
    | state            | /change/">test dga</a>" został pomyślnie dodany. |

  @feat_dga
  Scenario Outline: Failed DGA Resource creation when invalid file structure
    Given dataset with pk 9000 for state institution
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020", "status": "published", "contains_protected_data": "True"}
    And admin's request posted files {"file": <file>}
    And admin's page /resources/resource/add/ is requested
    Then admin's response page contains Zasób oznaczony poniżej jako wykaz chronionych danych może zawierać tylko kolumny nazwane w tej kolejności: Lp., Zasób chronionych danych, Format danych, Rozmiar danych, Warunki ponownego wykorzystywania.

    Examples:
    | file                                                        |
    | "example_invalid_dga_xls_file_contain_additional_cols.xls"  |
    | "example_invalid_dga_xls_file_not_contain_req_cols.xls"     |
    | "example_invalid_dga_xls_file_with_wrong_cols_order.xls"    |

  @feat_dga
  Scenario: Confirm addition of DGA Resource in the presence of an existing DGA Resource
    Given dataset with pk 9000 containing dga resource
    When admin's request method is POST
    And admin's request posted resource data is {"title": "new dga", "description": "more than 20 characters", "switcher": "file", "dataset": 9000, "data_date": "22.05.2020", "status": "published", "contains_protected_data": "True"}
    And admin's request posted files {"file": "example_dga_comma_separated_csv_file.csv"}
    And admin's page /resources/resource/add/ is requested
    Then admin's response page contains Czy na pewno chcesz, aby to był aktualny wykaz chronionych danych?
    When admin confirms saving the resource with posted data
    Then admin's response status code is 200
    And admin's response page contains /change/">new dga</a>" został pomyślnie dodany.
