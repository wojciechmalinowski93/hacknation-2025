@elasticsearch
Feature: lab_events list page in admin panel

  Scenario: Open Data laboratory section is not visible for NOT laboratory admin
    Given admin's request logged user is editor user
    When admin's page /laboratory/ is requested
    Then admin's response status code is 404
    Then admin's response page not contains <a href="/laboratory">Laboratorium Otwarte Dane</a>
    And admin's response page not contains <a href="/laboratory/lab_event/" class="changelink icon">Zmiana</a>

  Scenario: List of lab_events is not visible for NOT laboratory admin
    Given admin's request logged user is editor user
    When admin's page /laboratory/labevent is requested
    Then admin's response status code is 403

  Scenario: List of deleted lab_events (trash) is not visible for NOT laboratory admin
    Given admin's request logged user is editor user
    When admin's page /laboratory/labeventtrash is requested
    Then admin's response status code is 403

  Scenario: List of lab_events is visible for laboratory admin
    Given admin's request logged user is laboratory admin
    When admin's page /laboratory/labevent is requested
    Then admin's response status code is 200
    And admin's response page contains <a href="/laboratory/">Laboratorium</a>
    And admin's response page contains Dodaj Obiekt

  Scenario: List of deleted lab_events (trash) is visible for laboratory admin
    Given admin's request logged user is laboratory admin
    And lab_event created with params {"id": 999, "title": "Testowa analiza w koszu", "is_removed": true}
    When admin's page /laboratory/labeventtrash is requested
    Then admin's response status code is 200
    And admin's response page contains Testowa analiza w koszu
