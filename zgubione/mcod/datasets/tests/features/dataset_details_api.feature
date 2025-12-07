Feature: Datasets details API

  Scenario: Test dataset formats attribute contains format of related published resource
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "format": "csv"}
    When api request path is /datasets/999
    Then send api request and fetch the response
    And api's response body field data/attributes has items {"formats": ["csv"]}

  Scenario: Test dataset formats attribute doesnt contains format of related draft resource
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "format": "csv", "status": "draft"}
    When api request path is /datasets/999
    Then send api request and fetch the response
    And api's response body field data/attributes has items {"formats": []}

  Scenario: Dataset has assigned related resources regions
    Given dataset with id 999 and 2 resources
    And resource with id 995 dataset id 999 and single main region
    When api request path is /datasets/999
    Then send api request and fetch the response
    And api's response body field data/attributes/regions/1/name is Warszawa
    And api's response body field data/attributes/regions/1/region_id is 101752777
    And api's response body field data/attributes/regions/1/is_additional is False
    And api's response body field data/attributes/regions/0/name is Polska
    And api's response body field data/attributes/regions/0/is_additional is False
    And size of api's response body field data/attributes/regions is 5

  Scenario: Dataset with resources without regions has assigned poland as main region
    Given dataset with id 999 and 2 resources
    When api request path is /datasets/999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/attributes/regions/0/name is Polska
    And api's response body field data/attributes/regions/0/is_additional is False
