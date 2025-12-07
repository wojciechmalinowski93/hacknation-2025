Feature: Resend activation email
  Scenario: Resend is ok
    Given pending user with email InactiveTestUser@dane.gov.pl and password pASSWORD!
    And list of sent emails is empty
    When api request method is POST
    And api request path is /1.0/auth/registration/resend-email
    And api request posted data is {"data": {"type": "user", "attributes": {"email": "InactiveTestUser@dane.gov.pl"}}}
    And send api request and fetch the response
    Then api's response body field data/attributes/is_activation_email_sent is True
    And sent email recipient is InactiveTestUser@dane.gov.pl
    And valid confirmation link for InactiveTestUser@dane.gov.pl in mail content

  Scenario: Resend for wrong email
    Given pending user with email InactiveTestUser@dane.gov.pl and password pASSWORD!
    And list of sent emails is empty
    When api request method is POST
    And api request path is /1.0/auth/registration/resend-email
    And api request posted data is {"data": {"type": "user", "attributes": {"email": "this_is_so_wrong"}}}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/data/attributes/email is ['Nieważny adres email.']

  Scenario: Resend for non existing email
    Given pending user with email InactiveTestUser@dane.gov.pl and password pASSWORD!
    And list of sent emails is empty
    When api request method is POST
    And api request path is /1.0/auth/registration/resend-email
    And api request posted data is {"data": {"type": "user", "attributes": {"email": "not_existing_email@example.com"}}}
    And send api request and fetch the response
    Then api's response status code is 404
    And api's response body field code contains account_not_found
    And api's response body field description contains Nie znaleziono konta
    And api's response body field title contains 404 Not Found

  Scenario: Resend with send_mail exception raised
    Given pending user with email InactiveTestUser@dane.gov.pl and password pASSWORD!
    And list of sent emails is empty
    When api request method is POST
    And api request path is /1.0/auth/registration/resend-email
    And api request posted data is {"data": {"type": "user", "attributes": {"email": "InactiveTestUser@dane.gov.pl"}}}
    And send_mail will raise SMTPException
    And send api request and fetch the response
    Then api's response status code is 500

  Scenario: Resend in API 1.4
    Given pending user with email InactiveTestUser@dane.gov.pl and password pASSWORD!
    And list of sent emails is empty
    When api request method is POST
    And api request path is /1.4/auth/registration/resend-email
    And api request posted data is {"data": {"type": "user", "attributes": {"email": "InactiveTestUser@dane.gov.pl"}}}
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/attributes/is_activation_email_sent is True
    And sent email recipient is InactiveTestUser@dane.gov.pl
    And valid confirmation link for InactiveTestUser@dane.gov.pl in mail content

  Scenario: Resend for non existing email in API 1.4
    Given pending user with email InactiveTestUser@dane.gov.pl and password pASSWORD!
    And list of sent emails is empty
    When api request method is POST
    And api request path is /1.4/auth/registration/resend-email
    And api request posted data is {"data": {"type": "user", "attributes": {"email": "not_existing_email@example.com"}}}
    And send api request and fetch the response
    Then api's response status code is 404
    And api's response body field errors/[0]/code contains 404_not_found
    And api's response body field errors/[0]/detail is Nie znaleziono konta
    And api's response body field errors/[0]/status is 404 Not Found
    And api's response body field errors/[0]/title is 404 Not Found
