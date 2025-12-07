Feature: Meetings list page in admin panel

  Scenario: Meetings section is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /users/ is requested
    Then admin's response status code is 200
    Then admin's response page not contains <a href="/users/meeting">Spotkania pełnomocników</a>
    And admin's response page not contains <a href="/users/meeting/" class="changelink icon">Zmiana</a>

  Scenario: List of meetings is not visible for NOT admin
    Given admin's request logged user is editor user
    When admin's page /users/meeting is requested
    Then admin's response status code is 403

  Scenario: List of deleted meetings (trash) is not visible for NOT superuser
    Given admin's request logged user is editor user
    When admin's page /users/meetingtrash is requested
    Then admin's response status code is 403

  Scenario: List of meetings is visible for superuser
    Given admin's request logged user is admin user
    When admin's page /users/meeting is requested
    Then admin's response status code is 200
    And admin's response page contains <a href="/users/meeting/">Spotkania pełnomocników</a>
    And admin's response page contains Dodaj spotkanie pełnomocników
