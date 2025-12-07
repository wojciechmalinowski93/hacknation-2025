@elasticsearch
Feature: Courses list API
  Scenario Outline: Test courses list endpoint is not accessible for active user
    Given course with id 999
    And logged active user
    When api request language is <lang_code>
    And api request path is /courses
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | resp_body_field   | resp_body_value                      |
    | en        | errors/[0]/detail | Additional permissions are required! |
    # | pl        | errors/[0]/detail | Wymagane są dodatkowe uprawnienia!   |

  Scenario Outline: Test courses list endpoint is accessible by academy admin
    Given logged <user_type>
    When api request path is /courses
    Then send api request and fetch the response
    And api's response status code is 200

    Examples:
    | user_type        |
    | academy admin    |
    | admin user       |
    | editor user      |
    | laboratory admin |
    | official user    |
    | agent user       |

  Scenario: Test courses list endpoint returns required data
    Given course created with params {"id": 999, "title": "Course with id: 999"}
    And logged official user
    When api request language is en
    And api request path is /courses?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes has fields title,notes,venue,start,end,participants_number,sessions,file_type,file_url,materials_file_type,materials_file_url

  Scenario: Test courses list endpoint returns error if invalid state parameter is used
    Given finished course with id 999
    And planned course with id 998
    And current course with id 997
    And logged official user
    When api request language is pl
    And api request path is /courses
    And api request param state is invalid
    Then send api request and fetch the response
    And api's response status code is 422
    And api's response body field errors/[0]/detail is Niepoprawny wybór! Poprawne są: ['current', 'finished', 'planned'].

  Scenario Outline: Test courses list endpoint can be filtered by state
    Given finished course with id 999
    And planned course with id 998
    And current course with id 997
    And logged official user
    When api request language is pl
    And api request path is /courses
    And api request param <req_param_name> is <req_param_value>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | req_param_name | req_param_value | resp_body_field            | resp_body_value |
    | state          | planned         | /data/[0]/attributes/state | planned         |
    | state          | finished        | /data/[0]/attributes/state | finished        |
    | state          | current         | /data/[0]/attributes/state | current         |

  Scenario Outline: Test courses list endpoint can be filtered by list of states
    Given finished course with id 999
    And planned course with id 998
    And current course with id 997
    And logged official user
    When api request language is pl
    And api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200

    Examples:
    | request_path                                   |
    | /courses?state=current,finished,planned        |
    | /courses?state[terms]=finished,current,planned |

  Scenario: Test courses list endpoint returns required data with proper file url
    Given course with id 999
    And logged official user
    When api request language is en
    And api request path is /courses?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/file_url startswith http://test.mcod/media/
