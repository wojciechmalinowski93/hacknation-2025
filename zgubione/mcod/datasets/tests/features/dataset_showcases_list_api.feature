@elasticsearch
Feature: Dataset showcases list API
  Scenario Outline: Test dataset showcases list is sorted by title ascendingly
    Given dataset with id 999 and 3 showcases
    When api request path is <request_path>
    Then api request param sort is title
    And send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 3
    And api's response list is sorted by title ascendingly
    Examples:
    | request_path                |
    | /1.0/datasets/999/showcases |
    | /1.4/datasets/999/showcases |

  Scenario Outline: Test dataset resources list is sorted by title descendingly
    Given dataset with id 999 and 3 showcases
    When api request path is <request_path>
    Then api request param sort is -title
    And send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 3
    And api's response list is sorted by title descendingly
    Examples:
    | request_path                |
    | /1.0/datasets/999/showcases |
    | /1.4/datasets/999/showcases |
