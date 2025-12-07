@elasticsearch
Feature: LabEvent details page in admin panel

  Scenario: LabEvent change page is not visible for NOT laboratory admin
    Given lab_event with id 999
    And admin's request logged user is active user
    When admin's page /laboratory/labevent/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Zaloguj się

  Scenario: LabEvents change page is visible for laboratory admin
    Given admin's request logged user is laboratory admin
    And lab_event created with params {"id": 999, "title": "Testowy obiekt laboratorium 999"}
    When admin's page /laboratory/labevent/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Testowy obiekt laboratorium 999
