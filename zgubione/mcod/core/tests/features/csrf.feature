Feature: CSRF protection

  Scenario: Test cipher salting identity.
    Given a random cipher secret
    When the string has length 32
    And the string is alphanumeric
    Then salting and unsalting the string is mutually opposite

  Scenario: Unsalting a token returns secret.
    Given the salted secret
    When the token is of length 64
    Then unsalting the token results in the original cipher secret
