@elasticsearch
Feature: Dataset submission

  Scenario: Dataset submission list page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/datasetsubmission/ is requested
    Then admin's response status code is 403
    And admin's response page not contains Wybierz propozycję nowych danych do zmiany

  Scenario: Dataset submission list page is visible for superuser
    Given admin's request logged user is admin user
    And dataset with id 999
    And datasetsubmission created with params {"id": 999, "title": "Testowa propozycja nowych danych"}
    When admin's page /suggestions/datasetsubmission/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz propozycję nowych danych do zmiany
    And admin's response page contains Testowa propozycja nowych danych

  Scenario: Dataset submission list - Trash page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/datasetsubmissiontrash/ is requested
    Then admin's response status code is 403
    And admin's response page not contains Propozycje nowych danych - kosz

  Scenario: Dataset submission list - Trash page is visible for superuser
    Given admin's request logged user is admin user
    And dataset with id 999
    And datasetsubmission created with params {"id": 999, "title": "Testowa propozycja w koszu", "is_removed": true}
    When admin's page /suggestions/datasetsubmissiontrash/ is requested
    Then admin's response status code is 200
    And admin's response page contains Propozycje nowych danych - kosz
    And admin's response page contains Testowa propozycja w koszu

  Scenario: Dataset submission is being accepted by admin
    Given admin's request logged user is admin user
    And dataset with id 999
    And datasetsubmission created with params {"id": 999, "title": "Testowa propozycja w koszu", "decision": ""}
    When admin's request method is POST
    And admin's request posted datasetsubmission data is {"decision": "accepted"}
    And admin's page /suggestions/datasetsubmission/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Zadanie utworzenia zaakceptowanej propozycji nowych danych zostało uruchomione!
