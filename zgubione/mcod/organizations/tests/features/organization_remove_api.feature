@elasticsearch
Feature: Organization remove

  Scenario: /search endpoint shows dataset related to organization
    Given institution with id 1
    And dataset created with params {"id": 999, "title": "FIRST_UNIQUE_TITLE", "organization_id": 1}
    When api request path is /search?q=FIRST_UNIQUE_TITLE
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1

  Scenario: /search endpoint doesn't show dataset related to removed organization
    Given institution with id 1
    And dataset created with params {"id": 999, "title": "UNIQUE_TITLE", "organization_id": 1}
    When admin's request method is POST
    And admin's request posted institution data is {"post":"yes"}
    And admin's page /organizations/organization/1/delete/ is requested
    Then api request method is GET
    And api request path is /search?q=UNIQUE_TITLE
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 0
