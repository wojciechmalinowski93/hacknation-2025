@elasticsearch
Feature: Resources list in admin panel

  Scenario: Admin can see resources on list
    Given resource created with params {"id": 999, "title": "Test widoczności zasobu na liście"}
    When admin's page /resources/resource/ is requested
    Then admin's response status code is 200
    And admin's response page contains Test widoczności zasobu na liście
    # next line tests dal_admin_filters widget.
    And admin's response page contains Filtruj według nazwy zbioru
    And admin's response page contains Filtruj według nazwy instytucji

  Scenario: Admin shouldnt see deleted resources on list
    Given resource created with params {"id": 999, "title": "Test widoczności zasobu na liście", "is_removed": true}
    When admin's page /resources/resource/ is requested
    Then admin's response status code is 200
    And admin's response page not contains Test widoczności zasobu na liście

  Scenario: Editor shouldnt see deleted resources
    Given dataset with id 999 and institution 999
    And resource created with params {"id": 999, "title": "Test widoczności zasobu na liście", "is_removed": true, "dataset_id": 999}
    And admin's request logged editor user created with params {"organizations": [999]}
    When admin's page /resources/resource/ is requested
    Then admin's response status code is 200
    And admin's response page not contains Test widoczności zasobu na liście

  Scenario: Resources converted from csv to jsonld are returned in results when jsonld format is filtered
    Given resource with csv file converted to jsonld with params {"id": 999, "title": "Test filtrowania wg formatu"}
    When admin's page /resources/resource/?format=jsonld is requested
    Then admin's response status code is 200
    And admin's response page contains Test filtrowania wg formatu
