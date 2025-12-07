Feature: Registration

  Scenario Outline: Registration is ok
    When api request method is POST
    And api request path is <request_path>
    And api request posted data is <req_post_data>
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body has field data/id
    And api's response body has field data/attributes
    And api's response body field data/attributes/state is pending
    And api's response body field data/attributes has fields email,state
    And api's response body field data/attributes has no fields password1,password2,phone,phone_internal

    Examples:
    | request_path           | req_post_data                                                                                                                 |
#    | /1.0/auth/registration | {"email": "tester@mc.gov.pl", "password1": "123!A!b!c!", "password2": "123!A!b!c!"}                                           |
    | /1.4/auth/registration | {"data": {"type": "user", "attributes": {"email": "tester@mc.gov.pl", "password1": "123!A!b!c!", "password2": "123!A!b!c!"}}} |

  Scenario Outline: Registration with fullname is ok
    Given list of sent emails is empty
    When api request method is POST
    And api request path is <request_path>
    And api request posted data is <req_post_data>
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body has field data/id
    And api's response body has field data/attributes
    And api's response body field data/attributes/state is pending
    And api's response body field data/attributes/fullname is Test User 2
    And api's response body field data/attributes has fields email,state
    And api's response body field data/attributes has no fields password1,password2,phone,phone_internal
    And sent email recipient is tester2@mc.gov.pl
    And valid confirmation link for tester2@mc.gov.pl in mail content
    And sent email contains Link jest ważny przez 72 godziny.

    Examples:
    | request_path           | req_post_data                                                                                                                                             |
#    | /1.0/auth/registration | {"email": "tester2@mc.gov.pl", "fullname": "Test User 2", "password1": "123!A!b!c!", "password2": "123!A!b!c!"}                                           |
    | /1.4/auth/registration | {"data": {"type": "user", "attributes": {"email": "tester2@mc.gov.pl", "fullname": "Test User 2", "password1": "123!A!b!c!", "password2": "123!A!b!c!"}}} |

  Scenario Outline: Registration without required fields
    When api request method is POST
    And api request language is <lang_code>
    And api request path is <request_path>
    And api request posted data is {"data": {"type": "user", "attributes": {"fullname": "Test User"}}}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | request_path           | resp_body_field              | resp_body_value                  |
    | pl        | /1.0/auth/registration | errors/data/attributes/email | Brak danych w wymaganym polu.    |
    | en        | /1.0/auth/registration | errors/data/attributes/email | Missing data for required field. |
    | pl        | /1.4/auth/registration | errors/[0]/detail            | Brak danych w wymaganym polu.    |
    | en        | /1.4/auth/registration | errors/[0]/detail            | Missing data for required field. |

  Scenario: Registration with invalid email
    When api request method is POST
    And api request path is /1.0/auth/registration
    And api request register data has {"email": "not_valid@email", "password1": "123!a!b!c!", "password2": "123!a!b!c!"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field code is entity_error
    And api's response body field errors/data/attributes/email is ['Nieważny adres email.']

  Scenario: Registration with too short password
    When api request method is POST
    And api request path is /1.0/auth/registration
    And api request register data has {"email": "test@mc.gov.pl", "password1": "123.aBc", "password2": "123.aBc"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field code is entity_error
    And api's response body field errors/data/attributes/password1 is ['To hasło jest za krótkie. Musi zawierać co najmniej %(min_length)d znaków.']

  Scenario: Registration with different new passwords
    When api request method is POST
    And api request path is /1.0/auth/registration
    And api request register data has {"email": "test@mc.gov.pl", "password1": "12.34a.bCd!", "password2": "12.34a.bCd!!"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field code is entity_error
    And api's response body field errors/data/attributes/password1 is ['Hasła nie pasują']

  Scenario: Registration account already exists
    Given active user with email tester@mc.gov.pl and password 123!a!B!c!
    When api request method is POST
    And api request path is /1.0/auth/registration
    And api request register data has {"email": "tester@mc.gov.pl", "password1": "123!a!B!c!", "password2": "123!a!B!c!"}
    And send api request and fetch the response
    Then api's response status code is 403

  Scenario: Registration cannot change user state
    When api request method is POST
    And api request path is /1.0/auth/registration
    And api request register data has {"email": "tester@mc.gov.pl", "password1": "123!a!B!c!", "password2": "123!a!B!c!", "state": "active"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/data/attributes/state is ['Unknown field.']

  Scenario Outline: Cannot register same user twice with different case of letter
    Given active user with email tester@mc.gov.pl and password 123!a!B!c!
    When api request method is POST
    And api request path is <request_path>
    And api request register data has {"email": "TESTER@MC.GOV.PL", "password1": "123!a!B!c!", "password2": "123!a!B!c!"}
    And send api request and fetch the response
    Then api's response status code is 403

    Examples:
    | request_path           |
    | /1.0/auth/registration |
    | /1.4/auth/registration |

  Scenario Outline: Registration with too weak password used returns error
    When api request method is POST
    And api request path is /1.4/auth/registration
    And api request <object_type> data has <req_data>
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/password1
    Examples:
    | object_type | req_data                                                                                    |
    | register    | {"email": "test@mc.gov.pl", "password1": "abcd1234", "password2": "abcd1234"}               |
    | register    | {"email": "test@mc.gov.pl", "password1": "abcdefghi", "password2": "abcdefghi"}             |
    | register    | {"email": "test@mc.gov.pl", "password1": "123456789", "password2": "123456789"}             |
    | register    | {"email": "test@mc.gov.pl", "password1": "alpha101", "password2": "alpha101"}               |
    | register    | {"email": "test@mc.gov.pl", "password1": "92541001101", "password2": "92541001101"}         |
    | register    | {"email": "test@mc.gov.pl", "password1": "9dragons", "password2": "9dragons"}               |
    | register    | {"email": "test@mc.gov.pl", "password1": "@@@@@@@@", "password2": "@@@@@@@@"}               |
    | register    | {"email": "test@mc.gov.pl", "password1": ".........", "password2": "........."}             |
    | register    | {"email": "test@mc.gov.pl", "password1": "!!!!!!!!!!!", "password2": "!!!!!!!!!!!"}         |
    | register    | {"email": "test@mc.gov.pl", "password1": "12@@@@@@@", "password2": "12@@@@@@@"}             |
    | register    | {"email": "test@mc.gov.pl", "password1": "!!@#$$@ab@@", "password2": "!!@#$$@ab@@"}         |
    | register    | {"email": "test@mc.gov.pl", "password1": "admin@mc.gov.pl", "password2": "admin@mc.gov.pl"} |
    | register    | {"email": "test@mc.gov.pl", "password1": "1vdsA532A66", "password2": "1vdsA532A66"}         |
