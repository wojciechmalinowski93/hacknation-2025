@elasticsearch
Feature: Chart details API

  Scenario: Chart creation is not available for anonymous user
    Given resource with id 888
    When api request method is POST
    And api request path is /1.4/resources/999/chart
    And api request param resource_id is 999
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body has no field data

  Scenario: Chart creation is available for logged in user
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is POST
    And api request path is /1.4/resources/999/chart
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body has field data

  Scenario: Chart creation is NOT available for active user if related resource has chart creation blocked
    Given logged active user
    And resource created with params {"id": 999, "is_chart_creation_blocked": true}
    When api request method is POST
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/_schema
    And api's response body field errors/[0]/detail is Tworzenie wykresów dla tego zasobu jest zablokowane!

  Scenario: Active user cannot create second private chart if first one already exists
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    When api request method is POST
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/_schema
    And api's response body field errors/[0]/detail is Dodanie kolejnego wykresu prywatnego jest niemożliwe!

  Scenario: Editor cannot change type of chart
    Given logged editor user
    And logged user is from organization of resource 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is PATCH
    And api request path is /1.4/resources/999/charts/999
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/_schema
    And api's response body field errors/[0]/detail is Zmiana typu wykresu jest niemożliwa!

  Scenario: Chart creation is available for editor even if related resource has chart creation blocked
    Given logged editor user
    And resource created with params {"id": 999, "is_chart_creation_blocked": true}
    When api request method is POST
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/name is test

 Scenario: Creation of public chart is available for editor even if there is private chart already created
    Given logged editor user
    And logged user is from organization of resource 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false}
    When api request method is POST
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/name is test

  Scenario: Chart update is available for logged in user
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is POST
    And api request path is /1.4/resources/999/chart
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/id is not 999

  Scenario: Default chart update is not available for normal user
    Given logged editor user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    And logged active user
    When api request method is POST
    And api request language is pl
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is Brak uprawnień do definiowania wykresu

  Scenario: Update chart endpoint returns error if chart data is empty
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is POST
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": null, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/chart

  Scenario: Update chart endpoint returns error if chart name is not passed
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true}
    When api request method is POST
    And api request path is /1.4/resources/999/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/name

  Scenario: Editor cannot create chart for resource not related to his organization
    Given logged editor user
    And logged user is from organization of resource 1000
    And resource with id 1001
    When api request method is POST
    And api request language is pl
    And api request path is /1.4/resources/1001/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is Brak uprawnień do definiowania wykresu

  Scenario: Editor can create chart for resource which has blocked chart creation
    Given logged editor user
    And logged user is from organization of resource 1000
    And resource created with params {"id": 1001, "is_chart_creation_blocked": true}
    When api request method is POST
    And api request language is pl
    And api request path is /1.4/resources/1000/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/name is test

  Scenario: Editor can create chart for resource related to his organization
    Given logged editor user
    And logged user is from organization of resource 1000
    When api request method is POST
    And api request language is pl
    And api request path is /1.4/resources/1000/charts
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/is_default is True
    And api's response body field data/attributes/chart/x is col1
    And api's response body field data/attributes/chart/y is col2

  Scenario: Editor can update chart for resource related to his organization
    Given logged editor user
    And logged user is from organization of resource 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true, "name": "test"}
    When api request method is PATCH
    And api request language is pl
    And api request path is /1.4/resources/999/charts/999
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 202

  Scenario: Normal user cannot update default chart
    Given editor with id 999 from organization of resource 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": true, "name": "test", "created_by": 999}
    And logged active user
    When api request method is PATCH
    And api request language is pl
    And api request path is /1.4/resources/999/charts/999
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": true, "name": "test"}
    And send api request and fetch the response
    Then api's response status code is 403

  Scenario: Normal user can update his private chart
    Given logged active user
    And resource with id 999
    And chart created with params {"id": 999, "resource_id": 999, "is_default": false, "name": "test"}
    When api request method is PATCH
    And api request language is pl
    And api request path is /1.4/resources/999/charts/999
    And api request chart data has {"chart": {"x": "col1", "y": "col2"}, "is_default": false, "name": "Edited"}
    And send api request and fetch the response
    Then api's response status code is 202
    And api's response body field data/attributes/name is Edited
