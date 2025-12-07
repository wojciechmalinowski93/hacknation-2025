Feature: Send dataset update reminders

  Scenario Outline: Dataset to send update reminders is selected properly from multiple objects
    Given <object_type> created with params <params>
    And <object_type> created with params <another_params>
    And <param_object_type> with id <param_object_id> and <param_field_name> is <param_value>
    And <param_object_type> with id <another_param_object_id> and <param_field_name> is <another_param_value>
    When Dataset with id <param_value> resource's data_date delay equals <first_delay> and dataset with id <another_param_value> resource's data_date delay equals <second_delay>
    And Dataset update reminders are sent
    Then There is 1 sent reminder for dataset with title <dataset_title>

      Examples:
    |object_type | params                                                                                                  | another_params                                                                                         | param_object_type  |param_field_name| param_object_id | param_value  |  another_param_object_id | another_param_value | first_delay | second_delay | dataset_title |
    | dataset    | {"id": 991, "title": "Pierwszy zbior", "update_frequency": "weekly"}                                    | {"id": 992, "title": "Drugi zbior", "update_frequency": "monthly", "update_notification_frequency": 3} | resource           | dataset_id     | 911             | 991          |  912                     | 992                 | 1           | 3            | Drugi zbior   |
    | dataset    | {"id": 993, "title": "Pierwszy zbior", "update_frequency": "weekly", "update_notification_frequency":4} | {"id": 994, "title": "Drugi zbior", "update_frequency": "weekly", "update_notification_frequency": 1}  | resource           | dataset_id     | 913             | 993          |  914                     | 994                 | 4           | 4            | Pierwszy zbior|
