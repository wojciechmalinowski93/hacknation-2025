@elasticsearch
Feature: Stats API
  Scenario: Test stats API 1.0
    Given institution with id 777 and 2 datasets
    When api request path is /1.0/stats/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggs/datasets_by_openness_scores
    And api's response body has field /meta/aggs/datasets_by_formats
    And api's response body has field /meta/aggs/datasets_by_institution
    And api's response body has field /meta/aggs/datasets_by_category
    And api's response body has field /meta/aggs/documents_by_type

  Scenario: Test stats API 1.4
    Given institution with id 888 and 2 datasets
    When api request path is /1.4/stats/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggs/datasets_by_openness_scores
    And api's response body has field /meta/aggs/datasets_by_formats
    And api's response body has field /meta/aggs/datasets_by_institution
    And api's response body has field /meta/aggs/datasets_by_category
    And api's response body has field /meta/aggs/documents_by_type
    And api's response body has field /meta/aggs/resources_by_type
