Feature: Alerts
  Scenario: Adding alerts
    Given I'm logged as an admin user
    When I go to the alerts page
    Then the alerts page is empty
    And I click ADD button
    And I fill the form
    And I click SAVE button
