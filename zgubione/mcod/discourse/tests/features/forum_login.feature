Feature: Forum login

  Scenario: User with access data can log in to forum
    Given admin with forum access and data {"email": "activeAdmin@dane.gov.pl", "password": "12345.Abcde"}
    When forum request posted data is {"username": "activeAdmin@dane.gov.pl", "password": "12345.Abcde"}
    And User is logging in to forum
    Then user is redirected to external forum url with sso login

  Scenario: User without access data cannot log in to forum
    Given admin without forum access and data {"email": "noAccesAdmin@dane.gov.pl", "password": "12345.Abcde"}
    When forum request posted data is {"username": "noAccesAdmin@dane.gov.pl", "password": "12345.Abcde"}
    And User is logging in to forum
    Then login form error about no access is displayed

  Scenario: Inactive user cannot log in to forum
    Given inactive forum admin with data {"email": "inactiveAdmin@dane.gov.pl", "password": "12345.Abcde"}
    When forum request posted data is {"username": "inactiveAdmin@dane.gov.pl", "password": "12345.Abcde"}
    And User is logging in to forum
    Then login form error about inactive account is displayed

  Scenario Outline: User with invalid status cannot log in to forum
    Given forum admin with status <user_status>
    When forum request posted data is {"username": "activeAdmin@dane.gov.pl", "password": "12345.Abcde"}
    And User is logging in to forum
    Then login form error <status_error> is displayed

    Examples:
    | user_status | status_error                                                       |
    | pending     | Musisz najpierw potwierdzić swój adres email.                      |
    | blocked     | Ten użytkownik jest zablokowany, skontaktuj się z administracją.   |
