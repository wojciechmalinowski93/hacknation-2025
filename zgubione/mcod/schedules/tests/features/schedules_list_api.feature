Feature: Schedules list API
  Scenario Outline: Schedule notifications list endpoint is not accessible for active user
    Given logged active user
    When api request language is <lang_code>
    And api request path is /auth/schedule_notifications
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | lang_code | resp_body_field   | resp_body_value                      |
    | en        | errors/[0]/detail | Additional permissions are required! |
    | pl        | errors/[0]/detail | Wymagane są dodatkowe uprawnienia!   |

  Scenario Outline: Some endpoints are accessible by admin and agent users only
    Given logged <user_type>
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "notification_id": 999}
    When api request path is <request_path>
    # the next line is added to disable json api validation of response during tests of CSV, XLSX responses.
    And api request header x-api-version is 1.0
    Then send api request and fetch the response
    And api's response status code is <status_code>

    Examples:
    | user_type   | request_path                            | status_code |

    | admin user  | /auth/schedule_agents                   | 200         |
    | agent user  | /auth/schedule_agents                   | 403         |
    | active user | /auth/schedule_agents                   | 403         |

    | admin user  | /auth/schedule_notifications            | 200         |
    | agent user  | /auth/schedule_notifications            | 200         |
    | active user | /auth/schedule_notifications            | 403         |

    | admin user  | /auth/schedule_notifications/999        | 200         |
    | agent user  | /auth/schedule_notifications/999        | 200         |
    | active user | /auth/schedule_notifications/999        | 403         |

    | admin user  | /auth/schedules                         | 200         |
    | agent user  | /auth/schedules                         | 200         |
    | active user | /auth/schedules                         | 403         |

    | admin user  | /auth/schedules/999                     | 200         |
    | agent user  | /auth/schedules/999                     | 200         |
    | active user | /auth/schedules/999                     | 403         |
    | admin user  | /auth/schedules/999.csv                 | 200         |
    | agent user  | /auth/schedules/999.csv                 | 200         |
    | active user | /auth/schedules/999.csv                 | 403         |
    | admin user  | /auth/schedules/999.xlsx                | 200         |
    | agent user  | /auth/schedules/999.xlsx                | 200         |
    | active user | /auth/schedules/999.xlsx                | 403         |

    | admin user  | /auth/schedules/999/user_schedules      | 200         |
    | agent user  | /auth/schedules/999/user_schedules      | 200         |
    | active user | /auth/schedules/999/user_schedules      | 403         |

    | admin user  | /auth/schedules/999/user_schedule_items | 200         |
    | agent user  | /auth/schedules/999/user_schedule_items | 200         |
    | active user | /auth/schedules/999/user_schedule_items | 403         |

    | admin user  | /auth/user_schedules                    | 200         |
    | agent user  | /auth/user_schedules                    | 200         |
    | active user | /auth/user_schedules                    | 403         |
    | admin user  | /auth/user_schedules.csv                | 200         |
    | agent user  | /auth/user_schedules.csv                | 200         |
    | active user | /auth/user_schedules.csv                | 403         |
    | admin user  | /auth/user_schedules.xlsx               | 200         |
    | agent user  | /auth/user_schedules.xlsx               | 200         |
    | active user | /auth/user_schedules.xlsx               | 403         |

    | admin user  | /auth/user_schedule_items               | 200         |
    | agent user  | /auth/user_schedule_items               | 200         |
    | active user | /auth/user_schedule_items               | 403         |
    | admin user  | /auth/user_schedule_items.csv           | 200         |
    | agent user  | /auth/user_schedule_items.csv           | 200         |
    | active user | /auth/user_schedule_items.csv           | 403         |
    | admin user  | /auth/user_schedule_items.xlsx          | 200         |
    | agent user  | /auth/user_schedule_items.xlsx          | 200         |
    | active user | /auth/user_schedule_items.xlsx          | 403         |

    | admin user  | /auth/user_schedule_items/formats       | 200         |
    | agent user  | /auth/user_schedule_items/formats       | 200         |
    | active user | /auth/user_schedule_items/formats       | 403         |
    | admin user  | /auth/user_schedule_items/formats?debug=true | 200    |

  Scenario Outline: Specified endpoints returns related objects in included section for admin
    Given logged admin user
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "comment_id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has field included
    And api's response body included types contains <value>

    Examples:
    | request_path                                                                | value                               |
    | /auth/schedules?include=user_schedule,user_schedule_item                    | user_schedule,user_schedule_item    |
    | /auth/schedules/999?include=agent,user_schedule,user_schedule_item          | user,user_schedule,user_schedule_item |

    | /auth/user_schedules?include=schedule,user,user_schedule_item               | schedule,user,user_schedule_item    |
    | /auth/schedules/999/user_schedules?include=schedule,user,user_schedule_item | schedule,user,user_schedule_item    |
    | /auth/user_schedules/999?include=schedule,user,user_schedule_item           | schedule,user,user_schedule_item    |

    | /auth/user_schedule_items?include=comment,schedule,user,user_schedule       | comment,schedule,user,user_schedule |
    | /auth/user_schedules/999/items?include=comment,schedule,user,user_schedule  | comment,schedule,user,user_schedule |
    | /auth/user_schedule_items/999?include=comment,schedule,user,user_schedule   | comment,schedule,user,user_schedule |

    | /auth/schedule_agents?include=schedule,user_schedule,user_schedule_item     | schedule,user_schedule,user_schedule_item |

  Scenario Outline: Specified endpoints returns related objects in included section for agent
    Given institution with id 999
    And logged agent user created with {"id": 999, "agent_organizations": [999]}
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_id": 999, "user_schedule_item_id": 999, "comment_id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has field included
    And api's response body included types contains <value>

    Examples:
    | request_path                                                                | value                               |
    | /auth/schedules?include=user_schedule,user_schedule_item                    | user_schedule,user_schedule_item    |
    | /auth/schedules/999?include=user_schedule,user_schedule_item                | user_schedule,user_schedule_item    |

    | /auth/user_schedules?include=schedule,user,user_schedule_item               | schedule,user,user_schedule_item    |
    | /auth/schedules/999/user_schedules?include=schedule,user,user_schedule_item | schedule,user,user_schedule_item    |
    | /auth/user_schedules/999?include=schedule,user,user_schedule_item           | schedule,user,user_schedule_item    |

    | /auth/user_schedule_items?include=comment,schedule,user,user_schedule       | comment,schedule,user,user_schedule |
    | /auth/user_schedules/999/items?include=comment,schedule,user,user_schedule  | comment,schedule,user,user_schedule |
    | /auth/user_schedule_items/999?include=comment,schedule,user,user_schedule   | comment,schedule,user,user_schedule |

  Scenario Outline: Requests for export files returns link to tabular response
    Given logged <user_type>
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has field data/attributes/url

    Examples:
    | user_type   | request_path                   |
    | admin user  | /auth/schedules/999.csv        |
    | agent user  | /auth/schedules/999.csv        |
    | admin user  | /auth/schedules/999.xlsx       |
    | agent user  | /auth/schedules/999.xlsx       |

    | admin user  | /auth/user_schedules.csv       |
    | agent user  | /auth/user_schedules.csv       |
    | admin user  | /auth/user_schedules.xlsx      |
    | agent user  | /auth/user_schedules.xlsx      |

    | admin user  | /auth/user_schedule_items.csv  |
    | agent user  | /auth/user_schedule_items.csv  |
    | admin user  | /auth/user_schedule_items.xlsx |
    | agent user  | /auth/user_schedule_items.xlsx |

  Scenario: Opening of new schedule is available for admin
    Given logged admin user
    When api request method is POST
    And api request path is /auth/schedules
    Then send api request and fetch the response
    And api's response status code is 201
    And api's response body field data/type is schedule
    And api's response body field data/attributes/state is planned

  Scenario: Opening of new schedule is not available for agent user
    Given logged agent user
    When api request method is POST
    And api request path is /auth/schedules
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field errors/[0]/detail is Wymagane są dodatkowe uprawnienia!

  Scenario: Opening of new schedule returns error if currently planned schedule contains awaiting items
    Given logged out agent user created with {"id": 999, "email": "test@dane.gov.pl"}
    And logged admin user
    And schedule data created with {"schedule_id": 999, "user_schedule_id": 999, "user_schedule_item_id": 999, "user_id": 999, "recommendation_state": "awaits"}
    When api request method is POST
    And api request path is /auth/schedules
    Then send api request and fetch the response
    And api's response status code is 403
    And api's response body field errors/[0]/title is Brak rekomendacji dla "test@dane.gov.pl"
