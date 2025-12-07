Feature: User schedule item details API

  Scenario Outline: Attributes is_openness_score_increased and is_quality_improved are not editable if is_new is true in create user_schedule_item request
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999}
    When api request method is POST
    And api request <object_type> data has <req_data>
    And api request path is /auth/user_schedule_items/
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/is_new is True
    And api's response body field data/attributes/is_openness_score_increased is None
    And api's response body field data/attributes/is_quality_improved is None
    Examples:
    | object_type        | req_data                                                                             |
    | user_schedule_item | {"is_new": true}                                                                     |
    | user_schedule_item | {"is_new": true, "is_openness_score_increased": true}                                |
    | user_schedule_item | {"is_new": true, "is_quality_improved": true}                                        |
    | user_schedule_item | {"is_new": true, "is_openness_score_increased": false, "is_quality_improved": false} |
    | user_schedule_item | {"is_new": true, "is_openness_score_increased": true, "is_quality_improved": true}   |

  Scenario Outline: Passing at least one of is_openness_score_increased or is_quality_improved fields is required if is_new is false
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999}
    When api request method is POST
    And api request <object_type> data has <req_data>
    And api request path is /auth/user_schedule_items/
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/is_new is False
    Examples:
    | object_type        | req_data                                                                              |
    | user_schedule_item | {"is_new": false, "is_openness_score_increased": true}                                |
    | user_schedule_item | {"is_new": false, "is_quality_improved": true}                                        |
    | user_schedule_item | {"is_new": false, "is_openness_score_increased": true, "is_quality_improved": true}   |
    | user_schedule_item | {"is_new": false, "is_openness_score_increased": false}                               |
    | user_schedule_item | {"is_new": false, "is_quality_improved": false}                                       |
    | user_schedule_item | {"is_new": false, "is_openness_score_increased": false, "is_quality_improved": false} |

  Scenario: Not passing at least one of is_openness_score_increased or is_quality_improved fields returns error if is_new is false
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999}
    When api request method is POST
    And api request user_schedule_item data has {"is_new": false}
    And api request path is /auth/user_schedule_items/
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/*/source/pointer contains /data/attributes/_schema
    And api's response body field errors/*/detail contains is_openness_score_increased lub is_quality_improved są wymagane jeśli wartość is_new to False!

  Scenario Outline: Admin can add new user schedule item to schedule
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "implemented", "user_id": 999, "user_schedule_id": 999}
    And logged admin user
    When api request method is POST
    And api request <object_type> data has <req_data>
    And api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/dataset_title is Zgłoszenie w realizacji
    Examples:
    | object_type        | req_data                                                                                                                                                                                                                              |
    | user_schedule_item | {"dataset_title": "Zgłoszenie w realizacji", "is_new": true, "description": "", "is_accepted": true, "is_resource_added_notes": "komentarz", "is_resource_added": false, "recommendation_notes": "", "resource_link": ""}             |
    | user_schedule_item | {"dataset_title": "Zgłoszenie w realizacji", "is_new": true, "description": "", "is_accepted": true, "is_resource_added_notes": "komentarz", "is_resource_added": false, "recommendation_notes": "", "resource_link": null}           |
    | user_schedule_item | {"dataset_title": "Zgłoszenie w realizacji", "is_new": true, "description": "", "is_accepted": true, "is_resource_added_notes": "komentarz", "is_resource_added": false, "recommendation_notes": null, "resource_link": ""}           |
    | user_schedule_item | {"dataset_title": "Zgłoszenie w realizacji", "is_new": true, "description": "", "is_accepted": true, "is_resource_added_notes": "komentarz", "is_resource_added": false, "recommendation_notes": null, "resource_link": null}         |
    | user_schedule_item | {"dataset_title": "Zgłoszenie w realizacji", "is_new": true, "description": "", "is_accepted": true, "is_resource_added_notes": "", "is_resource_added": true, "recommendation_notes": null, "resource_link": "http://example.com"}   |
    | user_schedule_item | {"dataset_title": "Zgłoszenie w realizacji", "is_new": true, "description": "", "is_accepted": true, "is_resource_added_notes": null, "is_resource_added": true, "recommendation_notes": null, "resource_link": "http://example.com"} |

  Scenario: Agent cannot add new user schedule item if there is no currently planned schedule yet
    Given logged agent user created with {"id": 999}
    When api request method is POST
    And api request user_schedule_item data has {"is_new": true}
    And api request path is /auth/user_schedule_items/
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is There is no currently planned schedule yet!

  Scenario: Agent cannot add new user schedule item if currently planned schedule is blocked
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999}
    When api request method is POST
    And api request user_schedule_item data has {"is_new": false}
    And api request path is /auth/user_schedule_items/
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is The schedule is blocked!

  Scenario: Admin can add new user schedule item to blocked schedule
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999}
    And logged admin user
    When api request method is POST
    And api request user_schedule_item data has {"dataset_title": "Zgłoszenie do zablokowanego harmonogramu", "is_new": true}
    And api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/dataset_title is Zgłoszenie do zablokowanego harmonogramu

  Scenario: Create user schedule item by admin request returns 404 for invalid user schedule id (9999)
    Given logged admin user
    When api request method is POST
    And api request user_schedule_item data has {"dataset_title": "Zgłoszenie do archiwalnego harmonogramu", "is_new": true}
    And api request path is /auth/user_schedules/9999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Admin cannot add new user schedule item to archival schedule
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_state": "archival", "user_id": 999, "user_schedule_id": 999}
    And logged admin user
    When api request method is POST
    And api request user_schedule_item data has {"dataset_title": "Zgłoszenie do archiwalnego harmonogramu", "is_new": true}
    And api request path is /auth/user_schedules/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You cannot add new item to archival schedule!

  Scenario: Agent cannot add new user schedule item if currently planned schedule is set ready
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_is_ready": true}
    When api request method is POST
    And api request user_schedule_item data has {"is_new": true}
    And api request path is /auth/user_schedule_items/
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You cannot add new item - your schedule is set ready!

  Scenario: User schedule item details endpoint returns valid data for admin
    Given logged admin user
    And user_schedule_item with id 999
    When api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/id is 999
    And api's response body field data/type is user_schedule_item
    And api's response body field data/attributes has fields institution,institution_unit,dataset_title,created,is_new,format,is_openness_score_increased,is_quality_improved,description,state,recommendation_state,recommendation_notes,is_completed,is_recommendation_issued

  Scenario: User schedule item details endpoint returns valid data for agent who created it
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/id is 999
    And api's response body field data/type is user_schedule_item
    And api's response body field data/attributes has fields institution,institution_unit,dataset_title,created,is_new,format,is_openness_score_increased,is_quality_improved,description,state,is_completed,is_recommendation_issued
    And api's response body field data/attributes has no fields recommendation_state,recommendation_notes

  Scenario: User schedule item details endpoint is not available by agent other than related to the user schedule item
    Given logged out agent user created with {"id": 998, "email": "agent2@dane.gov.pl"}
    And logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 998, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Delete user schedule item request returns 404 for invalid user schedule item id
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged admin user
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/9999
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: User schedule item details endpoint is not available for active user
    Given logged out agent user created with {"id": 999}
    And logged active user
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403

  Scenario: User schedule item delete endpoint is not available for active user
    Given logged out agent user created with {"id": 999}
    And logged active user
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is 403 Forbidden

  Scenario: User schedule item can be deleted by admin
    Given logged out agent user created with {"id": 999}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 204

  Scenario: User schedule item can be deleted by agent which is related to the user schedule item
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 204

  Scenario: User schedule item cannot be deleted by agent different than related to the user schedule item
    Given logged out agent user created with {"id": 998, "email": "agent2@dane.gov.pl"}
    And logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 998, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You have no permission to delete the resource!

  Scenario: User schedule item cannot be deleted if his recommendation_state is not awaits
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "recommendation_state": "recommended"}
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You have no permission to delete the resource!

  Scenario: User schedule item related to blocked schedule cannot be deleted by agent
    Given logged agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is The schedule is blocked!

  Scenario: User schedule item related to blocked schedule can be deleted by admin
    Given logged out agent user created with {"id": 999}
    And schedule data created with {"schedule_id": 999, "schedule_is_blocked": true, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged admin user
    When api request method is DELETE
    And api request path is /auth/user_schedule_items/999
    And send api request and fetch the response
    Then api's response status code is 204

  Scenario: User schedule item comments list endpoint is available for admin
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "comment_id": 999}
    And logged admin user
    When api request path is /auth/user_schedule_items/999/comments
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/*/attributes has fields author,created,text
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes/text is Test comment...

  Scenario: Agent can list comments related to one of his user schedule items
    Given logged agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "comment_id": 999}
    When api request path is /auth/user_schedule_items/999/comments
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/*/attributes has fields author,created,text
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes/text is Test comment...

  Scenario: User schedule item comments list endpoint is not available for active user
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "comment_id": 999}
    And logged active user
    When api request path is /auth/user_schedule_items/999/comments
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/detail is Wymagane są dodatkowe uprawnienia!

  Scenario: User schedule item comments list endpoint returns 404 for invalid id
    Given logged agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    When api request path is /auth/user_schedule_items/9999/comments
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Agent can add comment related to specified user schedule item
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged agent user
    When api request method is POST
    And api request comment data has {"text": "Test comment"}
    And api request path is /auth/user_schedule_items/999/comments
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/text is Test comment

  Scenario: Admin can add comment related to specified user schedule item
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged admin user
    When api request method is POST
    And api request comment data has {"text": "Test comment"}
    And api request path is /auth/user_schedule_items/999/comments
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/text is Test comment

  Scenario: Posting new comment request returns 404 for invalid user schedule item id
    Given logged admin user
    When api request method is POST
    And api request comment data has {"text": "Test comment"}
    And api request path is /auth/user_schedule_items/9999/comments
    And send api request and fetch the response
    Then api's response status code is 404

  Scenario: Active admin cannot add comment related to specified user schedule item
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    And logged active user
    When api request method is POST
    And api request comment data has {"text": "Test comment"}
    And api request path is /auth/user_schedule_items/999/comments
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/detail is Wymagane są dodatkowe uprawnienia!

  Scenario: User can edit his own comment
    Given logged agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "comment_id": 998}
    When api request method is PATCH
    And api request comment data has {"text": "Edited comment!"}
    And api request path is /auth/user_schedule_items/comments/998/edit
    And send api request and fetch the response
    Then api's response status code is 202
    And api's response body field data/attributes/text is Edited comment!

  Scenario: User cannot edit comment of someone else
    Given logged out agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    And schedule data created with {"schedule_id": 999, "user_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "comment_id": 998}
    And logged agent user
    When api request method is PATCH
    And api request comment data has {"text": "Edit by other user"}
    And api request path is /auth/user_schedule_items/comments/998/edit
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field errors/[0]/title is You have no permission to update the resource!

  Scenario: Edit of comment request returns 404 for invalid user schedule item id
    Given logged agent user created with {"id": 999, "email": "agent@dane.gov.pl"}
    When api request method is PATCH
    And api request comment data has {"text": "Edited comment!"}
    And api request path is /auth/user_schedule_items/comments/9999/edit
    And send api request and fetch the response
    Then api's response status code is 404
