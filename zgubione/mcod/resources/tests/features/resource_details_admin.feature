@elasticsearch
Feature: Resource details page in admin panel

  Scenario: Change resource
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "type": "file"}
    When admin's request method is POST
    And admin's request posted resource data is {"title": "title changed in form", "description": "<p>more than 20 characters</p>", "dataset": [999], "status": "published", "data_date": "2021-05-04"}
    And admin's page /resources/resource/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains title changed in form
    And admin's response resolved url name is resources_resource_changelist

  Scenario: Imported resource is not editable in admin panel
    Given resource with id 999 imported from ckan named Test Source with url http://example.com
    When admin's page /resources/resource/999/change/ is requested
    Then admin's response page is not editable

  Scenario: Forced file type checkbox is hidden for imported api resource
    Given resource with id 999 imported from ckan named Test Source with url http://example.com and type api
    When admin's page /resources/resource/999/change/ is requested
    Then admin's response page not contains forced_file_type

  Scenario: Change type is run successfully
    Given dataset with id 999
    And geo_tabular_data_resource with params {"id": 999, "dataset_id": 999}
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test geo csv", "description": "<p>more than 20 characters</p>", "dataset": 999, "data_date": "2021-05-04", "status": "published", "show_tabular_view": "on", "schema_type_0": "string", "schema_type_1": "string", "schema_type_2": "number", "schema_type_3": "integer", "geo_0": "", "geo_1": "", "geo_2": "", "geo_3": "", "_change_type": ""}
    And admin's page /resources/resource/999/change/ is requested
    Then admin's response page contains Zmieniono typ danych

  Scenario: Map save is run successfully
    Given dataset with id 999
    And geo_tabular_data_resource with params {"id": 999, "dataset_id": 999}
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test geo csv", "description": "<p>more than 20 characters</p>", "dataset": 999, "data_date": "2021-05-04", "status": "published", "show_tabular_view": "on", "schema_type_0": "string", "schema_type_1": "string", "schema_type_2": "integer", "schema_type_3": "integer", "geo_0": "", "geo_1": "label", "geo_2": "l", "geo_3": "b", "_map_save": ""}
    And admin's page /resources/resource/999/change/ is requested
    Then admin's response page contains Zapisano definicję mapy

  Scenario: Auto data date checkbox is visible on form for resource with type api
    Given draft remote file resource of api type with id 998
    When admin's page /resources/resource/998/change/ is requested
    Then admin's response page contains is_auto_data_date
    Then admin's response page has element label with Aktualizacja automatyczna

  Scenario: Auto data date checkbox is not visible on form for resource with type file
    Given resource created with params {"id": 1999, "type": "file"}
    When admin's page /resources/resource/1999/change/ is requested
    Then admin's response page contains Zmień zasób
    Then admin's response page doesn't have element label with Aktualizacja automatyczna

  Scenario: Admin can add supplements to resource
    When admin's page /resources/resource/add/ is requested
    Then admin's response page contains Pliki dokumentów mające na celu uzupełnienie danych znajdujących się w zasobie.
    And admin's response page contains Dodaj dokument

  Scenario: Editor can add supplements to resource
    Given institution with id 999
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    When admin's page /resources/resource/add/ is requested
    Then admin's response page contains Pliki dokumentów mające na celu uzupełnienie danych znajdujących się w zasobie.
    And admin's response page contains Dodaj dokument

  Scenario: Openness score is visible on resource edit form
    Given resource created with params {"id": 1999, "type": "file"}
    When admin's page /resources/resource/1999/change/ is requested
    Then admin's response page contains Poziom otwartości danych

  Scenario: Method of sharing is visible on resource edit form
    Given resource created with params {"id": 1999, "type": "file"}
    When admin's page /resources/resource/1999/change/ is requested
    Then admin's response page contains Sposób udostępnienia
    Then admin's response page contains Manualnie

  Scenario: Method of sharing is hidden for editors on resource edit form
    Given institution with id 999
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    And resource created with params {"id": 1999, "type": "file"}
    When admin's page /resources/resource/1999/change/ is requested
    Then admin's response page not contains Sposób udostępnienia
