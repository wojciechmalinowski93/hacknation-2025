Feature: Extra tests
  Scenario: Endpoint /auth/user_schedule_items/institutions returns list of institutions for agent
    Given institution with id 999
    And logged agent user created with {"id": 999, "agent_organizations": [999]}
    When api request path is /auth/user_schedule_items/institutions
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/*/type is institution

  Scenario: Endpoint /auth/user_schedule_items/institutions/<id> returns institutions for specified agent
    Given institution with id 999
    And logged out agent user created with {"id": 999, "agent_organizations": [999]}
    And logged admin user
    When api request path is /auth/user_schedule_items/institutions/999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/*/type is institution

  Scenario: Endpoint /auth/user_schedule_items/institutions/<id> returns 404 for invalid agent id
    Given institution with id 999
    And logged out agent user created with {"id": 999, "agent_organizations": [999]}
    And logged admin user
    When api request path is /auth/user_schedule_items/institutions/9999
    Then send api request and fetch the response
    And api's response status code is 404

  Scenario Outline: Export user schedule items to xlsx file
    Given institution with id 999
    And logged agent user created with {"id": 999, "agent_organizations": [999]}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/type is export
    And api's response body field data/attributes/url endswith .xlsx
    And api request path from response is data/attributes/url
    # the next line is added to disable json api validation of response during test.
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    And api's response status code is 200
    And api's response header content-type is application/vnd.ms-excel
    And api's response header content-disposition contains attachment; filename=
    And api's response header content-disposition contains .xlsx
    Examples:
    | request_path                        |
    | /auth/schedules/current.xlsx        |
    | /auth/schedules/999.xlsx            |
    | /auth/user_schedules.xlsx           |
    | /auth/user_schedules/999/items.xlsx |

  Scenario Outline: Export user schedule items to xlsx file returns 404 for invalid schedule id in url
    Given institution with id 999
    And logged agent user created with {"id": 999, "agent_organizations": [999]}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/type is export
    And api's response body field <resp_body_field> endswith <resp_body_value>
    And api request path from response is data/attributes/url
    And api request path substring 999 is replaced by 9999
    # the next line is added to disable json api validation of response during test.
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    And api's response status code is 404
    Examples:
    | request_path                        | resp_body_field     | resp_body_value |
    | /auth/schedules/999.xlsx            | data/attributes/url | .xlsx           |
    | /auth/user_schedules/999/items.xlsx | data/attributes/url | .xlsx           |
    | /auth/schedules/999.csv             | data/attributes/url | .csv            |
    | /auth/user_schedules/999/items.csv  | data/attributes/url | .csv            |

  Scenario Outline: Export user schedule items to csv file
    Given institution with id 999
    And logged agent user created with {"id": 999, "agent_organizations": [999]}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/type is export
    And api's response body field data/attributes/url endswith .csv
    And api request path from response is data/attributes/url
    # the next line is added to disable json api validation of response during test.
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    And api's response status code is 200
    And api's response header content-type is text/csv
    And api's response header content-disposition contains attachment; filename=
    And api's response header content-disposition contains .csv
    Examples:
    | request_path                       |
    | /auth/schedules/current.csv        |
    | /auth/schedules/999.csv            |
    | /auth/user_schedules.csv           |
    | /auth/user_schedules/999/items.csv |

  Scenario: Create notification as admin
    Given logged admin user
    When api request method is POST
    And api request notification data has {"message": "Test", "notification_type": "all"}
    And api request path is /auth/schedule_notifications/
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/result is Powiadomienie zostało wysłane

  Scenario: Set all notifications as read
    Given logged admin user
    When api request method is PATCH
    And api request notification data has {"unread": false}
    And api request path is /auth/schedule_notifications/
    And send api request and fetch the response
    Then api's response status code is 202

  Scenario: Notification details endpoint returns 404 for invalid notification id
    Given logged admin user
    When api request path is /auth/schedule_notifications/9999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Update notification request returns 404 for invalid notification id
    Given logged admin user
    When api request method is PATCH
    And api request notification data has {"unread": false}
    And api request path is /auth/schedule_notifications/9999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Update notification request works fine
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "notification_id": 999}
    When api request method is PATCH
    And api request notification data has {"unread": false}
    And api request path is /auth/schedule_notifications/999
    # the next line is added to disable json api validation of response during test.
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    Then api's response status code is 200

  Scenario: Update notification request returns error if notification is not related to request user
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "notification_id": 999}
    And logged agent user
    When api request method is PATCH
    And api request notification data has {"unread": false}
    And api request path is /auth/schedule_notifications/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You have no permission to update the resource.

  Scenario: Send schedule notifications task
    Given schedule data created with {"schedule_id": 999, "schedule_state": "planned", "user_schedule_id": 999, "user_schedule_item_id": 999}
    When send schedule notifications task
    Then send schedule notifications task result is {}
