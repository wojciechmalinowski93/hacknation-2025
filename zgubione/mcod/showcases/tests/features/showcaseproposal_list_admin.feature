Feature: ShowcaseProposal list
  Scenario: ShowcaseProposal list with decision
    Given dataset with id 999
    And showcaseproposal created with params {"id": 999, "title": "Test accepted showcaseproposal", "datasets": [999], "category": "app", "decision": "accepted"}
    When admin's page /showcases/showcaseproposal/?decision=taken is requested
    Then admin's response status code is 200
    And admin's response page contains Test accepted showcaseproposal
  Scenario: ShowcaseProposal list without decision
    Given dataset with id 999
    And showcaseproposal created with params {"id": 999, "title": "Test showcaseproposal without decision", "datasets": [999], "category": "app", "decision": ""}
    When admin's page /showcases/showcaseproposal/?decision=not_taken is requested
    Then admin's response status code is 200
    And admin's response page contains Test showcaseproposal without decision
  Scenario: ShowcaseProposal list export to csv
    Given dataset with id 999
    And showcaseproposal created with params {"id": 999, "title": "Test showcaseproposal without decision", "datasets": [999], "category": "app", "decision": ""}
    When admin's request method is POST
    And admin's request posted action data is {"action": "export_to_csv", "_selected_action": 999}
    And admin's page /showcases/showcaseproposal/ is requested
    Then admin's response status code is 200
    And admin's response page contains Tworzenie pliku CSV dodane do kolejki zadań
