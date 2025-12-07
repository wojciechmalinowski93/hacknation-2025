@sparql
Feature: Manage dataset in SPARQL database

  Scenario: Dataset is created in sparql database.
    Given dataset created with params {"id": 998, "slug": "test-rdf"}
    Then sparql store contains subject <http://test.mcod/pl/dataset/998,test-rdf>

  Scenario: Removed dataset is deleted from sparql database.
    Given dataset created with params {"id": 998, "slug": "test-rdf"}
    And remove dataset with id 998
    Then sparql store does not contain subject <http://test.mcod/pl/dataset/998,test-rdf>

  Scenario: Switching dataset to draft deletes it from sparql database.
    Given dataset created with params {"id": 998, "slug": "test-rdf"}
    Then set status to draft on dataset with id 998
    And sparql store does not contain subject <http://test.mcod/pl/dataset/998,test-rdf>

  Scenario: Restoring dataset creates it in sparql database.
    Given dataset created with params {"id": 998, "slug": "test-rdf", "status": "draft"}
    Then sparql store does not contain subject <http://test.mcod/pl/dataset/998,test-rdf>
    And set status to published on dataset with id 998
    And sparql store contains subject <http://test.mcod/pl/dataset/998,test-rdf>

  Scenario: Deleting dataset removes also all related resources from sparql database
    Given dataset with id 998
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 998}
    Then sparql store contains subject <http://test.mcod/pl/dataset/998/resource/999>
    And remove dataset with id 998
    And sparql store does not contain subject <http://test.mcod/pl/dataset/998/resource/999>

  Scenario: Related distribution regions with geonames ids are assigned to dataset
    Given dataset created with params {"id": 998, "slug": "test-rdf"}
    And resource with id 999 dataset id 998 and single main region
    Then sparql store contains object <http://sws.geonames.org/756135/>

  Scenario: Related distribution regions without geonames ids are assigned to dataset as centroids
    Given dataset created with params {"id": 998, "slug": "test-rdf"}
    And resource with id 999 dataset id 998 and single main region
    Then sparql store contains predicate <http://www.w3.org/ns/dcat#centroid>
