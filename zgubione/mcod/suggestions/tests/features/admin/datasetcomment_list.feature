@elasticsearch
Feature: Dataset comments list page in admin panel

  Scenario: Dataset comments list page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/datasetcomment/ is requested
    Then admin's response status code is 403
    Then admin's response page not contains Uwagi do zbiorów danych

  Scenario: Dataset comments list page is visible for superuser
    Given admin's request logged user is admin user
    And dataset created with params {"id":999, "title":"Testowa nazwa zbioru danych"}
    And datasetcomment created with params {"id": 999, "dataset_id": 999,  "comment": "Testowa uwaga do zbioru danych"}
    When admin's page /suggestions/datasetcomment/ is requested
    Then admin's response status code is 200
    And admin's response page contains Uwagi do zbiorów danych
    And admin's response page contains Testowa nazwa zbioru danych

  Scenario: Dataset comments list page is filtered by decision
    Given admin's request logged user is admin user
    And dataset created with params {"id":999, "title":"Testowa nazwa zbioru danych"}
    And datasetcomment created with params {"id": 999, "dataset_id": 999,  "comment": "Testowa uwaga bez decyzji", "decision": ""}
    When admin's page /suggestions/datasetcomment/?decision=not_taken is requested
    Then admin's response status code is 200
    And admin's response page contains Uwagi do zbiorów danych
    And admin's response page contains Testowa nazwa zbioru danych

  Scenario: Dataset comments list - Trash page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/datasetcommenttrash/ is requested
    Then admin's response status code is 403
    Then admin's response page not contains Uwagi do zbiorów danych - kosz

  Scenario: Dataset comment details page is visible for superuser
    Given admin's request logged user is admin user
    And dataset created with params {"id":999, "title":"Testowa nazwa zbioru danych"}
    And datasetcomment created with params {"id": 999, "dataset_id": 999,  "comment": "Testowa uwaga do zbioru danych"}
    When admin's page /suggestions/datasetcomment/999/change is requested
    Then admin's response status code is 200
    And admin's response page contains Testowa nazwa zbioru danych
    And admin's response page contains Testowa uwaga do zbioru danych

  Scenario: Dataset comments list - Trash page is visible for superuser
    Given admin's request logged user is admin user
    When admin's page /suggestions/datasetcommenttrash/ is requested
    Then admin's response status code is 200
    Then admin's response page contains Uwagi do zbiorów danych - kosz
