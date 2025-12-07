@elasticsearch
Feature: Accepted Dataset submission

  Scenario: Accepted dataset submission list page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/accepteddatasetsubmission/ is requested
    Then admin's response status code is 403
    Then admin's response page not contains Wybierz zaakceptowaną propozycję nowych danych do zmiany

  Scenario: Accepted dataset submission list page is visible for superuser
    Given admin's request logged user is admin user
    And dataset with id 999
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When admin's page /suggestions/accepteddatasetsubmission/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz zaakceptowaną propozycję nowych danych do zmiany
    And admin's response page contains Testowa zaakceptowana propozycja nowych danych

  Scenario: Accepted dataset submission details page is visible for superuser
    Given admin's request logged user is admin user
    And dataset with id 999
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When admin's page /suggestions/accepteddatasetsubmission/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Zmień zaakceptowaną propozycję nowych danych
    And admin's response page contains Testowa zaakceptowana propozycja nowych danych

  Scenario: Accepted dataset submission is validated for status and is_published_for_all
    Given admin's request logged user is admin user
    And dataset with id 999
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When admin's request method is POST
    And admin's request posted datasetsubmission data is {"title": "Testowa zaakceptowana propozycja nowych danych", "notes": "notes", "status": "draft", "is_published_for_all": true}
    And admin's page /suggestions/accepteddatasetsubmission/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Jeżeli chcesz opublikować propozycję nowych danych dla wszystkich użytkowników to propozycja musi posiadać status &quot;Opublikowany&quot;

  Scenario: Accepted dataset submission update
    Given admin's request logged user is admin user
    And dataset with id 999
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When admin's request method is POST
    And admin's request posted datasetsubmission data is {"title": "Testowa zaakceptowana propozycja nowych danych", "notes": "notes", "status": "published", "is_published_for_all": true}
    And admin's page /suggestions/accepteddatasetsubmission/999/change/ is requested
    Then admin's response status code is 200

  Scenario: Accepted dataset submission list - Trash page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/accepteddatasetsubmissiontrash/ is requested
    Then admin's response status code is 403
    Then admin's response page not contains Zaakceptowane propozycje nowych danych - kosz

  Scenario: Accepted Dataset submission list - Trash page is visible for superuser
    Given admin's request logged user is admin user
    And dataset with id 999
    And accepteddatasetsubmission created with params {"id": 999, "title": "Zaakceptowana propozycja nowych danych w koszu", "is_removed": true}
    When admin's page /suggestions/accepteddatasetsubmissiontrash/ is requested
    Then admin's response status code is 200
    Then admin's response page contains Zaakceptowane propozycje nowych danych - kosz
