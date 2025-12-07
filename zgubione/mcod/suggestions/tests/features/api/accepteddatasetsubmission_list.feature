@elasticsearch
Feature: Accepted dataset submission API

  Scenario Outline: Accepted dataset submission list endpoint is accessible by some user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request path is /submissions/accepted
    Then send api request and fetch the response
    And api's response status code is 200

    Examples:
    | user_type   |
    | editor user |
    | admin user  |
    | agent user  |

  Scenario Outline: Accepted dataset submission list endpoint is not accessible for some user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request path is /submissions/accepted
    Then send api request and fetch the response
    And api's response status code is 403

    Examples:
    | user_type     |
    | active user   |
    | official user |

  Scenario Outline: Public accepted dataset submission list endpoint is accessible by all user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych", "is_published_for_all": true}
    When api request path is /submissions/accepted/public
    Then send api request and fetch the response
    And api's response status code is 200

    Examples:
    | user_type     |
    | editor user   |
    | admin user    |
    | agent user    |
    | active user   |
    | official user |

  Scenario Outline: Accepted dataset submission details endpoint is not accessible for some user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request path is /submissions/accepted/999
    Then send api request and fetch the response
    And api's response status code is 403

    Examples:
    | user_type     |
    | active user   |
    | official user |

  Scenario Outline: Accepted dataset submission details endpoint is accessible by some user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request path is /submissions/accepted/999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/attributes/title is Testowa zaakceptowana propozycja nowych danych

    Examples:
    | user_type     |
    | editor user   |
    | admin user    |
    | agent user    |
