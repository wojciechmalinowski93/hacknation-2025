Feature: Schedule details API
  Scenario: Schedule details endpoint for admin
    Given logged admin user
    And schedule with id 999
    When api request path is /auth/schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/type is schedule
    And api's response body field data/attributes has fields period_name,start_date,end_date,new_end_date,link,state,is_blocked,name,total_agents_count
    And api's response body field data/relationships has fields user_schedules,user_schedule_items,agents

  Scenario: Schedule details endpoint for agent
    Given logged agent user
    And schedule with id 999
    When api request path is /auth/schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/type is schedule
    And api's response body field data/attributes has fields period_name,start_date,end_date,new_end_date,link,state,is_blocked,name,total_agents_count
    And api's response body field data/relationships has fields user_schedules,user_schedule_items
    And api's response body field data/relationships has no fields agents

  Scenario: Current schedule details endpoint returns 404 if no planned schedule yet
    Given logged admin user
    When api request path is /auth/schedules/current
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Schedule details endpoint is not available for active user
    Given logged active user
    And schedule with id 999
    When api request language is pl
    And api request path is /auth/schedules/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/detail is Wymagane są dodatkowe uprawnienia!

  Scenario: Schedule can be updated by admin
    Given logged admin user
    And schedule data created with {"schedule_id": 999}
    When api request method is PATCH
    And api request schedule data has {"end_date": "2021-06-01"}
    And api request path is /auth/schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/id is 999
    And api's response body field data/attributes/end_date is 2021-06-01

  Scenario: Schedule cannot be updated by agent
    Given logged agent user created with {"id": 999}
    And schedule with id 999
    When api request method is PATCH
    And api request schedule data has {}
    And api request path is /auth/schedules/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

  Scenario: Schedule cannot be updated by active user
    Given logged active user
    And schedule with id 999
    When api request method is PATCH
    And api request schedule data has {}
    And api request path is /auth/schedules/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

  Scenario: Update schedule request returns 404 for invalid schedule id
    Given logged admin user
    And schedule with id 999
    When api request method is PATCH
    And api request schedule data has {}
    And api request path is /auth/schedules/9999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Update current schedule request returns 404 if no currently planned schedule yet
    Given logged admin user
    When api request method is PATCH
    And api request schedule data has {}
    And api request path is /auth/schedules/current
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Passing end_date in schedule update request is optional
    Given logged admin user
    And schedule data created with {"schedule_id": 999}
    When api request method is PATCH
    And api request schedule data has {"end_date": null}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/end_date is None

  Scenario: Admin can pass custom period name in request
    Given logged admin user
    And schedule data created with {"schedule_id": 999}
    When api request method is PATCH
    And api request schedule data has {"period_name": "Testowa nazwa okresu"}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/period_name is Testowa nazwa okresu

  Scenario: Passing of link to schedule update request is optional
    Given logged admin user
    And schedule data created with {"schedule_id": 999}
    When api request method is PATCH
    And api request schedule data has {"link": ""}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes has items {"link": ""}

  Scenario: Schedule update requires that link passed in request should be valid url
    Given logged admin user
    And schedule data created with {"schedule_id": 999}
    When api request method is PATCH
    And api request schedule data has {"link": "INVALID"}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/link
    And api's response body field errors/[0]/detail is Niepoprawny adres URL.

  Scenario: Update new_end_date of schedule requires end_data attribute already set
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "end_date": null}
    When api request method is PATCH
    And api request schedule data has {"new_end_date": "2021-01-01"}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/new_end_date
    And api's response body field errors/[0]/detail is Nie można ustawić nowej daty zakończenia przed ustawieniem daty zakończenia!

  Scenario: Admin can set implemented schedule as archival
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented"}
    When api request method is PATCH
    And api request schedule_state data has {"state": "archived"}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/state is archived

  Scenario: Admin cannot set planned schedule as archival
    Given logged admin user
    And schedule data created with {"schedule_id": 999}
    When api request method is PATCH
    And api request schedule_state data has {"state": "archived"}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/*/source/pointer contains /data/attributes/state
    And api's response body field errors/*/detail contains Unknown field.

  Scenario Outline: Implemented schedule passing archived state is the only option
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented"}
    When api request method is PATCH
    And api request <object_type> data has <req_data>
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/state
    And api's response body field errors/[0]/detail is Niepoprawna wartość! Możliwe wartości: archived

    Examples:
    | object_type    | req_data                 |
    | schedule_state | {"state": "planned"}     |
    | schedule_state | {"state": "implemented"} |
    | schedule_state | {"state": "invalid"}     |

  Scenario: Admin can set archived schedule as implemented
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "archived"}
    When api request method is PATCH
    And api request schedule_state data has {"state": "implemented"}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/state is implemented

  Scenario Outline: For archived schedule passing implemented state is the only option
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "archived"}
    When api request method is PATCH
    And api request <object_type> data has <req_data>
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/state
    And api's response body field errors/[0]/detail is Niepoprawna wartość! Możliwe wartości: implemented

    Examples:
    | object_type    | req_data              |
    | schedule_state | {"state": "planned"}  |
    | schedule_state | {"state": "archived"} |
    | schedule_state | {"state": "invalid"}  |

  Scenario: Admin can set schedule as blocked
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "is_blocked": false}
    When api request method is PATCH
    And api request schedule data has {"is_blocked": true}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/is_blocked is True

  Scenario: Agent cannot set schedule as blocked
    Given logged agent user
    And schedule data created with {"schedule_id": 999, "is_blocked": false}
    When api request method is PATCH
    And api request schedule data has {"is_blocked": true}
    And api request path is /auth/schedules/999
    And api request language is pl
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden
    And api's response body field errors/[0]/detail is Wymagane są dodatkowe uprawnienia!
