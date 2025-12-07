@sparql
Feature: Manage organization in SPARQL database

  Scenario: Test that organization is created in sparql database.
    Given institution created with params {"id": 999, "slug": "test-institution-slug"}
    Then sparql store contains subject <http://test.mcod/pl/institution/999,test-institution-slug>

  Scenario: Removed organization is deleted from sparql database.
    Given institution created with params {"id": 999, "slug": "test-institution-slug"}
    And remove institution with id 999
    Then sparql store does not contain subject <http://test.mcod/pl/institution/999,test-institution-slug>

  Scenario: Switching organization to draft deletes it from sparql database.
    Given institution created with params {"id": 999, "slug": "test-institution-slug"}
    Then set status to draft on institution with id 999
    And sparql store does not contain subject <http://test.mcod/pl/institution/999,test-institution-slug>

  Scenario: Restoring organization creates it in sparql database.
    Given institution created with params {"id": 999, "slug": "test-institution-slug", "status": "draft"}
    Then sparql store does not contain subject <http://test.mcod/pl/institution/999,test-institution-slug>
    And set status to published on institution with id 999
    And sparql store contains subject <http://test.mcod/pl/institution/999,test-institution-slug>
