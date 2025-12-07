Feature: User Logout

  Scenario: Logout is ok
    # Given session is flushed
    Given logged active user
    When api request method is POST
    And api request path is /1.0/auth/logout
    And send api request and fetch the response
    Then api's response status code is 200

  Scenario: Logout is ok in API 1.4
    Given logged active user
    When api request method is POST
    And api request path is /1.4/auth/logout
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/is_logged_out is True

  Scenario: Logout by not logged in
    When api request method is POST
    And api request path is /1.0/auth/logout
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body field code is token_missing
