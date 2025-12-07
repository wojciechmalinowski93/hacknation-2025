@elasticsearch
Feature: Resources list API

  Scenario Outline: Test resources list contains required information
    Given 3 resources
    When api request path is <request_path>
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/[0]/attributes has fields created,data_date,description,format,modified,openness_score,title,verified,visualization_types,supplements

    Examples:
      | request_path    |
      | /resources/     |
      | /1.0/resources/ |
      | /1.4/resources/ |


  Scenario: Test resources list contains resource ident in links section in API 1.4
    Given resource with id 999 and slug is resource-test-slug
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/[0]/links/self endswith 999,resource-test-slug

  Scenario: Test resources list data field is empty list if no results in API 1.4
    Given 3 resources
    When api request path is /1.4/resources/?q=noresultsfound
    And send api request and fetch the response
    Then api's response body field data is []

  Scenario: Test resources list is sorted by views_count ascendingly in API 1.0
    Given 3 resources
    When api request path is /1.0/resources/
    Then api request param sort is views_count
    And send api request and fetch the response
    And api's response status code is 200
    And api's response list is sorted by views_count ascendingly

  Scenario: Test resources list is sorted by views_count ascendingly in API 1.4
    Given 3 resources
    When api request path is /1.4/resources/
    Then api request param sort is views_count
    And send api request and fetch the response
    And api's response status code is 200
    And api's response list is sorted by views_count ascendingly

  Scenario: Test resources list is sorted by views_count descendingly in API 1.0
    Given 3 resources
    When api request path is /1.0/resources/
    Then api request param sort is -views_count
    And send api request and fetch the response
    And api's response status code is 200
    And api's response list is sorted by views_count descendingly

  Scenario: Test resources list is sorted by views_count descendingly in API 1.4
    Given 3 resources
    When api request path is /1.4/resources/
    Then api request param sort is -views_count
    And send api request and fetch the response
    And api's response status code is 200
    And api's response list is sorted by views_count descendingly

  Scenario Outline: Test resources can be filtered by resource visualization type in API 1.0
    Given resource with buzzfeed file
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    Examples:
      | request_path                            | number |
      | /1.0/resources?visualization_type=chart | 0      |
      | /1.0/resources?visualization_type=geo   | 0      |
      | /1.0/resources?visualization_type=table | 1      |
      | /1.0/resources?visualization_type=na    | 0      |


  Scenario Outline: Test resources can be filtered by resource visualization type in API 1.4
    Given resource with buzzfeed file
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    Examples:
      | request_path                            | number |
      | /1.4/resources?visualization_type=chart | 0      |
      | /1.4/resources?visualization_type=geo   | 0      |
      | /1.4/resources?visualization_type=table | 1      |
      | /1.4/resources?visualization_type=na    | 0      |

  Scenario Outline: Test resources can be filtered by resource type
    Given resource with buzzfeed file
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    Examples:
      | request_path                | number |
      | /1.0/resources?type=website | 0      |
      | /1.0/resources?type=api     | 0      |
      | /1.0/resources?type=file    | 1      |
      | /1.4/resources?type=website | 0      |
      | /1.4/resources?type=api     | 0      |
      | /1.4/resources?type=file    | 1      |

  Scenario Outline: Test resources can be filtered by created
    Given three resources with created dates in 2018-02-02T10:00:00Z|2019-02-02T10:00:00Z|2020-02-02T10:00:00Z
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    Examples:
      | request_path                                             | number |
      | /resources                                               | 3      |
      | /resources?created[gte]=2019-01-01                       | 2      |
      | /resources?created[gte]=2020-01-01                       | 1      |
      | /resources?created[gte]=2021-01-01                       | 0      |
      | /resources?created[lt]=2021-01-01                        | 3      |
      | /resources?created[lt]=2020-01-01                        | 2      |
      | /resources?created[lt]=2019-01-01                        | 1      |
      | /resources?created[lt]=2018-01-01                        | 0      |
      | /resources?created[gt]=2019-01-01&created[lt]=2020-01-01 | 1      |

  Scenario Outline: Test resources can be filtered by language
    Given <object_type> created with params <params>
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    And api's response body has field data/[0]/attributes/language
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
      | object_type | params                        | request_path                                                   | number | resp_body_field                         | resp_body_value |
      | resource    | {"id": 999, "language": "en"} | /resources?language=en&id=999&facet[terms]=by_language         | 1      | meta/aggregations/by_language/[0]/title | angielski       |
      | resource    | {"id": 999, "language": "pl"} | /resources?language=pl&id=999&facet[terms]=by_language         | 1      | meta/aggregations/by_language/[0]/title | polski          |
      | resource    | {"id": 999, "language": "en"} | /resources?language=en&id=999&facet[terms]=by_language&lang=en | 1      | meta/aggregations/by_language/[0]/title | English         |
      | resource    | {"id": 999, "language": "pl"} | /resources?language=pl&id=999&facet[terms]=by_language&lang=en | 1      | meta/aggregations/by_language/[0]/title | Polish          |

  Scenario Outline: Test listing endpoints returns empty list if no results in API 1.4
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response body field data is []
    Examples:
      | request_path                       |
      | /1.4/showcases?q=noresultsfound    |
      | /1.4/datasets?q=noresultsfound     |
      | /1.4/histories?q=noresultsfound    |
      | /1.4/institutions?q=noresultsfound |
      | /1.4/resources?q=noresultsfound    |

  Scenario: Test resource file size is properly returned (3.9GiB)
    Given resource created with params {"id": 999, "file_size": 4156328079}
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/[0]/attributes/file_size is 4156328079

  Scenario: Test xls resource converted to csv on resources list
    Given resource with id 999 and xls file converted to csv
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then api's response body field data/[0]/attributes/file_url endswith example_xls_file.xls
    And api's response body field data/[0]/attributes/csv_file_url endswith example_xls_file.csv
    And api's response body field data/[0]/attributes/csv_file_size is not None
    And api's response body field data/[0]/attributes/csv_download_url is not None

  Scenario: Test csv resource converted to jsonld on resources list
    Given resource with csv file converted to jsonld with params {"id": 999}
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then api's response body field data/[0]/attributes/file_url endswith csv2jsonld.csv
    And api's response body field data/[0]/attributes/jsonld_file_url endswith csv2jsonld.jsonld
    And api's response body field data/[0]/attributes/jsonld_file_size is not None
    And api's response body field data/[0]/attributes/jsonld_download_url is not None
    And api's response body field data/[0]/attributes/openness_score is 4

  Scenario: Test incrementing resource views count updates data in ES
    Given dataset with id 999
    And resource created with params {"id": 998, "slug": "test-rdf", "dataset_id": 999, "views_count": 0, "status": "published"}
    And resource with id 998 is viewed and counter incrementing task is executed
    When api request header x-api-version is 1.0
    And api request path is /1.4/datasets/999/resources/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/0/attributes/views_count is 1

  Scenario: Resource's region is returned by ES api
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then has assigned Polska,Warszawa as name for regions
    And has assigned 85633723,101752777 as region_id for regions
