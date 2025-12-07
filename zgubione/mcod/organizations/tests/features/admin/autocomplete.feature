Feature: Autocomplete
  Scenario: Organization autocomplete for admin
    Given institution created with params {"id": 999, "title": "Test autocomplete institution"}
    When admin's page /organization-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results/[0]/id is 999
    And admin's response body field results/[0]/text is Test autocomplete institution
    And admin's response body field results/[0]/selected_text is Test autocomplete institution

  Scenario: Organization autocomplete for logged out user
    Given admin's request user is unauthenticated
    And institution created with params {"id": 999, "title": "Test autocomplete institution"}
    When admin's page /organization-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results is []

  Scenario: Organization autocomplete for editor without related organization
    Given admin's request logged user is editor user
    And institution created with params {"id": 999, "title": "Test autocomplete institution"}
    When admin's page /organization-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results is []
