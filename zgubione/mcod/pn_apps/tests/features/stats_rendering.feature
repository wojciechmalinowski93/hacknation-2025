Feature: Statistics display

  Scenario Outline: Statistics are rendered successfully for users
    Given 3 datasets with 3 resources
    And stats document viewed by <user_type>
    Then Figures are rendered without errors

    Examples:
    | user_type   |
    | admin user  |
    | editor user |
    | active user |
    | agent user  |

  Scenario: Statistics with data for agents are rendered successfully
    Given institution with id 999
    And dataset created with params {"id": 998, "organization_id": 999}
    And resource with id 999 and dataset_id is 998
    And stats document viewed by agent created with params {"id": 999, "agent_organizations": [999]}
    Then Figures are rendered without errors
