Feature: Special signs list page in admin panel

  Scenario: Special signs list page is not visible for editor
    Given admin's request logged user is editor user
    When admin's page /special_signs/specialsign is requested
    Then admin's response status code is 403

  Scenario: Special signs list page is visible for admin
    Given admin's request logged user is admin user
    When admin's page /special_signs/specialsign is requested
    Then admin's response status code is 200
    And admin's response page contains Dodaj znak umowny
