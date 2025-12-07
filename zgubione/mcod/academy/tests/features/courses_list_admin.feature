@elasticsearch
Feature: Courses list page in admin panel

  Scenario: Open Data Academy section is not visible for NOT academy admin
    Given admin's request logged user is editor user
    When admin's page /academy/ is requested
    Then admin's response status code is 404
    Then admin's response page not contains <a href="/academy">Akademia Otwarte Dane</a>
    And admin's response page not contains <a href="/academy/course/" class="changelink icon">Zmiana</a>

  Scenario: List of courses is not visible for NOT academy admin
    Given admin's request logged user is editor user
    When admin's page /academy/course is requested
    Then admin's response status code is 403

  Scenario: List of deleted courses (trash) is not visible for NOT academy admin
    Given admin's request logged user is editor user
    When admin's page /academy/coursetrash is requested
    Then admin's response status code is 403

  Scenario: List of courses is visible for academy admin
    Given admin's request logged user is academy admin
    When admin's page /academy/course is requested
    Then admin's response status code is 200
    And admin's response page contains <a href="/academy/course">Akademia Otwarte Dane</a>
    And admin's response page contains Dodaj kurs

  Scenario: List of deleted courses (trash) is visible for academy admin
    Given admin's request logged user is academy admin
    And course created with params {"id": 999, "title": "Testowy kurs w koszu", "is_removed": true}
    When admin's page /academy/coursetrash is requested
    Then admin's response status code is 200
    And admin's response page contains Testowy kurs w koszu
