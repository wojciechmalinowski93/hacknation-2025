@elasticsearch
Feature: LabEvents list API
  Scenario Outline: Test lab events list endpoint is not accessible for unlogged
    Given LabEvent id 999
    When api request language is <lang_code>
    And api request path is /laboratory
    Then send api request and fetch the response
    And api's response status code is 401
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | resp_body_field   | resp_body_value              |
    | en        | errors/[0]/detail | Missing authorization header |
    | pl        | errors/[0]/detail | Brak Nagłówka Autoryzacji    |

  Scenario: Test lab events list endpoint is accessible by official user
    Given logged official user
    When api request path is /laboratory
    Then send api request and fetch the response
    And api's response status code is 200

  Scenario: Test lab_events list endpoint is accessible by admin (superuser)
    Given logged admin user
    When api request path is /laboratory
    Then send api request and fetch the response
    And api's response status code is 200

  Scenario: Test lab_events list endpoint returns required data
    Given LabEvent id 999
    And logged official user
    When api request language is en
    And api request path is /laboratory?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes has fields title,notes,event_type,reports,execution_date

  Scenario Outline: Test lab_events list endpoint can be filtered by event_type
    Given Laboratory analysis 998
    And logged official user
    And Laboratory research 999
    When api request language is pl
    And api request path is /laboratory
    And api request param <req_param_name> is <req_param_value>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | req_param_name      | req_param_value | resp_body_field                 | resp_body_value |
    | event_type          | analysis        | /data/[0]/attributes/event_type | analysis        |
    | event_type          | research        | /data/[0]/attributes/event_type | research        |
