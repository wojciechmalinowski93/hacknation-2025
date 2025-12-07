Feature: Schedules details API
  Scenario Outline: User schedule details endpoint is accessible by admin but not active user
    Given logged <user_type>
    And user_schedule created with params {"id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is <status_code>

    Examples:
    | user_type   | request_path             | status_code |
    | admin user  | /auth/user_schedules/999 | 200         |
    | active user | /auth/user_schedules/999 | 403         |

  Scenario: User schedule details endpoint returns valid data for admin
    Given logged admin user
    And user_schedule with id 999
    When api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/type is user_schedule
    And api's response body field data/id is 999
    And api's response body field data/attributes has fields email,institution,items_count,is_blocked,is_ready,recommended_items_count,implemented_items_count,state

  Scenario: Currently planned user schedule details endpoint is not available for admin
    Given logged admin user
    When api request path is /auth/user_schedules/current
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Currently planned user schedule details endpoint for agent returns 404 if no currently planned schedule yet
    Given logged agent user
    When api request path is /auth/user_schedules/current
    And send api request and fetch the response
    Then api's response status code is 404

 Scenario: Currently planned user schedule details endpoint returns valid data for agent who created it
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "planned", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is /auth/user_schedules/current
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/type is user_schedule
    And api's response body field data/id is 999
    And api's response body field data/attributes has fields email,institution,items_count,is_blocked,is_ready,recommended_items_count,implemented_items_count,state

  Scenario: User schedule details endpoint returns valid data for agent who created it
    Given logged agent user created with {"id": 999}
    And user_schedule created with params {"id": 999, "user_id": 999}
    When api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/type is user_schedule
    And api's response body field data/id is 999
    And api's response body field data/attributes has fields email,institution,items_count,is_blocked,is_ready,recommended_items_count,implemented_items_count,state

  Scenario: User schedule details endpoint returns valid data for extra agent of agent who created it
    Given logged extra agent with id 998 of agent with id 999
    And user_schedule created with params {"id": 999, "user_id": 999}
    When api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/type is user_schedule
    And api's response body field data/id is 999
    And api's response body field data/attributes has fields email,institution,items_count,is_blocked,is_ready,recommended_items_count,implemented_items_count,state

  Scenario: User schedule details endpoint is not available for agents other than agent related to the schedule
    Given logged out agent user created with {"id": 998, "email": "agent2@dane.gov.pl"}
    And logged agent user created with {"id": 999}
    And user_schedule created with params {"id": 999, "user_id": 998}
    When api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: User schedule without related recommended or not_recommended items is not set as blocked
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "awaits"}
    When api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response body field data/attributes/is_blocked is False

  Scenario: User schedule with related recommended or not_recommended items is set as blocked
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response body field data/attributes/is_blocked is True

  Scenario: Agent is able to set is_ready field is user schedule is not blocked
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "awaits"}
    When api request method is PATCH
    And api request user_schedule data has {"is_ready": true}
    And api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/is_ready is True
    And api's response body field data/attributes/is_blocked is False

  Scenario: Agent cannot set is_ready field for blocked user schedule
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request method is PATCH
    And api request user_schedule data has {"is_ready": true}
    And api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/is_ready
    And api's response body field errors/[0]/detail is Nie można zmienić statusu gotowości harmonogramu!

  Scenario: Update user schedule by agent returns 404 for invalid user schedule id (9999)
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request method is PATCH
    And api request user_schedule data has {"is_ready": true}
    And api request path is /auth/user_schedules/9999
    And send api request and fetch the response
    Then api's response status code is 404
