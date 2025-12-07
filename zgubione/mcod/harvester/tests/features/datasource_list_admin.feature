Feature: DataSources list in admin panel

  Scenario: Administrator can see list of datasources
    Given institution with id 999
    And active ckan_datasource with id 101 for data {"organization_id": 999, "name": "Other org import"}
    When admin's page /harvester/datasource/ is requested
    Then admin's response status code is 200
    And admin's response page contains Other org import
