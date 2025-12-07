@elasticsearch
Feature: Meetings list API
  Scenario Outline: Test meetings list endpoint is not accessible for active user
    Given logged active user
    When api request language is <lang_code>
    And api request path is /meetings
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | resp_body_field   | resp_body_value                      |
    | en        | errors/[0]/detail | Additional permissions are required! |
    # | pl        | errors/[0]/detail | Wymagane są dodatkowe uprawnienia!   |

  Scenario: Test meetings list endpoint is accessible by superuser
    Given logged admin user
    When api request path is /meetings
    Then send api request and fetch the response
    And api's response status code is 200

  Scenario: Test courses list endpoint is accessible by agent user
    Given logged agent user
    When api request path is /meetings
    Then send api request and fetch the response
    And api's response status code is 200

  Scenario: Test courses list endpoint returns required data
    Given course with id 999
    And logged official user
    When api request language is en
    And api request path is /courses?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes has fields title,notes,venue,start,end,participants_number,sessions,file_type,file_url,materials_file_type,materials_file_url

  Scenario: Test meetings list endpoint returns error if invalid state parameter is used
    Given logged agent user
    When api request language is pl
    And api request path is /meetings
    And api request param state is invalid
    Then send api request and fetch the response
    And api's response status code is 422
    And api's response body field errors/[0]/detail is Niepoprawny wybór! Poprawne są: ['finished', 'planned'].

  Scenario Outline: Test meetings list endpoint can be filtered by list of states
    Given logged admin user
    When api request language is pl
    And api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200

    Examples:
    | request_path                            |
    | /meetings?state=finished,planned        |
    | /meetings?state[terms]=finished,planned |

  Scenario: Two different meeting files can have the same file names
    Given logged admin user
    And meeting with id 999 and 2 files
    When api request path is /meetings
    Then send api request and fetch the response
    And api's response body field data/[0]/attributes/materials/[0]/name is meeting_file.txt
    And api's response body field data/[0]/attributes/materials/[1]/name is meeting_file.txt
