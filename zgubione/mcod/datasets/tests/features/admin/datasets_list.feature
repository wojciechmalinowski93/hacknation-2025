@elasticsearch
Feature: Datasets list

  Scenario: Page with list of datasets works fine
    Given dataset created with params {"id": 999, "title": "Dataset on list"}
    When admin's page /datasets/dataset/ is requested
    Then admin's response page contains Dataset on list
    And admin's response page contains Filtruj według nazwy instytucji
    And admin's response page contains Promowane zbiory danych

  Scenario: Imported dataset is visible on list
    Given dataset for data {"id": 999, "title": "CKAN Imported Dataset"} imported from ckan named Test Source with url http://example.com
    When admin's page /datasets/dataset/ is requested
    Then admin's response page contains CKAN Imported Dataset

  Scenario: Removed datasets are not on datasets list
    Given dataset created with params {"id": 999, "is_removed": true, "title": "Removed dataset 999"}
    When admin's page /datasets/dataset/ is requested
    Then admin's response page not contains Removed dataset 999

  Scenario: Removed dataset is visible in trash for admin
    Given dataset created with params {"id": 999, "is_removed": true, "title": "Removed dataset visible in trash"}
    When admin's page /datasets/datasettrash/ is requested
    Then admin's response page contains Removed dataset visible in trash

  Scenario: Removed dataset is visible in trash for editor
    Given institution with id 999
    And admin's request logged editor user created with params {"id": 999, "organizations": [999]}
    And dataset created with params {"id": 999, "organization_id": 999, "is_removed": true, "title": "Removed dataset visible in trash", "created_by_id": 999}
    When admin's page /datasets/datasettrash/ is requested
    Then admin's response page contains Removed dataset visible in trash

  Scenario: Not removed dataset is not visible in trash
    Given dataset created with params {"id": 999, "title": "Not removed dataset not visible in trash"}
    When admin's page /datasets/datasettrash/ is requested
    Then admin's response page not contains Not removed dataset not visible in trash

  Scenario: Imported removed dataset is visible in trash for admin
    Given dataset for data {"id": 999, "title": "Imported removed dataset visible in trash", "is_removed": true} imported from ckan named Test Source with url http://example.com
    When admin's page /datasets/datasettrash/ is requested
    Then admin's response page contains Imported removed dataset visible in trash

  Scenario: Filtering for promoted datasets
    Given dataset created with params {"id": 999, "title": "Promoted dataset", "is_promoted": true}
    When admin's page /datasets/dataset/?is_promoted=on is requested
    Then admin's response page contains Promoted dataset
    And admin's response page contains <tr class="row1 info">

  Scenario: Filtering for not promoted datasets
    Given dataset created with params {"id": 999, "title": "Not promoted dataset", "is_promoted": false}
    When admin's page /datasets/dataset/?is_promoted=on is requested
    Then admin's response page not contains Not promoted dataset
    And admin's response page not contains <tr class="row1 info">
