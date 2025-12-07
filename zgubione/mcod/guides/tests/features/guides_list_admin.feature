@elasticsearch
Feature: Guides list page in admin panel

  Scenario: Portal guide section is not visible for editor
    Given admin's request logged user is editor user
    When admin's page /guides/ is requested
    Then admin's response status code is 404
    Then admin's response page not contains <a href="/guides/">Przewodnik po portalu</a>
    And admin's response page not contains <a href="/guides/guide/" class="changelink icon">Zmiana</a>

  Scenario: List of guides is not visible for editor
    Given admin's request logged user is editor user
    When admin's page /guides/guide is requested
    Then admin's response status code is 403

  Scenario: List of deleted guides (trash) is not visible for editor
    Given admin's request logged user is editor user
    When admin's page /guides/guidetrash is requested
    Then admin's response status code is 403

  Scenario: List of courses is visible for admin
    Given admin's request logged user is admin user
    When admin's page /guides/guide is requested
    Then admin's response status code is 200
    And admin's response page contains <a href="/guides/">Przewodnik po portalu</a>
    And admin's response page contains Dodaj kurs

  Scenario: List of deleted guides (trash) is visible for admin
    Given admin's request logged user is admin user
    And guide created with params {"id": 999, "title": "Testowy przewodnik w koszu", "is_removed": true}
    When admin's page /guides/guidetrash is requested
    Then admin's response status code is 200
    And admin's response page contains Testowy przewodnik w koszu
