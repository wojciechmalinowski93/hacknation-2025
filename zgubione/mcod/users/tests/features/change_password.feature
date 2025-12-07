Feature: Change password

  Scenario Outline: Change password
    Given logged active user with email ActiveTestUser@dane.gov.pl and password 12345.Abcde
    When api request method is POST
    And api request path is <request_path>
    And api request posted data is {"data": {"type": "user", "attributes": {"old_password": "12345.Abcde", "new_password1": "AaCc.5922", "new_password2": "AaCc.5922"}}}
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/is_password_changed is True
    And password AaCc.5922 is valid for user ActiveTestUser@dane.gov.pl
    Examples:
    | request_path              |
    | /1.0/auth/password/change |
    | /1.4/auth/password/change |

  Scenario Outline: Change password by logged out
    Given active user with email ActiveTestUser@dane.gov.pl and password 12345.Abcde
    When api request method is POST
    And api request path is <request_path>
    And api request posted data is <req_post_data>
    And send api request and fetch the response
    Then api's response status code is 401
    And api's response body field <resp_body_field> is <resp_body_value>
    And password 12345.Abcde is valid for user ActiveTestUser@dane.gov.pl

    Examples:
    | request_path              | req_post_data                                                                                                                         | resp_body_field | resp_body_value |
    | /1.0/auth/password/change | {"old_password": "12345.Abcde", "new_password1": "AaCc.5922", "new_password2": "AaCc.5922"}                                           | code            | token_missing   |
    | /1.4/auth/password/change | {"data": {"type": "user", "attributes": {"old_password": "12345.Abcde", "new_password1": "AaCc.5922", "new_password2": "AaCc.5922"}}} | errors/[0]/code | 401_unauthorized |

  Scenario Outline: Change password with errors
    Given logged active user with email ActiveTestUser@dane.gov.pl and password 12345.Abcde
    When api request method is POST
    And api request path is <request_path>
    And api request posted data is <req_post_data>
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | request_path              | req_post_data                                                                                                                          | resp_body_field | resp_body_value          |
    | /1.0/auth/password/change | {"old_password": "AAAA.BBBB12", "new_password1": "AaCc.5922", "new_password2": "AaCc.5922"}                                            | code            | entity_error             |
    | /1.0/auth/password/change | {"old_password": "12345.Abcde", "new_password1": "AaCc.5922", "new_password2": "AaCc.59222"}                                           | code            | entity_error             |
    | /1.0/auth/password/change | {"old_password": "12345.Abcde", "new_password1": "Abcde", "new_password2": "Abcde"}                                                    | code            | entity_error             |

    | /1.4/auth/password/change | {"data": {"type": "user", "attributes": {"old_password": "AAAA.BBBB12", "new_password1": "AaCc.5922", "new_password2": "AaCc.5922"}}}  | errors/[0]/code | 422_unprocessable_entity |
    | /1.4/auth/password/change | {"data": {"type": "user", "attributes": {"old_password": "12345.Abcde", "new_password1": "AaCc.5922", "new_password2": "AaCc.59222"}}} | errors/[0]/code | 422_unprocessable_entity |
    | /1.4/auth/password/change | {"data": {"type": "user", "attributes": {"old_password": "12345.Abcde", "new_password1": "Abcde", "new_password2": "Abcde"}}}          | errors/[0]/code | 422_unprocessable_entity |
