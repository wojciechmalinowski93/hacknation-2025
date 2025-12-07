Feature: User schedule item update API
  Scenario: User schedule item cannot be updated by active user
    Given logged out agent user created with {"id": 999}
    And logged active user
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_data data has {"is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

  Scenario: User schedule item cannot be updated by agent different than related to the user schedule item
    Given logged out agent user created with {"id": 998, "email": "agent2@dane.gov.pl"}
    And logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 998, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You have no permission to update the resource!

  Scenario: Update user schedule item returns 404 for invalid user schedule item id (9999)
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "pdf", "is_new": true}
    And api request path is /auth/user_schedule_items/9999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: User schedule item is available for update by agent related to the user schedule item
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "pdf", "is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/id is 999
    And api's response body field data/attributes/dataset_title is Test
    And api's response body field data/attributes/format is pdf
    And api's response body field data/attributes/institution is Ministerstwo Cyfryzacji

  Scenario: User schedule item is available for update by admin
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "pdf", "is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/id is 999
    And api's response body field data/attributes/dataset_title is Test
    And api's response body field data/attributes/format is pdf
    And api's response body field data/attributes/institution is Ministerstwo Cyfryzacji

  Scenario: User schedule item planning data cannot be updated by agent if schedule state is implemented
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "pdf", "is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/*/source/pointer contains /data/attributes/is_resource_added
    And api's response body field errors/*/detail contains Brak danych w wymaganym polu.

  Scenario: Recommendation_state and is_accepted can be set by passing recommendation_state field in request
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "txt", "is_new": true, "recommendation_state": "not_recommended", "recommendation_notes": "komentarz do rekomendacji"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/recommendation_state is not_recommended
    And api's response body field data/attributes/is_accepted is False
    And api's response body field data/attributes/recommendation_notes is komentarz do rekomendacji

  Scenario: Recommendation_comment is required when recommendation_state is set as not_recommended
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "txt", "is_new": true, "recommendation_state": "not_recommended"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is To pole jest obowiązkowe!
    And api's response body field errors/[0]/source/pointer is /data/attributes/recommendation_notes

  Scenario: Recommendation_state and is_accepted can be set by passing is_accepted as true in request
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "txt", "is_new": true, "is_accepted": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/recommendation_state is recommended
    And api's response body field data/attributes/is_accepted is True

  Scenario: Recommendation_state and is_accepted can be set by passing is_accepted as false in request
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "txt", "is_new": true, "is_accepted": false, "recommendation_notes": "komentarz do rekomendacji"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/recommendation_state is not_recommended
    And api's response body field data/attributes/is_accepted is False

  Scenario: User schedule item planning data can be updated by admin even if schedule state is implemented
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "txt", "is_new": true, "recommendation_state": "recommended"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/format is txt

  Scenario: User schedule item update requires format passed in request
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"format": "", "is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is Shorter than minimum length 1.
    And api's response body field errors/[0]/source/pointer is /data/attributes/format

  Scenario: User schedule item update requires institution passed in request
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"institution": "", "is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/source/pointer is /data/attributes/institution
    And api's response body field errors/[0]/detail is Shorter than minimum length 1.

  Scenario: Planned user schedule item is available to update for admin
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "planned", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item_admin data has {"institution": "MC", "institution_unit": "OD", "dataset_title": "Z1", "format": "csv", "is_new": true, "description": "desc...", "recommendation_state": "not_recommended", "recommendation_notes": "notes..."}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/institution is MC
    And api's response body field data/attributes/institution_unit is OD
    And api's response body field data/attributes/dataset_title is Z1
    And api's response body field data/attributes/format is csv
    And api's response body field data/attributes/is_new is True
    And api's response body field data/attributes/description is desc...
    And api's response body field data/attributes/recommendation_state is not_recommended
    And api's response body field data/attributes/recommendation_notes is notes...

  Scenario: User schedule item with state set to implemented is available for admin recommendation
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item_admin data has {"recommendation_notes": "notes..."}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/recommendation_state is recommended
    And api's response body field data/attributes/recommendation_notes is notes...

  Scenario: User schedule item with state set to implemented cannot be recommended by agent
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item_admin data has {"recommendation_state": "recommended"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/*/source/pointer contains /data/attributes/recommendation_state
    And api's response body field errors/*/detail contains Unknown field.

  Scenario: Accepted (recommendation_state=recommended) user schedule item with state set to implemented is available for agent to set resource info
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request method is PATCH
    And api request user_schedule_item_agent data has {"is_resource_added": true, "is_resource_added_notes": "komentarz...", "resource_link": "http://dane.gov.pl"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/resource_link is http://dane.gov.pl
    And api's response body field data/attributes/is_resource_added is True
    And api's response body field data/attributes/is_resource_added_notes is komentarz...
    And api's response body has no field data/attributes/recommendation_state
    And api's response body has no field data/attributes/recommendation_notes

  Scenario: Resource_link is required during set resource info request if is_resource_added is True
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request method is PATCH
    And api request user_schedule_item_agent data has {"is_resource_added": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is To pole jest obowiązkowe!
    And api's response body field errors/[0]/source/pointer is /data/attributes/resource_link

  Scenario: Attribute is_resource_added_notes is required during set resource info request if is_resource_added is False
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request method is PATCH
    And api request user_schedule_item_agent data has {"is_resource_added": false}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is To pole jest obowiązkowe!
    And api's response body field errors/[0]/source/pointer is /data/attributes/is_resource_added_notes

  Scenario: Archived user schedule item cannot be updated by related agent
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "archived", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_data data has {"is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You have no permission to update the resource!

  Scenario: Archived user schedule item is available to update for admin
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "schedule_state": "archived", "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_item data has {"dataset_title": "Edycja", "is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/dataset_title is Edycja

  Scenario: User schedule item related to blocked schedule cannot be updated by agent
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is PATCH
    And api request user_schedule_data data has {"is_new": true}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is The schedule is blocked!

  Scenario: User schedule item related to blocked schedule can be updated by admin
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged admin user
    When api request method is PATCH
    And api request user_schedule_data data has {"is_new": true, "dataset_title": "Zgłoszenie po edycji administratora"}
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/dataset_title is Zgłoszenie po edycji administratora
