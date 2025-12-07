@elasticsearch
Feature: CSRF in Dataset Comments API

  Scenario: Test posting dataset comment endpoint if CSRF is not valid
    Given dataset with id 1000
    When api request path is /1.4/datasets/1000/comments
    And api request mcod_csrf_token is invalid
    And api request method is POST
    And api request posted data is {"data": {"type": "comment", "attributes": {"comment": "Test comment"}}}
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field /errors/[0]/title is CSRF error
    And api's response body field /errors/[0]/detail is Token CSRF nie został poprawnie wprowadzony.
    And api's response body field /errors/[0]/status is Forbidden
    And api's response body field /errors/[0]/code is 403 Forbidden

  Scenario: Test posting dataset comment endpoint if CSRF is valid
    Given dataset with id 1000
    When api request path is /1.4/datasets/1000/comments
    And api request mcod_csrf_token is valid
    And api request method is POST
    And api request posted data is {"data": {"type": "comment", "attributes": {"comment": "Test comment"}}}
    Then send api request and fetch the response
    And api's response status code is 201
