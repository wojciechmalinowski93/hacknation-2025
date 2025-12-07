@elasticsearch
Feature: CMS API endpoints

  Scenario: Check every CMS API's endpoint response for valid status_code
    Given cms structure from file cms.json is loaded
    When every CMS API endpoint is requested
    Then every CMS API response status code is 200
    And CMS live page count is 20
