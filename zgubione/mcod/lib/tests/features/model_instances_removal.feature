  Feature: Model instances removal
    Scenario Outline: Remove model instances
      Given factory <object_type> with params <params>
      When admin's path is changelist for <object_type>
      And admin's page is requested
      Then admin's response status code is 200
      And <object_type> has trash if <has_trash>
      And object is deletable in admin panel if <can_delete>
      And object can be removed from database by button if <can_delete> and <can_remove_from_db>
      And object can be removed from database by action if <can_delete> and <can_remove_from_db>
      And object can be removed from database by model delete method if <can_delete> and <can_remove_from_db>
      And object can be removed from database by queryset delete method if <can_delete> and <can_remove_from_db>

    Examples:
    | object_type               |                              params| has_trash | can_delete | can_remove_from_db |
    | course                    |                       {"id": 1001} |         1 |          1 |                  0 |
    | search history            |                       {"id": 1001} |         0 |          1 |                  1 |
    | institution               |                       {"id": 1001} |         1 |          1 |                  0 |
    | category                  |                       {"id": 1001} |         1 |          1 |                  0 |
    | lab_event                 |                       {"id": 1001} |         1 |          1 |                  0 |
    | newsletter                |                       {"id": 1001} |         0 |          1 |                  1 |
    | submission                |                       {"id": 1001} |         0 |          0 |                  0 |
    | subscription              |                       {"id": 1001} |         0 |          1 |                  1 |
    | guide                     |                       {"id": 1001} |         1 |          1 |                  0 |
    | organizationreport        |                       {"id": 1001} |         0 |          1 |                  1 |
    | userreport                |                       {"id": 1001} |         0 |          1 |                  1 |
    | resourcereport            |                       {"id": 1001} |         0 |          1 |                  1 |
    | datasetreport             |                       {"id": 1001} |         0 |          1 |                  1 |
    | summarydailyreport        |                       {"id": 1001} |         0 |          1 |                  1 |
    | monitoringreport          |                       {"id": 1001} |         0 |          1 |                  1 |
    | tag                       |     {"id": 1001, "language": "pl"} |         0 |          1 |                  1 |
    | meeting                   |                       {"id": 1001} |         1 |          1 |                  0 |
    | active user               |                       {"id": 1001} |         0 |          1 |                  0 |
    | resource                  |                       {"id": 1001} |         1 |          1 |                  0 |
    | dataset                   |                       {"id": 1001} |         1 |          1 |                  0 |
    | datasetsubmission         |                       {"id": 1001} |         1 |          1 |                  0 |
    | resourcecomment           |                       {"id": 1001} |         1 |          1 |                  0 |
    | datasetcomment            |                       {"id": 1001} |         1 |          1 |                  0 |
    | accepteddatasetsubmission |                       {"id": 1001} |         1 |          1 |                  0 |
    | specialsign               |                       {"id": 1001} |         0 |          1 |                  0 |
    | datasourceimport          |                       {"id": 1001} |         0 |          0 |                  0 |
    | datasource                | {"id": 1001, "status": "inactive"} |         1 |          1 |                  0 |
    | datasource                |   {"id": 1002, "status": "active"} |         1 |          0 |                  0 |
    | showcase                  |                       {"id": 1001} |         1 |          1 |                  0 |
    | showcaseproposal          |                       {"id": 1001} |         1 |          1 |                  0 |


    Scenario Outline: Remove model instances from trash
      Given removed factory <object_type> with params <params>
      When admin's page <page_url> is requested
      Then admin's response status code is 200
      And admin's path is trash change for <object_type>
      And admin's page is requested
      And admin's response status code is 200
      And admin's response page contains name="_save">Zapisz</button
      And admin's response page not contains Zapisz i kontynuuj edycję
      And removed object is flagged as permanently removed after deleted from trash by button
      And removed object is flagged as permanently removed after deleted from trash by action
      And removed object is flagged as permanently removed after deleted from trash by model delete method
      And removed object is flagged as permanently removed after deleted from trash by trash queryset delete method

    Examples:
    | object_type               | page_url                                     | params       |
    | course                    | /academy/coursetrash/                        | {"id": 1003} |
    | institution               | /organizations/organizationtrash/            | {"id": 1003} |
    | category                  | /categories/categorytrash/                   | {"id": 1003} |
    | lab_event                 | /laboratory/labeventtrash/                   | {"id": 1003} |
    | guide                     | /guides/guidetrash/                          | {"id": 1003} |
    | meeting                   | /users/meetingtrash/                         | {"id": 1003} |
    | resource                  | /resources/resourcetrash/                    | {"id": 1003} |
    | dataset                   | /datasets/datasettrash/                      | {"id": 1003} |
    | datasetsubmission         | /suggestions/datasetsubmissiontrash/         | {"id": 1003} |
    | resourcecomment           | /suggestions/resourcecommenttrash/           | {"id": 1003} |
    | datasetcomment            | /suggestions/datasetcommenttrash/            | {"id": 1003} |
    | accepteddatasetsubmission | /suggestions/accepteddatasetsubmissiontrash/ | {"id": 1003} |
    | datasource                | /harvester/datasourcetrash/                  | {"id": 1003, "status": "inactive"} |
    | showcase                  | /showcases/showcasetrash/                    | {"id": 1003} |
    | showcaseproposal          | /showcases/showcaseproposaltrash/            | {"id": 1003} |
