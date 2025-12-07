@elasticsearch
Feature: Chart delete API

    Scenario: Delete chart returns status 404 if chart does not exists
    Given logged admin user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/888
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Delete default chart returns status 401 if user is not logged in
    Given resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body has no field data

  Scenario: Delete private chart returns status 401 if user is not logged in
    Given resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body has no field data

  Scenario: Delete chart returns status 403 if user does not have required permissions
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    And logged active user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body has no field data

  Scenario: Delete chart returns 403 if chart is not default and user is not creator of chart
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    And logged active user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body has no field data

  Scenario: Delete chart works properly if chart exists
    Given logged admin user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 204
    And api's response body has no field data

  Scenario: Admin cannot delete someones private chart
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    And logged admin user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

  Scenario: Normal user cannot delete someones private chart
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    And logged active user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

  Scenario: Admin can delete his private chart
    Given logged admin user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 204
    And api's response body has no field data

  Scenario: Normal user can delete his private chart
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 204
    And api's response body has no field data

  Scenario: Admin can delete someones default chart
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    And logged admin user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 204
    And api's response body has no field data

  Scenario: Normal user cannot delete someones default chart
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    And logged active user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

   Scenario: Editor from organization can delete chart
     Given logged editor user
     And logged user is from organization of resource 999
     And resource with id 999
     And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
     When api request method is DELETE
     And api request path is /1.4/resources/charts/999
     And send api request and fetch the response
     Then api's response status code is 204
     And api's response body has no field data

  Scenario: Editor outside of organization cannot delete private chart
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    And logged editor user
    When api request method is DELETE
    And api request path is /1.4/resources/charts/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden
