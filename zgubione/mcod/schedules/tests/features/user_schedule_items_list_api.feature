Feature: User schedule items list API
  Scenario: Test that user schedule item list endpoint can be filtered by planned state
    Given logged admin user
    And 3 user schedule items with state planned
    When api request path is /auth/user_schedule_items?state=planned
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field meta/count is 3
    And api's response body field data/*/attributes/state is planned

  Scenario: Test that user schedule item list endpoint can be filtered by implemented state
    Given logged admin user
    And 3 user schedule items with state implemented
    When api request path is /auth/user_schedule_items?state=implemented
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field meta/count is 3
    And api's response body field data/*/attributes/state is implemented

  Scenario: Test that user schedule item list endpoint can be filtered by archived state
    Given logged admin user
    And 3 user schedule items with state archived
    When api request path is /auth/user_schedule_items?state=archived
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field meta/count is 3
    And api's response body field data/*/attributes/state is archived

  Scenario: Test that user schedule item list endpoint returns error message if invalid state is passed
    Given logged admin user
    And 3 user schedule items with state planned
    When api request language is pl
    And api request path is /auth/user_schedule_items?state=invalid
    Then send api request and fetch the response
    And api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /state
    And api's response body field errors/[0]/detail is Niepoprawna wartość! Możliwe wartości: planned, implemented, archived

  Scenario: Test that user schedule item list results can be filtered by specified phrase
    Given logged admin user
    And 3 user schedule items with state planned
    And user_schedule_item created with params {"id": 999, "dataset_title": "Zbiór testowy"}
    When api request language is pl
    And api request path is /auth/user_schedule_items?q=testow
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/dataset_title is Zbiór testowy

  Scenario: Test that user schedule item list results can be filtered by specified phrase with exclude_id param
    Given logged admin user
    And 3 user schedule items with state planned
    And user_schedule_item created with params {"id": 999, "dataset_title": "Zbiór testowy"}
    When api request language is pl
    And api request path is /auth/user_schedule_items?q=testow&exclude_id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/*/id is not 999

  Scenario: Test that admin can list user schedule items related to specified schedule
    Given logged out agent user created with {"id": 999}
    And user_schedule_item with id 998
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged admin user
    When api request path is /auth/schedules/999/user_schedule_items
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field meta/count is 1
    And api's response body field data/[0]/id is 999

  Scenario: Test that agent can list all his user schedule items related to specified schedule
    Given logged agent user created with {"id": 999}
    And user_schedule_item with id 998
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is /auth/schedules/999/user_schedule_items
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field meta/count is 1
    And api's response body field data/[0]/id is 999
