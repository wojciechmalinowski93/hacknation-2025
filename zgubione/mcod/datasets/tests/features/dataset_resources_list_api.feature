@elasticsearch
Feature: Dataset resources list API
  Scenario Outline: Test dataset resources list is sorted by views_count ascendingly
    Given dataset with id 999 and 3 resources
    When api request path is <request_path>
    Then api request param sort is views_count
    And send api request and fetch the response
    And api's response status code is 200
    And api's response list is sorted by views_count ascendingly
    Examples:
    | request_path                |
    | /1.0/datasets/999/resources |
    | /1.4/datasets/999/resources |

  Scenario Outline: Test dataset resources list is sorted by views_count descendingly
    Given dataset with id 999 and 3 resources
    When api request path is <request_path>
    Then api request param sort is -views_count
    And send api request and fetch the response
    And api's response status code is 200
    And api's response list is sorted by views_count descendingly
    Examples:
    | request_path                |
    | /1.0/datasets/999/resources |
    | /1.4/datasets/999/resources |

  Scenario: Related resource's region is returned by ES api
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    When api request path is /1.4/datasets/998/resources
    And send api request and fetch the response
    Then has assigned Polska,Warszawa as name for regions
    And has assigned 85633723,101752777 as region_id for regions
