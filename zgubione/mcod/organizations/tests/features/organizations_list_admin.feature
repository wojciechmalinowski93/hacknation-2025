@elasticsearch
Feature: Organizations list

  Scenario: Export to CSV action is available in actions dropdown for superuser
    Given 3 institutions
    And admin's request logged user is admin user
    When admin's page /organizations/organization/ is requested
    Then admin's response status code is 200
    And admin's response page contains <option value="export_to_csv">
