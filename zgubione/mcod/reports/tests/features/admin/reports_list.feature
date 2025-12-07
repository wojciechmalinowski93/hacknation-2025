Feature: Reports list

  Scenario: Reports subpage is available for admin
    Given admin's request logged user is admin user
    When admin's page /reports/ is requested
    Then admin's response status code is 200
    And admin's response page contains Raporty: administracja

  Scenario Outline: Reports subpage is not available for some user roles
    Given admin's request logged user is <user_type>
    When admin's page /reports/ is requested
    Then admin's response status code is 404
    Examples:
    | user_type        |
    | academy admin    |
    | laboratory admin |
    | editor user      |

  Scenario: Organization reports list is available for admin
    Given admin's request logged user is admin user
    And organizationreport created with params {"id": 999, "file": "/media/reports/organizations/organizations.csv"}
    When admin's page /reports/organizationreport/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz raport instytucji do zmiany
    And admin's response page contains /media/reports/organizations/organizations.csv
    # next line tests dal_admin_filters widget.
    And admin's response page contains data-placeholder="Zlecone przez"

  Scenario: Organization reports list with filtered results
    Given admin's request logged user is admin user
    And editor user with id 999
    And organizationreport created with params {"id": 999, "ordered_by_id": 999, "file": "/media/reports/organizations/organizations.csv"}
    When admin's page /reports/organizationreport/?created__gte=&created__lte=&ordered_by__id__exact=999 is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz raport instytucji do zmiany
    And admin's response page contains /media/reports/organizations/organizations.csv

  Scenario: User reports list is available for admin
    Given admin's request logged user is admin user
    And userreport created with params {"id": 999, "file": "/media/reports/users/users.csv"}
    When admin's page /reports/userreport/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz raport użytkownika do zmiany
    And admin's response page contains /media/reports/users/users.csv
    # next line tests dal_admin_filters widget.
    And admin's response page contains data-placeholder="Zlecone przez"

  Scenario: Resource reports list is available for admin
    Given admin's request logged user is admin user
    And resourcereport created with params {"id": 999, "file": "/media/reports/resources/resources.csv"}
    When admin's page /reports/resourcereport/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz raport zasobów do zmiany
    And admin's response page contains /media/reports/resources/resources.csv
    # next line tests dal_admin_filters widget.
    And admin's response page contains data-placeholder="Zlecone przez"

  Scenario: Dataset reports list is available for admin
    Given admin's request logged user is admin user
    And datasetreport created with params {"id": 999, "file": "/media/reports/datasets/datasets.csv"}
    When admin's page /reports/datasetreport/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz raport zbioru danych do zmiany
    And admin's response page contains /media/reports/datasets/datasets.csv
    # next line tests dal_admin_filters widget.
    And admin's response page contains data-placeholder="Zlecone przez"

  Scenario: Summary daily reports list is available for admin
    Given admin's request logged user is admin user
    And summarydailyreport created with params {"id": 999, "file": "media/reports/daily/Zbiorczy_raport_dzienny_2021_05_21_0400.csv"}
    When admin's page /reports/summarydailyreport/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz zbiorczy raport dzienny do zmiany
    And admin's response page contains Generuj raport
    And admin's response page contains /media/reports/daily/Zbiorczy_raport_dzienny_2021_05_21_0400.csv
    # next line tests dal_admin_filters widget.
    And admin's response page contains data-placeholder="Zlecone przez"

  Scenario: Monitoring reports list is available for admin
    Given admin's request logged user is admin user
    And monitoringreport created with params {"id": 999, "file": "/media/reports/suggestions/suggestions.csv"}
    When admin's page /reports/monitoringreport/ is requested
    Then admin's response status code is 200
    And admin's response page contains Wybierz zgłoszenia do zmiany
    And admin's response page contains /media/reports/suggestions/suggestions.csv
    # next line tests dal_admin_filters widget.
    And admin's response page contains data-placeholder="Zlecone przez"

  Scenario Outline: Monitoring reports list is not available for some user roles
    Given admin's request logged user is <user_type>
    When admin's page <page_url> is requested
    Then admin's response status code is 403
    Examples:
    | user_type        | page_url                     |

    | academy admin    | /reports/userreport/         |
    | laboratory admin | /reports/userreport/         |
    | editor user      | /reports/userreport/         |

    | academy admin    | /reports/organizationreport/ |
    | laboratory admin | /reports/organizationreport/ |
    | editor user      | /reports/organizationreport/ |

    | academy admin    | /reports/resourcereport/     |
    | laboratory admin | /reports/resourcereport/     |
    | editor user      | /reports/resourcereport/     |

    | academy admin    | /reports/datasetreport/      |
    | laboratory admin | /reports/datasetreport/      |
    | editor user      | /reports/datasetreport/      |

    | academy admin    | /reports/summarydailyreport/ |
    | laboratory admin | /reports/summarydailyreport/ |
    | editor user      | /reports/summarydailyreport/ |

    | academy admin    | /reports/monitoringreport/   |
    | laboratory admin | /reports/monitoringreport/   |
    | editor user      | /reports/monitoringreport/   |

  Scenario: Admin can generate daily report
    Given admin's request logged user is admin user
    And monitoringreport created with params {"id": 999}
    When admin's page /reports/summarydailyreport/generate_daily_report is requested
    Then admin's response status code is 200
    And admin's response page contains Zadanie wygenerowania raportu zostało zlecone. Raport może pojawić się z opóźnieniem...
