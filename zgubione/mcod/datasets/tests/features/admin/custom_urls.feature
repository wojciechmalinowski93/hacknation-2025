Feature: Custom urls
  Scenario Outline: Custom url to dataset details works ok
    Given <object_type> created with params <params>
    When admin's page /datasets/dataset/999/details/ is requested
    Then admin's response status code is 200
    And admin's response page contains <contained_value>
    Examples:
    | object_type | params                                                               | contained_value                                                                                                   |
    | dataset     | {"id": 999, "has_high_value_data": true, "has_high_value_data_from_ec_list": null, "has_dynamic_data": true, "has_research_data": true}    | {"has_high_value_data": true, "has_high_value_data_from_ec_list": null, "has_dynamic_data": true, "has_research_data": true}    |
    | dataset     | {"id": 999, "has_high_value_data": false, "has_high_value_data_from_ec_list": null, "has_dynamic_data": false, "has_research_data": false} | {"has_high_value_data": false, "has_high_value_data_from_ec_list": null, "has_dynamic_data": false, "has_research_data": false} |
    | dataset     | {"id": 999, "has_high_value_data": null, "has_high_value_data_from_ec_list": null, "has_dynamic_data": null, "has_research_data": null}    | {"has_high_value_data": null, "has_high_value_data_from_ec_list": null, "has_dynamic_data": null, "has_research_data": null}    |

  Scenario: Custom url to dataset details for invalid dataset id
    When admin's page /datasets/dataset/23423423423/details/ is requested
    Then admin's response status code is 200
    And admin's response page contains {}
