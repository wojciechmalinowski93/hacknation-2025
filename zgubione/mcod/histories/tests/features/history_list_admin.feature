Feature: History list page in admin panel

    Scenario: History section is visible for admin
    When admin's page /histories/ is requested
    Then admin's response status code is 200
    And admin's response page contains <a id="LogEntryChangeButton" href="/histories/logentry/" class="changelink icon">

  Scenario: History section is not visible for editor user
    Given admin's request logged user is editor user
    When admin's page /histories/ is requested
    Then admin's response status code is 404
    And admin's response page not contains <a id="LogEntryChangeButton" href="/histories/logentry/" class="changelink icon">

  Scenario: History list is visible for admin
    When admin's page /histories/logentry/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz Historia do zmiany

  Scenario: History list is not visible for editor user
    Given admin's request logged user is editor user
    When admin's page /histories/logentry/ is requested
    Then admin's response status code is 403
    And admin's response page not contains Wybierz Historia do zmiany
