@elasticsearch
Feature: Charts list API

  Scenario: Chart details endpoint returns status code 404 if resource is not found
    Given logged admin user
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 404
    And api's response body field errors/[0]/detail is The requested resource could not be found

  Scenario: Chart details endpoint returns empty data if chart is not found
    Given logged admin user
    And resource with id 999
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field data
    And api's response body field data is None

  Scenario: Chart details endpoint returns empty data if chart for resource exists but is set as removed
    Given logged admin user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true, "is_removed": true}
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field data
    And api's response body field data is None

  Scenario: Anonymous user gets empty data if there is no default chart
    Given resource with id 999
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data is None

  Scenario: Not authorized user gets empty data if there is no default chart
    Given resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data is None

  Scenario: Chart details endpoint works properly for anonymous user
    Given two charts for resource with {"id": 999}
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/type is chart
    And api's response body field /data/attributes/is_default is True

  Scenario: Authorized user gets own chart even if default is created
    Given logged editor user
    And default charts for resource with id 999 with ids 999
    And private chart for resource with id 999 with id 1000
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/attributes/is_default is False
    And api's response body field /data/id is 1000

  Scenario: Authorized user gets default chart if does not have private
    Given logged editor user
    And default charts for resource with id 999 with ids 999
    When api request path is /1.4/resources/999/chart
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/attributes/is_default is True
    And api's response body field /data/id is 999

  Scenario: Charts list endpoint returns empty list if there is no charts for specified resource
    Given logged editor user
    And resource with id 999
    When api request path is /1.4/resources/999/charts
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data is []

  Scenario: Charts list endpoint returns default chart only if user is not authenticated
    Given two charts for resource with {"id": 999}
    When api request path is /1.4/resources/999/charts
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/[0]/attributes/is_default is True
    And size of api's response body field data is 1

  Scenario: Charts list endpoint returns default and custom charts if the custom is created by the user
    Given logged editor user
    And two charts for resource with {"id": 999}
    When api request path is /1.4/resources/999/charts
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/[0]/attributes/is_default is True
    And api's response body field data/[1]/attributes/is_default is False
    And size of api's response body field data is 2

  Scenario Outline: Charts list endpoint returns only default charts if related resource has chart creation blocked
    Given logged <user_type>
    And two charts for resource with {"id": 999, "is_chart_creation_blocked": true}
    When api request path is /1.4/resources/999/charts
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/[0]/attributes/is_default is True
    And size of api's response body field data is 1
    Examples:
    | user_type   |
    | active user |
    | editor user |

  Scenario: Chart details endpoint is available when chart id is specified
    Given default charts for resource with id 988 with ids 101
    When api request path is /1.4/resources/988/charts/101
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/attributes/is_default is True
    And api's response body field /data/id is 101

  Scenario: Chart details endpoint returns 404 for non existent chart
    Given default charts for resource with id 988 with ids 101
    When api request path is /1.4/resources/988/charts/102
    And send api request and fetch the response
    Then api's response status code is 404
