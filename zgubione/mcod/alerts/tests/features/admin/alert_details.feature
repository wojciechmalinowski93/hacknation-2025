Feature: Alert details
  Scenario: Change of alert
    Given logged admin user
    And alert created with params {"id": 999, "title": "Test alert"}
    When admin's request method is POST
    And admin's request posted alert data is {"title_pl": "Test alert", "start_date_0": "2022-01-01", "start_date_1": "00:00:00", "finish_date_0": "2050-02-01", "finish_date_1": "00:00:00"}
    And admin's page /alerts/alert/999/change/ is requested
    Then admin's response page contains Komunikat "<a href="/alerts/alert/999/change/">Test alert</a>" został pomyślnie zmieniony.
