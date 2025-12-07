@elasticsearch
Feature: Dashboard view
  Scenario: Query subscription is visible in dashboard.
    Given logged admin user
    And admin has query subscription with id 100 for url google.com as xxx
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/aggregations/subscriptions/queries is 1

  Scenario: Dataset subscription is visible in dashboard.
    Given logged active user
    And subscription with id 999 of dataset with id 10 as yyy
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /meta/aggregations/subscriptions/datasets is 1

  Scenario Outline: Academy courses' states in dashboard have correct counts.
    Given logged admin user
    And <planned> planned academy courses
    And <current> current academy courses
    And <finished> finished academy courses
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And dashboard api's response planned courses is <planned>
    And dashboard api's response current courses is <current>
    And dashboard api's response finished courses is <finished>

    Examples:
    | planned | current | finished |
    | 0       | 0       | 0        |
    | 10      | 0       | 0        |
    | 0       | 10      | 0        |
    | 0       | 0       | 10       |
    | 5       | 5       | 0        |
    | 0       | 5       | 5        |
    | 5       | 5       | 5        |

  Scenario Outline: LOD aggregations in Dashboard API.
    Given logged admin user
    And <researches> laboratory researches
    And <analyses> laboratory analyses
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And dashboard api's response laboratory researches is <researches>
    And dashboard api's response laboratory analyses is <analyses>

    Examples:
    | researches | analyses |
    | 0          | 0        |
    | 10         | 0        |
    | 5          | 5        |
    | 0          | 10       |

  Scenario: Ordinary active user sees only LOD data and subscriptions in dashboard.
    Given logged active user
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has no field /meta/aggregations/academy
    And api's response body has field /meta/aggregations/lab
    And api's response body has field /meta/aggregations/subscriptions

  Scenario: AOD admin sees AOD, LOD and subscription data in dashboard.
    Given logged academy admin
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggregations/academy
    And api's response body has field /meta/aggregations/lab
    And api's response body has field /meta/aggregations/subscriptions

  Scenario: LOD admin sees AOD, LOD and subscriptions data in dashboard.
    Given logged laboratory admin
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggregations/academy
    And api's response body has field /meta/aggregations/lab
    And api's response body has field /meta/aggregations/subscriptions

  Scenario Outline: Official user/Agent user sees AOD, LOD and subscriptions data in dashboard.
    Given logged <user_type>
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggregations/academy
    And api's response body has field /meta/aggregations/lab
    And api's response body has field /meta/aggregations/subscriptions

    Examples:
    | user_type     |
    | official user |
    | agent user    |

  Scenario: Staff/editor user sees AOD, LOD and subscriptions data in dashboard.
    Given logged editor user
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggregations/academy
    And api's response body has field /meta/aggregations/lab
    And api's response body has field /meta/aggregations/subscriptions

  Scenario: Aggregated suggestions data are not visible for active normal user.
    Given logged active user
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has no field /meta/aggregations/suggestions

  Scenario Outline: Aggregated suggestions data are visible for admin, editor and agent users.
    Given logged <user_type>
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggregations/suggestions/active
    And api's response body has field /meta/aggregations/suggestions/inactive

    Examples:
    | user_type   |
    | admin user  |
    | editor user |
    | agent user  |

#  Scenario Outline: Aggregated meetings data are visible for admin and agent users.
#    Given logged <user_type>
#    When api request path is /auth/user/dashboard
#    And send api request and fetch the response
#    Then api's response status code is 200
#    And api's response body has field /meta/aggregations/meetings/finished
#    And api's response body has field /meta/aggregations/meetings/planned
#
#    Examples:
#    | user_type  |
#    | admin user |
#    | agent user |

  Scenario: Analytical tools and cms url are visible for admin
    Given logged admin user
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field /meta/aggregations/analytical_tools
    And api's response body has field /meta/aggregations/cms_url

  Scenario Outline: Analytical tools and cms url are not visible for non admin user
    Given logged <user_type>
    When api request path is /auth/user/dashboard
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has no field /meta/aggregations/analytical_tools
    And api's response body has no field /meta/aggregations/cms_url

    Examples:
    | user_type        |
    | editor user      |
    | agent user       |
    | active user      |
    | laboratory admin |
    | academy admin    |
