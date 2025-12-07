Feature: Autocomplete
  Scenario: Resource autocomplete for admin
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource"}
    # forward is urlencoded: {"dataset":"999"}
    When admin's page /resource-autocomplete/?q=autocomplete&forward=%7B%22dataset%22%3A%22999%22%7D is requested
    Then admin's response status code is 200
    And admin's response body field results/[0]/id is 999
    And admin's response body field results/[0]/text is Test autocomplete resource (Opublikowany)
    And admin's response body field results/[0]/selected_text is Test autocomplete resource (Opublikowany)

  Scenario: Resource autocomplete for admin when resource id to exclude from results is passed
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource"}
    # forward is urlencoded: {"dataset":"999","id":999}
    When admin's page /resource-autocomplete/?q=autocomplete&forward=%7B%22dataset%22%3A%22999%22%2C%22id%22%3A999%7D is requested
    Then admin's response status code is 200
    And admin's response body field results is []

  Scenario: Resource autocomplete contains draft
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource", "status": "draft"}
    # forward is urlencoded: {"dataset":"999"}
    When admin's page /resource-autocomplete/?q=autocomplete&forward=%7B%22dataset%22%3A%22999%22%7D is requested
    Then admin's response status code is 200
    And admin's response body field results/[0]/id is 999
    And admin's response body field results/[0]/text is Test autocomplete resource (Szkic)
    And admin's response body field results/[0]/selected_text is Test autocomplete resource (Szkic)

  Scenario: Resource autocomplete contains resources in trash
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource", "is_removed": true}
    # forward is urlencoded: {"dataset":"999"}
    When admin's page /resource-autocomplete/?q=autocomplete&forward=%7B%22dataset%22%3A%22999%22%7D is requested
    Then admin's response status code is 200
    And admin's response body field results/[0]/id is 999
    And admin's response body field results/[0]/text is Test autocomplete resource (usunięty)
    And admin's response body field results/[0]/selected_text is Test autocomplete resource (usunięty)

  Scenario: Resource autocomplete without forward parameter
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource"}
    When admin's page /resource-autocomplete/?q=autocomplete is requested
    Then admin's response status code is 200
    And admin's response body field results is []

  Scenario: Resource autocomplete for logged out user
    Given admin's request user is unauthenticated
    And dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource"}
    When admin's page /resource-autocomplete/?q=autocomplete&forward=%7B%22dataset%22%3A%22999%22%7D is requested
    Then admin's response status code is 200
    And admin's response body field results is []

  Scenario: Resource autocomplete for editor without related organization
    Given admin's request logged user is editor user
    And dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "title": "Test autocomplete resource"}
    When admin's page /resource-autocomplete/?q=autocomplete&forward=%7B%22dataset%22%3A%22999%22%7D is requested
    Then admin's response status code is 200
    And admin's response body field results is []
