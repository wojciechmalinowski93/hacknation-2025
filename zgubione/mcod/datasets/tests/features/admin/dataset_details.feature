@elasticsearch
Feature: Dataset details

  Scenario: Imported dataset is not editable
    Given dataset for data {"id": 999} imported from ckan named Test Source with url http://example.com
    When admin's page /datasets/dataset/999/change/ is requested
    Then admin's response page is not editable
    Then admin's response page contains Obejrzyj zbiór danych
    Then admin's response page contains Sposób udostępnienia
    Then admin's response page contains CKAN

  Scenario: Imported dataset's history page is available for admin
    Given dataset for data {"id": 999} imported from ckan named Test Source with url http://example.com
    When admin's page /datasets/dataset/999/history/ is requested
    Then admin's response status code is 200

  Scenario: Imported dataset's history page is available for editor
    Given institution with id 999
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    And dataset for data {"id": 999, "organization_id": 999} imported from ckan named Test Source with url http://example.com
    When admin's page /datasets/dataset/999/history/ is requested
    Then admin's response status code is 200

  Scenario: Dataset resources tab has pagination
    Given dataset with id 999 and 2 resources
    When admin's page /datasets/dataset/999/change/ is requested
    Then admin's response page contains pagination-block

  Scenario: Dataset creation automatically creates slug from title
    Given institution with id 999
    And category with id 999
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "test@example.com", "title": "Dataset automatically created slug test", "notes": "more than 20 characters", "organization": [999], "categories": [999], "tags": [999], "tags_pl": [999]}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Dataset automatically created slug test</a>" został pomyślnie dodany.
    And datasets.Dataset with title Dataset automatically created slug test contains data {"slug": "dataset-automatically-created-slug-test"}

  Scenario: Admin can add tags to dataset
    Given institution with id 999
    And category with id 999
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "test@example.com", "title": "Admin can add tags to dataset test", "notes": "more than 20 characters", "categories": [999], "organization": [999], "tags": [999], "tags_pl": [999]}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Admin can add tags to dataset test</a>" został pomyślnie dodany.
    And datasets.Dataset with title Admin can add tags to dataset test contains data {"tags_list_as_str": "Tag1"}

  Scenario: Editor can add tags to dataset
    Given institution with id 999
    And category with id 999
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "test@example.com", "title": "Editor can add tags to dataset test", "notes": "more than 20 characters", "organization": [999], "categories": [999], "tags": [999], "tags_pl": [999]}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Editor can add tags to dataset test</a>" został pomyślnie dodany.
    And datasets.Dataset with title Editor can add tags to dataset test contains data {"tags_list_as_str": "Tag1"}

  Scenario: Dataset creation sets created_by to currently logged user
    Given institution with id 999
    And category with id 999
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "test@example.com", "title": "Dataset created_by set test", "notes": "more than 20 characters", "organization": [999], "categories": [999], "tags": [999], "tags_pl": [999]}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Dataset created_by set test</a>" został pomyślnie dodany.
    And datasets.Dataset with title Dataset created_by set test contains data {"created_by_id": 999}

  Scenario: Dataset creation with related resource at once
    Given institution with id 999
    And category with id 999
    And admin's request logged admin user created with params {"id": 999}
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "test@example.com", "notes": "more than 20 characters", "organization": [999], "categories": [999], "tags": [999], "tags_pl": [999], "resources-2-TOTAL_FORMS": "1", "resources-2-0-switcher": "link", "resources-2-0-link": "https://test.pl", "resources-2-0-title": "123", "resources-2-0-description": "<p>more than 20 characters</p>", "resources-2-0-status": "published", "resources-2-0-id": "", "resources-2-0-dataset": ""}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Test with dataset title</a>" został pomyślnie dodany.
    And resources.Resource with title 123 contains data {"link": "https://test.pl", "created_by_id": 999, "modified_by_id": 999}

  Scenario: Dataset creation with related resource file at once
    Given institution with id 999
    And category with id 999
    And admin's request logged admin user created with params {"id": 999}
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "test@example.com", "notes": "more than 20 characters", "organization": [999], "categories": [999], "tags": [999], "tags_pl": [999], "resources-2-TOTAL_FORMS": "1", "resources-2-0-switcher": "file", "resources-2-0-title": "file-test-123", "resources-2-0-description": "<p>more than 20 characters</p>", "resources-2-0-status": "published", "resources-2-0-id": "", "resources-2-0-dataset": "", "resources-2-0-data_date": "2022-01-01"}
    And admin's request posted files {"resources-2-0-file": "unique_simple.csv"}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Test with dataset title</a>" został pomyślnie dodany.
    And Resource with title file-test-123 has assigned file unique_simple.csv

  Scenario: Dataset modified attribute is set
    Given institution with id 999
    And category with id 999
    And admin's request logged admin user created with params {"id": 999}
    And tag created with params {"id": 999, "name": "Tag1", "language": "pl"}
    When admin's request method is POST
    And admin's request posted dataset data is {"title": "test metadata_modified title", "slug": "Test", "notes": "more than 20 characters", "organization": [999], "url": "http://cos.tam.pl", "update_frequency": "weekly", "update_notification_recipient_email": "test@example.com", "license_id": "other-pd", "status": "published", "categories": [999], "tags": [999], "tags_pl": [999], "resources-2-TOTAL_FORMS": "1", "resources-2-0-switcher": "link", "resources-2-0-link": "https://test.pl", "resources-2-0-title": "123", "resources-2-0-description": "<p>more than 20 characters</p>", "resources-2-0-status": "published", "resources-2-0-id": "", "resources-2-0-dataset": ""}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test metadata_modified title</a>" został pomyślnie dodany.
    And latest dataset attribute title is test metadata_modified title
    And latest dataset attribute modified is not None

  Scenario: Imported dataset is correctly displayed in trash for admin
    Given dataset for data {"id": 999, "is_removed": true} imported from ckan named Test Source with url http://example.com
    When admin's page /datasets/datasettrash/999/change/ is requested
    Then admin's response page is not editable

  Scenario: Removed dataset is correctly displayed in trash for editor
    Given logged editor user
    And dataset created with params {"id": 999, "is_removed": true}
    When admin's page /datasets/datasettrash/999/change/ is requested
    Then admin's response page is not editable

  Scenario Outline: Dataset details page is properly displayed even if pagination param is invalid
    Given dataset with id 999
    And resource created with params {"id": 998, "title": "dataset resources pagination test", "dataset_id": 999}
    When admin's page <page_url> is requested
    Then admin's response page contains dataset resources pagination test
    Examples:
    | page_url                            |
    | /datasets/dataset/999/change/?p=X   |
    | /datasets/dataset/999/change/?p=999 |
    | /datasets/dataset/999/change/?all=  |

  Scenario: Dataset details page contains related resources
    Given logged editor user
    And dataset with id 999
    And resource created with params {"id": 998, "title": "dataset with resources test", "dataset_id": 999}
    When admin's page /datasets/dataset/999/change is requested
    Then admin's response page contains dataset with resources test

  Scenario: Notification mail is updated after dataset edition by editor
    Given institution with id 999
    And category with id 999
    And tag created with params {"id": 998, "name": "Tag1", "language": "pl"}
    And admin's request logged editor user created with params {"id": 1000, "organizations": [999], "email": "editor@dane.gov.pl"}
    And dataset with id 1001 and institution 999
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "temp@dane.gov.pl", "organization": [999], "categories": [999], "tags_pl": [998]}
    And admin's page /datasets/dataset/1001/change/ is requested
    Then datasets.Dataset with id 1001 contains data {"update_notification_recipient_email": "editor@dane.gov.pl"}

  Scenario: Notification mail is not updated after dataset edition by superuser
    Given institution with id 999
    And category with id 999
    And tag created with params {"id": 998, "name": "Tag1", "language": "pl"}
    And admin's request logged admin user created with params {"id": 1000, "organizations": [999], "email": "superuser@dane.gov.pl"}
    And dataset with id 1001 and institution 999
    When admin's request method is POST
    And admin's request posted dataset data is {"update_notification_recipient_email": "temp@dane.gov.pl", "organization": [999], "categories": [999], "tags_pl": [998]}
    And admin's page /datasets/dataset/1001/change/ is requested
    Then datasets.Dataset with id 1001 contains data {"update_notification_recipient_email": "temp@dane.gov.pl"}

  Scenario: Resource title on inline list redirects to resource admin edit page
    Given dataset with id 999
    And resource created with params {"id": 998, "title": "Title as link", "dataset_id": 999}
    When admin's page /datasets/dataset/999/change/#resources is requested
    Then admin's response page contains <a href="/resources/resource/998/change/">Title as link</a>

  Scenario: Promoted datasets limit is raised
    Given 5 promoted datasets
    When admin's request method is POST
    And admin's request posted dataset data is {"is_promoted": true}
    And admin's page /datasets/dataset/add/ is requested
    Then admin's response page contains Obecnie zostało już zaznaczone 5 zbiorów danych jako promowane. Jeżeli chcesz zaznaczyć ten zbiór musisz odznaczyć inny.

  Scenario: Dataset promotion is disabled when dataset is moved to trash
    Given dataset created with params {"id": 999, "is_promoted": true}
    When admin's request method is POST
    And admin's request posted dataset data is {"post": "yes"}
    And admin's page /datasets/dataset/999/delete/ is requested
    Then admin's response status code is 200
    And datasets.Dataset with id 999 contains data {"is_promoted": false}

  Scenario: Admin can add supplements to dataset
    When admin's page /datasets/dataset/add/ is requested
    Then admin's response page contains Pliki dokumentów mające na celu uzupełnienie danych znajdujących się w zbiorze.
    And admin's response page contains Dodaj dokument

  Scenario: Editor can add supplements to dataset
    Given institution with id 999
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    When admin's page /datasets/dataset/add/ is requested
    Then admin's response page contains Pliki dokumentów mające na celu uzupełnienie danych znajdujących się w zbiorze.
    And admin's response page contains Dodaj dokument

  Scenario: Method of sharing is visible on dataset edit form
    Given dataset with id 999 and 2 resources
    When admin's page /datasets/dataset/999/change/ is requested
    Then admin's response page contains Sposób udostępnienia
    Then admin's response page contains Manualnie

  Scenario Outline: Method of sharing is visible on dataset edit form for harvested resources
    Given dataset for data {"id": 999} imported from <source_type> named Test Source with url http://example.com
    When admin's page /datasets/dataset/999/change/ is requested
    Then admin's response page contains Sposób udostępnienia
    Then admin's response page contains <source_type_label>

    Examples:
      | source_type | source_type_label |
      | ckan        | CKAN              |
      | xml         | XML               |
      | dcat        | DCAT-AP           |

  Scenario: Method of sharing is hidden for editors on dataset edit form
    Given institution with id 999
    And dataset with id 1001 and institution 999
    And admin's request logged editor user created with params {"id": 1000, "organizations": [999]}
    When admin's page /datasets/dataset/1001/change/ is requested
    Then admin's response page contains Zmień zbiór danych
    Then admin's response page not contains Sposób udostępnienia
