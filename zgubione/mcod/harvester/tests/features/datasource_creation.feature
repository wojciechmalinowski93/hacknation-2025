Feature: DataSource creation

  Scenario: Last activation date is updated during activation of data source.
    Given CKAN datasource with id 999 inactive
    And datasource with id 999 attribute last_activation_date is set to 2019-09-01 12:00:00Z
    Then datasource with id 999 is activated and last_activation_date is updated

  Scenario: Last activation date is not updated during deactivation of data source.
    Given CKAN datasource with id 999 active
    And datasource with id 999 attribute last_activation_date is set to None
    Then datasource with id 999 is deactivated and last_activation_date is not updated
