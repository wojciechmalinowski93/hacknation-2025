@elasticsearch
Feature: Change resource in admin panel

  Scenario: Change of resource regions updates regions in db
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 998, "data_date": "22.05.2020", "status": "published", "regions": ["0005084", "0918123"], "_continue":""}
    And admin's page with mocked geo api /resources/resource/999/change/ is requested
    Then admin's response status code is 200
    And resource has assigned main and additional regions
    And admin's response page form contains Warszawa and Wólka Kosowska

  @feat_dga
  Scenario: Confirm updating DGA Resource in the presence of an existing DGA Resource
    Given dataset with pk 998 containing dga resource with pk 999
    And DGA compliant resource with pk 1000 in dataset with pk 998
    When admin's request method is POST
    And admin's request posted resource data is {"contains_protected_data": "True", "title": "test", "description": "more than 20 characters", "dataset": 998, "data_date": "22.05.2020", "status": "published"}
    And admin's page /resources/resource/1000/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz, aby to był aktualny wykaz chronionych danych?
    When admin confirms saving the resource with posted data
    Then admin's response page contains /change/">test</a>" został pomyślnie zmieniony.
    And resource with id 999 is not DGA
    And resource with id 1000 is DGA

  @feat_dga
  Scenario: Confirmation pops up when the Resource is deselected as DGA and the Resource is updated
    Given dataset with pk 998 containing dga resource with pk 999
    When admin's request method is POST
    And admin's request posted resource data is {"contains_protected_data": "False", "title": "test", "description": "more than 20 characters", "dataset": 998, "data_date": "22.05.2020", "status": "published"}
    And admin's page /resources/resource/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz odznaczyć metadaną "Zawiera wykaz chronionych danych"?
    When admin confirms saving the resource with posted data
    Then admin's response page contains /change/">test</a>" został pomyślnie zmieniony.
    And resource with id 999 does not contain protected data

  @feat_dga
  Scenario: Confirmation pops up when marking a DGA Resource as Draft and the Resource is updated
    Given dataset with pk 998 containing dga resource with pk 999
    When admin's request method is POST
    And admin's request posted resource data is {"status": "draft", "contains_protected_data": "True", "title": "test", "description": "more than 20 characters", "dataset": 998, "data_date": "22.05.2020"}
    And admin's page /resources/resource/999/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz zmienić status zasobu z "Opublikowany" na "Szkic"?
    When admin confirms saving the resource with posted data
    Then admin's response page contains /change/">test</a>" został pomyślnie zmieniony.
    And resource with id 999 is draft

  @periodic_task
  Scenario: Auto data date with end date can be set on resource with type api
    Given dataset with id 990
    And draft remote file resource of api type with id 986
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "True", "data_date": "22.05.2022","automatic_data_date_start": "22.05.2022", "data_date_update_period": "daily", "automatic_data_date_end": "24.05.2022"}
    And admin's page /resources/resource/986/change/ is requested
    Then admin's response status code is 200
    And resource with id 986 has periodic task with interval schedule
    And Periodic task for resource with id 986 has last_run_at attr set

  @periodic_task
  Scenario: Auto data date without end date can be set on resource with type api
    Given dataset with id 990
    And draft remote file resource of api type with id 987
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "True", "data_date": "22.05.2022", "automatic_data_date_start": "22.05.2022", "data_date_update_period": "monthly", "endless_data_date_update": "True"}
    And admin's page /resources/resource/987/change/ is requested
    Then admin's response status code is 200
    And resource with id 987 has periodic task with crontab schedule

  @periodic_task
  Scenario: Auto data date without end date can be set on resource with type website
    Given dataset with id 990
    And resource of type website with id 988
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "True", "data_date": "22.05.2022", "automatic_data_date_start": "22.05.2022", "data_date_update_period": "weekly", "endless_data_date_update": "True"}
    And admin's page /resources/resource/988/change/ is requested
    Then admin's response status code is 200
    And resource with id 988 has periodic task with interval schedule

  @periodic_task
  Scenario: Data date update can be canceled by is manual data date checkbox
    Given dataset with id 990
    And resource with status published and data date update periodic task with interval schedule
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "False", "data_date": "22.05.2022", "automatic_data_date_start": "22.05.2022", "data_date_update_period": "monthly", "endless_data_date_update": "True"}
    And 'mcod.resources.admin.ResourceAdmin' edition page is requested for created object
    Then admin's response status code is 200
    And created resource has no data date periodic task

  @periodic_task
  Scenario: Data date update can be canceled by setting status to draft
    Given dataset with id 990
    And resource with id 997 and status published and data date update periodic task with interval schedule
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "draft", "is_auto_data_date": "True", "data_date": "22.05.2022", "automatic_data_date_start": "22.05.2022", "data_date_update_period": "monthly", "endless_data_date_update": "True"}
    And admin's page /resources/resource/997/change/ is requested
    Then admin's response status code is 200
    And resource with id 997 has no data date periodic task

  @periodic_task
  Scenario: Data date update task can be changed from interval to crontab schedule
    Given dataset with id 990
    And resource with status published and data date update periodic task with interval schedule
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "True", "data_date": "22.05.2022", "automatic_data_date_start": "22.05.2022", "data_date_update_period": "monthly", "endless_data_date_update": "True"}
    And 'mcod.resources.admin.ResourceAdmin' edition page is requested for created object
    Then admin's response status code is 200
    And created resource has periodic task with crontab schedule

  @periodic_task
  Scenario: Auto data date with end date can be set on resource with remote file
    Given dataset with id 990
    And remote file resource with id 1001
    And update link of remote file resource with id '1001'
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test remote file", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "True", "data_date": "22.05.2022","automatic_data_date_start": "22.05.2022", "data_date_update_period": "daily", "automatic_data_date_end": "24.05.2022"}
    And admin's page /resources/resource/1001/change/ is requested
    Then admin's response status code is 200
    And resource with id 1001 has periodic task with interval schedule
    And Periodic task for resource with id 1001 has last_run_at attr set

  @periodic_task
  Scenario: End of month data date update correctly updates next scheduled update date
    Given dataset with id 990
    And draft remote file resource of api type with id 986
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test", "description": "more than 20 characters", "dataset": 990, "status": "published", "is_auto_data_date": "True", "data_date": "31.05.2022", "automatic_data_date_start": "31.05.2022", "data_date_update_period": "monthly", "endless_data_date_update": "True"}
    And admin's page /resources/resource/986/change/ is requested
    Then admin's response status code is 200
    And resource with id 986 has periodic task with crontab schedule
    And crontab schedule for resource with id 986 has current month last day set up as run date
