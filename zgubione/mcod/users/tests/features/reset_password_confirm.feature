Feature: Reset password confirm

  Scenario Outline: Reset password confirm with invalid token
    Given active user with email ActiveTestUser@dane.gov.pl and password pASSWORD!
    When api request method is POST
    And api request path is <request_path>
    And api request posted data is {"data": {"type": "user", "attributes": {"new_password1": "123.4.bcE", "new_password2": "123.4.bcE"}}}
    And send api request and fetch the response
    Then api's response status code is 404

    Examples:
    | request_path                                                  |
    | /1.0/auth/password/reset/abcdedfg                             |
    | /1.4/auth/password/reset/abcdedfg                             |
    | /1.0/auth/password/reset/8c37fd0c-5600-4277-a13a-67ced4a61e66 |
    | /1.4/auth/password/reset/8c37fd0c-5600-4277-a13a-67ced4a61e66 |
