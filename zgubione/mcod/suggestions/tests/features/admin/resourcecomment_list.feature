@elasticsearch
Feature: Resource comments list page in admin panel

  Scenario: Resource comments list page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/resourcecomment/ is requested
    Then admin's response status code is 403
    And admin's response page not contains Uwagi do danych

  Scenario: Resource comments list page is visible for superuser
    Given admin's request logged user is admin user
    And resource with id 999
    And resourcecomment created with params {"id": 999, "resource_id": 999, "comment": "Komentarz XYZ"}
    When admin's page /suggestions/resourcecomment/ is requested
    Then admin's response status code is 200
    Then admin's response page contains Wybierz uwagę do danych do zmiany
    And admin's response page contains Komentarz XYZ

  Scenario: Resource comment details page is visible for superuser
    Given admin's request logged user is admin user
    And resource with id 999
    And resourcecomment created with params {"id": 999, "resource_id": 999, "comment": "Komentarz XYZ"}
    When admin's page /suggestions/resourcecomment/999/change is requested
    Then admin's response status code is 200
    And admin's response page contains Zmień uwagę do danych
    And admin's response page contains Komentarz XYZ

  Scenario: Resource comments list - Trash page is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /suggestions/resourcecommenttrash/ is requested
    Then admin's response status code is 403
    And admin's response page not contains Uwagi do danych - kosz

  Scenario: Resource comments list - Trash page is visible for superuser
    Given admin's request logged user is admin user
    And resource with id 999
    And resourcecomment created with params {"id": 999, "resource_id": 999, "comment": "Komentarz YZ", "is_removed": true}
    When admin's page /suggestions/resourcecommenttrash/ is requested
    Then admin's response status code is 200
    And admin's response page contains Uwagi do danych - kosz
    And admin's response page contains Komentarz YZ
