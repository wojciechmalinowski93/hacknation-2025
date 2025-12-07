Feature: Dataset Comment

  Scenario Outline: Commenting for dataset works fine
    Given dataset with id 999
    And list of sent emails is empty
    When api request method is POST
    And api request header <req_header_name> is <req_header_value>
    And api request path is /1.4/datasets/999/comments
    And api request posted data is {"data": {"type": "comment", "attributes": {"comment": "Some comment for dataset 999."}}}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/comment is Some comment for dataset 999.
    And sent email contains Some comment for dataset 999.
    And sent email contains została zgłoszona uwaga

    Examples:
    | req_header_name | req_header_value |
    | Accept-Language | en               |
    | Accept-Language | pl               |

  Scenario: Adding of dataset comment returns error if comment is too short
    Given dataset with id 999
    When api request method is POST
    And api request path is /datasets/999/comments
    And api request posted data is {"data": {"type": "comment", "attributes": {"comment": "OK"}}}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is Komentarz musi mieć przynajmniej 3 znaki

  Scenario: Dataset comment recipients list contains email from update_notification_recipient_email attribute of related dataset
    Given dataset created with params {"id": 999, "update_notification_recipient_email": "update_notification_recipient_email@example.com"}
    When api request method is POST
    And api request path is /datasets/999/comments
    And api request dataset_comment data has {}
    And send api request and fetch the response
    Then latest datasetcomment attribute editor_email is update_notification_recipient_email@example.com
