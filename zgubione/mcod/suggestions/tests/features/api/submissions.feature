@elasticsearch
Feature: Submissions

  Scenario: Post submission
    Given logged editor user
    When api request method is POST
    And api request path is /submissions/
    And api request posted data is {"data": {"type": "submission", "attributes": {"title": "test", "notes": "notes"}}}
    Then send api request and fetch the response
    And api's response status code is 201

  Scenario: Post submission without notes
    Given logged active user
    When api request method is POST
    And api request path is /submissions/
    And api request posted data is {"data": {"type": "submission", "attributes": {"title": "test"}}}
    Then send api request and fetch the response
    And api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/notes
    And api's response body field errors/[0]/detail is Brak danych w wymaganym polu.

  Scenario Outline: Accepted dataset submission feedback endpoint is not accessible for some user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request method is POST
    And api request path is /submissions/accepted/999/feedback
    Then send api request and fetch the response
    And api's response status code is 403

    Examples:
    | user_type     |
    | active user   |
    | official user |

  Scenario Outline: Accepted dataset submission feedback endpoint is accessible for some user types
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych", "is_active": "True"}
    When api request method is POST
    And api request posted data is {"data": {"type": "feedback", "attributes": {"opinion": "plus"}}}
    And api request path is /submissions/accepted/999/feedback
    Then send api request and fetch the response
    And api's response status code is 201
    And api's response body has field data/attributes/published_at

    Examples:
    | user_type   |
    | editor user |
    | admin user  |
    | agent user  |

  Scenario: Accepted dataset submission feedback with invalid opinion
    Given logged editor user
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request method is POST
    And api request posted data is {"data": {"type": "feedback", "attributes": {"opinion": "invalid"}}}
    And api request path is /submissions/accepted/999/feedback
    Then send api request and fetch the response
    And api's response status code is 400
    And api's response body field errors/[0]/detail is Valid values are 'plus' and 'minus'

  Scenario Outline: Accepted dataset submission feedback delete endpoint if no feedback yet
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych"}
    When api request method is DELETE
    And api request path is /submissions/accepted/999/feedback
    Then send api request and fetch the response
    And api's response status code is 404

    Examples:
    | user_type   |
    | editor user |
    | admin user  |
    | agent user  |

  Scenario Outline: Submission comment
    Given logged <user_type>
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych", "is_published_for_all": true}
    When api request method is POST
    And api request posted data is {"data": {"type": "feedback", "attributes": {"comment": "Test submission comment"}}}
    And api request path is /submissions/accepted/public/999/comment
    Then send api request and fetch the response
    And api's response status code is 201
    And api's response body field data/attributes/is_comment_email_sent is True

    Examples:
    | user_type   |
    | editor user |
    | admin user  |
    | agent user  |

  Scenario: Submission comment endpoint returns 404 if submission is not public
    Given logged editor user
    And accepteddatasetsubmission created with params {"id": 999, "title": "Testowa zaakceptowana propozycja nowych danych", "is_published_for_all": false}
    When api request method is POST
    And api request posted data is {"data": {"type": "feedback", "attributes": {"comment": "Test submission comment"}}}
    And api request path is /submissions/accepted/public/999/comment
    Then send api request and fetch the response
    And api's response status code is 404
