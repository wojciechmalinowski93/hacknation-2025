Feature: Guide details page in admin panel
  Scenario: Guide creation is ok
    When admin's request method is POST
    And admin's request posted guide data is {"title": "test ok"}
    And admin's page /guides/guide/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test ok</a>" został pomyślnie dodany.
