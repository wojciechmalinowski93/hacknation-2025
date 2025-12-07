@elasticsearch
Feature: Query Watcher
  Scenario: query watcher created by request has initial ref_value equal to search's current /meta/count
    Given logged active user
    And dataset created with params {"id": 2110, "title": "Creative Name"}
    And dataset created with params {"id": 2111, "title": "Regular Name"}

    When api request path is /search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/count is 1

    Then api request method is POST
    And api request path is /auth/subscriptions
    And api request body field /data is of type dict
    And api request body field /data/type is subscription
    And api request body field /data/attributes/name is QUERY_RESULT_NAME
    And api request body field /data/attributes/object_ident is http://api.test.mcod/search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And api request body field /data/attributes/object_name is query
    And api request body field /data/attributes/objects_count is 1
    And send api request and fetch the response
    Then api's response status code is 201

    Then api request method is GET
    And api request path is /auth/notifications
    And send api request and fetch the response
    And api's response body field /meta/count is 0

    Then trigger query watcher update

    Then api request path is /auth/notifications
    And send api request and fetch the response
    And api's response body field /meta/count is 0

    Then set status to draft on dataset with id 2110
    And trigger query watcher update

    Then send api request and fetch the response
    And api's response body field /meta/count is 1
    And api's response body field /data/0/attributes/notification_type is result_count_decresed
    And api's response body field /data/0/attributes/ref_value is 0
    And api's response body field /data/0/relationships/subscribed_object/data/id is http://api.test.mcod/search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And api's response body field /data/0/relationships/subscribed_object/data/type is query

  Scenario: query watcher updates
    Given logged active user
    And dataset created with params {"id": 2112, "title": "Creative Name"}
    And dataset created with params {"id": 2113, "title": "Regular Name"}

    And query subscription with id 999 for url /search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance with 1 results

    When api request path is /auth/subscriptions/999
    And send api request and fetch the response
    Then api's response status code is 200

    And api request path is /auth/notifications
    And send api request and fetch the response
    And api's response body field /meta/count is 0

    And set status to draft on dataset with id 2112
    And trigger query watcher update

    And send api request and fetch the response
    And api's response body field /meta/count is 1
    And api's response body field /data/0/attributes/notification_type is result_count_decresed
    And api's response body field /data/0/attributes/ref_value is 0
    And api's response body field /data/0/relationships/subscribed_object/data/id is /search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And api's response body field /data/0/relationships/subscribed_object/data/type is query

    And set status to published on dataset with id 2112
    And trigger query watcher update

    And send api request and fetch the response
    And api's response body field /meta/count is 2
    And api's response body field /data/0/attributes/notification_type is result_count_incresed
    And api's response body field /data/0/attributes/ref_value is 1
    And api's response body field /data/0/relationships/subscribed_object/data/id is /search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And api's response body field /data/0/relationships/subscribed_object/data/type is query

    And remove dataset with id 2112
    And trigger query watcher update

    And send api request and fetch the response
    And api's response body field /meta/count is 3
    And api's response body field /data/0/attributes/notification_type is result_count_decresed
    And api's response body field /data/0/attributes/ref_value is 0
    And api's response body field /data/0/relationships/subscribed_object/data/id is /search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And api's response body field /data/0/relationships/subscribed_object/data/type is query

    And restore dataset with id 2112
    And trigger query watcher update

    And send api request and fetch the response
    And api's response body field /meta/count is 4
    And api's response body field /data/0/attributes/notification_type is result_count_incresed
    And api's response body field /data/0/attributes/ref_value is 1
    And api's response body field /data/0/relationships/subscribed_object/data/id is /search?advanced=all&model[terms]=dataset&page=1&per_page=20&q=creative&sort=relevance
    And api's response body field /data/0/relationships/subscribed_object/data/type is query
