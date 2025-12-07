@sparql
Feature: Manage resource in SPARQL database
  Scenario: Resource is created in sparql database.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    Then sparql store contains subject <http://test.mcod/pl/dataset/999/resource/999>

  Scenario: Removing resource deletes it from sparql database.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    And remove resource with id 999
    Then sparql store does not contain subject <http://test.mcod/pl/dataset/999/resource/999>

  Scenario: Switching resource to draft deletes it from sparql database.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    Then set status to draft on resource with id 999
    And sparql store does not contain subject <http://test.mcod/pl/dataset/999/resource/999>

  Scenario: Restoring resource creates it in sparql database.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999, "status": "draft"}
    Then sparql store does not contain subject <http://test.mcod/pl/dataset/999/resource/999>
    And set status to published on resource with id 999
    And sparql store contains subject <http://test.mcod/pl/dataset/999/resource/999>

  Scenario: Creating resource updates related dataset
    Given dataset with id 998, slug test-rdf and resources
    Then sparql store contains triple with attributes {"subject":"<http://test.mcod/pl/dataset/998,test-rdf>", "predicate":"<http://www.w3.org/ns/dcat#distribution>"}
