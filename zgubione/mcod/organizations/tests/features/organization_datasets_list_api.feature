@elasticsearch
Feature: Organization datasets list API
  Scenario: Test organization datasets number on list is valid
    Given institution with id 999 and 3 datasets and 2 removed datasets
    When api request path is /1.4/institutions/999/datasets
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 3

  Scenario: Test organization datasets on list contain valid links to related items
    Given institution with id 999 and 3 datasets and 2 removed datasets
    When api request path is /1.4/institutions/999/datasets
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response datasets contain valid links to related resources
