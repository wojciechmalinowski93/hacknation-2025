@elasticsearch
Feature: Organizations API

  Scenario Outline: Filtering institutions by type
    Given institutions of type {"local": 3, "state": 3, "other": 3}
    When api request path is <request_path>
    Then api request param <req_param_name> is <req_param_value>
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | request_path       | req_param_name | req_param_value | resp_body_field                      | resp_body_value |
    | /1.0/institutions/ | type           | local           | /data/*/attributes/institution_type  | local           |
    | /1.0/institutions/ | type           | state           | /data/*/attributes/institution_type  | state           |
    | /1.0/institutions/ | type           | other           | /data/*/attributes/institution_type  | other           |

    | /1.4/institutions/ | type           | local           | /data/*/attributes/institution_type  | local           |
    | /1.4/institutions/ | type           | state           | /data/*/attributes/institution_type  | state           |
    | /1.4/institutions/ | type           | other           | /data/*/attributes/institution_type  | other           |

  Scenario Outline: Institution on list contains required fields
    Given 3 institutions
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response body has field /data/*/attributes/abbreviation
    And api's response body has field /data/*/attributes/description
    And api's response body has field /data/*/attributes/electronic_delivery_address
    And api's response body has field /data/*/attributes/notes
    And api's response body has field /data/*/attributes/sources
    And api's response body has field /data/*/relationships/datasets/meta/count
    And api's response body has field /data/*/relationships/datasets/links/related
    And api's response body has field /data/*/relationships/resources/meta/count

    Examples:
    | request_path       |
    | /1.0/institutions/ |
    | /1.4/institutions/ |

    Scenario Outline: Institution without datasets returns data in relationship
      Given institution created with params {"id": 1000, "title": "test institution", "slug": "test-institution"}
      When api request path is <request_path>
      Then send api request and fetch the response
      And api's response body field /data/relationships/datasets/meta/count is 0
      And api's response body field /data/relationships/datasets/links/related endswith institutions/1000,test-institution/datasets

        Examples:
    | request_path       |
    | /1.0/institutions/1000 |
    | /1.4/institutions/1000 |

    Scenario Outline: Institutions datasets relationship has proper object urls
      Given institution created with params {"id": 1000, "title": "test institution", "slug": "test-institution"}
      And institution with id 1001 and title is another test institution and slug is another-test-institution
      When api request path is <request_path>
      Then send api request and fetch the response
      And api's response body field /data/0/relationships/datasets/links/related endswith institutions/1000,test-institution/datasets
      And api's response body field /data/0/relationships/datasets/meta/count is 0
      And api's response body field /data/1/relationships/datasets/links/related endswith institutions/1001,another-test-institution/datasets
      And api's response body field /data/1/relationships/datasets/meta/count is 0

        Examples:
    | request_path       |
    | /1.0/institutions/?sort=id |
    | /1.4/institutions/?sort=id |
