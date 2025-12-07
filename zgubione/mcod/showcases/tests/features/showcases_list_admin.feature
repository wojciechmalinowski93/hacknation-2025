Feature: Showcases list admin

  Scenario: Removed showcase is not on showcases list
    Given removed showcase with id 999
    When admin's page /showcases/showcase/ is requested
    Then admin's response page not contains /showcases/showcase/999/change/

  Scenario: Removed showcase is in trash
    Given removed showcase with id 999
    When admin's page /showcases/showcasetrash/ is requested
    Then admin's response page contains /showcases/showcasetrash/999/change/

  Scenario: Editor doesnt see showcases in admin panel
    Given admin's request logged user is editor user
    When admin's page / is requested
    Then admin's response status code is 200
    And admin's response page not contains /showcases/

  Scenario: Editor cant go to showcases in admin panel
    Given admin's request logged user is editor user
    When admin's page /showcases/ is requested
    Then admin's response status code is 404

  Scenario: Admin can see showcases in admin panel
    When admin's page / is requested
    Then admin's response status code is 200
    And admin's response page contains /showcases/

  Scenario: Admin can go to showcases in admin panel
    When admin's page /showcases/ is requested
    Then admin's response status code is 200
