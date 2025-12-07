@elasticsearch
Feature: Search history list API

  Scenario: Test search history list for unauthorized user
    Given 5 search histories for admin
    When api request path is /searchhistories/
    Then send api request and fetch the response
    And api's response status code is 401

  Scenario: Test search history list of admin is empty for another user
    Given 5 search histories for admin
    And logged active user
    When api request path is /searchhistories/
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 0

  Scenario: Test search history list for authorized user with histories
    Given 5 search histories for admin
    And logged admin user
    When api request path is /searchhistories/
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 5

  Scenario Outline: Test search history list can be sorted
    Given 5 search histories for admin
    And logged admin user
    When api request language is pl
    And api request path is <request_path>
    And api request param per_page is 100
    And api request param <req_param_name> is <req_param_value>
    Then send api request and fetch the response
    And search history list in response is sorted by <sort>

    Examples:
    | request_path         | req_param_name | req_param_value | sort                    |
    | /1.0/searchhistories | sort           | id              | id                      |
    | /1.0/searchhistories | sort           | -id             | -id                     |
    | /1.0/searchhistories | sort           | query_sentence  | query_sentence_keyword  |
    | /1.0/searchhistories | sort           | -query_sentence | -query_sentence_keyword |
    | /1.0/searchhistories | sort           | modified        | modified                |
    | /1.0/searchhistories | sort           | -modified       | -modified               |
    | /1.0/searchhistories | sort           | user            | user.id                 |
    | /1.0/searchhistories | sort           | -user           | -user.id                |

    | /1.4/searchhistories | sort           | id              | id                      |
    | /1.4/searchhistories | sort           | -id             | -id                     |
    | /1.4/searchhistories | sort           | query_sentence  | query_sentence_keyword  |
    | /1.4/searchhistories | sort           | -query_sentence | -query_sentence_keyword |
    | /1.4/searchhistories | sort           | modified        | modified                |
    | /1.4/searchhistories | sort           | -modified       | -modified               |
    | /1.4/searchhistories | sort           | user            | user.id                 |
    | /1.4/searchhistories | sort           | -user           | -user.id                |
