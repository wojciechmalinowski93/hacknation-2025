@elasticsearch
Feature: Dashboard schedules section

  Scenario: Admin sees specific schedules data in dashboard.
    Given logged admin user
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response body has no field /meta/aggregations/schedules/schedule_items
    And api's response body has no field /meta/aggregations/schedules/state
    And api's response body has field /meta/aggregations/schedules/started
    And api's response body has field /meta/aggregations/schedules/ready
    And api's response body has field /meta/aggregations/schedules/recommended
    And api's response body has field /meta/aggregations/schedules/notifications_count
    And api's response body has field /meta/aggregations/schedules/notifications

  Scenario: Agent user sees specific schedules data in dashboard.
    Given logged agent user
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response body has no field /meta/aggregations/schedules/started
    And api's response body has no field /meta/aggregations/schedules/ready
    And api's response body has no field /meta/aggregations/schedules/recommended
    And api's response body has field /meta/aggregations/schedules/schedule_items
    And api's response body has field /meta/aggregations/schedules/state
    And api's response body has field /meta/aggregations/schedules/notifications_count
    And api's response body has field /meta/aggregations/schedules/notifications

  Scenario: Test that admin user can display schedule comments notifications
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 995, "user_schedule_item_id": 996, "comment_id": 998}
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/aggregations/schedules/notifications/[0]/user_schedule_id is 995
    And api's response body field /meta/aggregations/schedules/notifications/[0]/user_schedule_item_id is 996
    And api's response body field /meta/aggregations/schedules/notifications/[0]/schedule_id is 999
    And api's response body field /meta/aggregations/schedules/notifications/[0]/schedule_state is planned
