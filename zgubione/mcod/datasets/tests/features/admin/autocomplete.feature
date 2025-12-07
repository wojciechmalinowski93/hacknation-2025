Feature: Autocomplete
  Scenario: Datasets autocomplete for admin
    Given dataset created with params {"id": 999, "title": "Test autocomplete dataset"}
    When admin's page /dataset-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results/[0]/id is 999
    And admin's response body field results/[0]/text is Test autocomplete dataset
    And admin's response body field results/[0]/selected_text is Test autocomplete dataset

  Scenario: Datasets autocomplete only published in results
    Given dataset created with params {"id": 999, "title": "Test autocomplete dataset", "status": "draft"}
    When admin's page /dataset-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results is []

  Scenario: Datasets autocomplete for logged out user
    Given admin's request user is unauthenticated
    And dataset created with params {"id": 999, "title": "Test autocomplete dataset"}
    When admin's page /dataset-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results is []

  Scenario: Datasets autocomplete for editor without related organization
    Given admin's request logged user is editor user
    And institution with id 999
    And dataset created with params {"id": 999, "title": "Test autocomplete dataset", "organization_id": 999}
    When admin's page /dataset-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results is []
