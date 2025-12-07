Feature: Schedule agents API
  Scenario Outline: Schedule agent details endpoint is not accessible for active user
    Given logged active user
    And logged out agent user created with {"id": 999}
    When api request language is <lang_code>
    And api request path is /auth/schedule_agents/999
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | resp_body_field   | resp_body_value                      |
    | en        | errors/[0]/detail | Additional permissions are required! |
    | pl        | errors/[0]/detail | Wymagane są dodatkowe uprawnienia!   |

  Scenario Outline: Schedule agent details endpoint is not accessible for agent
    Given logged out agent user created with {"id": 999, "email": "agent1@dane.gov.pl"}
    And logged agent user
    When api request language is <lang_code>
    And api request path is /auth/schedule_agents/999
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | resp_body_field   | resp_body_value                      |
    | en        | errors/[0]/detail | Additional permissions are required! |
    | pl        | errors/[0]/detail | Wymagane są dodatkowe uprawnienia!   |

  Scenario: Schedule agent details endpoint returns 404 for invalid agent id
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "planned"}
    And logged admin user
    When api request path is /auth/schedule_agents/9999
    Then send api request and fetch the response
    And api's response status code is 404

  Scenario: Schedule agent details endpoint is accessible for admin
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "planned"}
    And logged admin user
    When api request path is /auth/schedule_agents/999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has field data/attributes/planned_user_schedule/institution
    And api's response body has field data/attributes/planned_user_schedule/items_count
    And api's response body has field data/attributes/planned_user_schedule/recommended_items_count
    And api's response body has field data/attributes/planned_user_schedule/implemented_items_count
    And api's response body has field data/attributes/planned_user_schedule/is_ready
    And api's response body has field data/attributes/planned_user_schedule/state

  Scenario: Admin is able to create user schedule item for specified agent
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "planned"}
    And logged admin user
    When api request method is POST
    And api request path is /auth/schedule_agents/999
    And api request user_schedule_item data has {"is_new": true}
    Then send api request and fetch the response
    And api's response status code is 201
    And api's response body field data/type is user_schedule_item
    And api's response body field data/attributes/state is planned

  Scenario: Active user cannot create user schedule item for specified agent
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "planned"}
    And logged active user
    When api request method is POST
    And api request path is /auth/schedule_agents/999
    And api request user_schedule_item data has {"is_new": true}
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field errors/[0]/detail is Wymagane są dodatkowe uprawnienia!

  Scenario: Admin cannot create user schedule item for specified agent if planned schedule is not found
    Given logged out agent user created with {"id": 999}
    And logged admin user
    When api request method is POST
    And api request path is /auth/schedule_agents/999
    And api request user_schedule_item data has {"is_new": true}
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field errors/[0]/title is There is no currently planned schedule yet!

  Scenario: Create user schedule item for specified agent request returns 404 for invalid agent id
    Given logged out agent user created with {"id": 999}
    And logged admin user
    When api request method is POST
    And api request path is /auth/schedule_agents/9999
    And api request user_schedule_item data has {"is_new": true}
    Then send api request and fetch the response
    And api's response status code is 404
