@elasticsearch
Feature: Datasets list API

  Scenario: Test datasets list does not contain included section by default in API 1.4
    Given dataset with id 999 and 3 resources
    When api request path is /1.4/datasets/
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has no field included

  Scenario: Test datasets list contains included section in API 1.4
    Given dataset with id 999 and 3 resources
    When api request path is /1.4/datasets/
    And api request param include is institution
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has field included

  Scenario: Test number of returned datasets is the same in API 1.0 and API 1.4
    Given dataset with title unikalny_tytuł and 3 resources
    When api request path is /1.0/datasets/
    And api request param q is unikalny_tytuł
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field /meta/count is 1
    Then api request path is /1.4/datasets/
    And api request param q is unikalny_tytuł
    And send api request and fetch the response
    And api's response body field /meta/count is 1

  Scenario: Test datasets list elements contain valid links to related items
    Given 3 datasets with 3 resources
    When api request path is /1.4/datasets/
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response datasets contain valid links to related resources

  Scenario: Test dataset openness scores contains scores only from related resources that are published
    Given dataset with id 10001
    And resource with example.html file, dataset_id 10001 and id 20000
    And resource with example.txt file, dataset_id 10001 and id 20001
    When api request path is /1.4/datasets/10001
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/attributes/openness_scores is [1, 3]
    Then set status to draft on resource with id 20000
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/attributes/openness_scores is [1]

  Scenario Outline: Test datasets list is filtered by openness_scores
    Given dataset with id 999
    And resource created with params {"id": 999, "dataset_id": 999, "openness_score": 3}
    When api request path is <request_path>
    And api request param <req_param_name> is <req_param_value>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body list <field_name> contains <field_value>

    Examples:
    | request_path  | req_param_name  | req_param_value | field_name                         | field_value |
    | /1.0/datasets | openness_score  | 3               | /data/*/attributes/openness_scores | 3           |
    | /1.4/datasets | openness_score  | 3               | /data/*/attributes/openness_scores | 3           |

  Scenario Outline: Test datasets list can be sorted
    Given 3 datasets
    When api request language is pl
    And api request path is <request_path>
    And api request param per_page is 100
    And api request param <req_param_name> is <req_param_value>
    Then send api request and fetch the response
    And datasets list in response is sorted by <sort>

    Examples:
    | request_path  | req_param_name | req_param_value | sort                    |
    | /1.0/datasets | sort           | created         | created                 |
    | /1.0/datasets | sort           | -created        | -created                |
    | /1.0/datasets | sort           | id              | id                      |
    | /1.0/datasets | sort           | -id             | -id                     |
    | /1.0/datasets | sort           | modified        | modified                |
    | /1.0/datasets | sort           | -modified       | -modified               |
    | /1.0/datasets | sort           | title           | title.pl.sort           |
    | /1.0/datasets | sort           | -title          | -title.pl.sort          |
    | /1.0/datasets | sort           | verified        | verified                |
    | /1.0/datasets | sort           | -verified       | -verified               |
    | /1.0/datasets | sort           | views_count     | views_count             |
    | /1.0/datasets | sort           | -views_count    | -views_count            |

    | /1.4/datasets | sort           | created         | created                 |
    | /1.4/datasets | sort           | -created        | -created                |
    | /1.4/datasets | sort           | id              | id                      |
    | /1.4/datasets | sort           | -id             | -id                     |
    | /1.4/datasets | sort           | modified        | modified                |
    | /1.4/datasets | sort           | -modified       | -modified               |
    | /1.4/datasets | sort           | title           | title.pl.sort           |
    | /1.4/datasets | sort           | -title          | -title.pl.sort          |
    | /1.4/datasets | sort           | verified        | verified                |
    | /1.4/datasets | sort           | -verified       | -verified               |
    | /1.4/datasets | sort           | views_count     | views_count             |
    | /1.4/datasets | sort           | -views_count    | -views_count            |

  Scenario Outline: Test filtering of datasets by unknown visualization_type returns empty list
    Given dataset with tabular resource
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 0

    Examples:
    | request_path                                |
    | /1.0/datasets?visualization_types=na        |
    | /1.4/datasets?visualization_types=na        |
    | /1.4/datasets?visualization_types[terms]=na |

  Scenario Outline: Test datasets with local file resources can be filtered by resource visualization types
    Given dataset with local file resource
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body list /data/*/attributes/visualization_types contains any from <values>

    Examples:
      | request_path                                             | values          |
      | /1.4/datasets?visualization_types=table                  | table           |
      | /1.4/datasets?visualization_types[terms]=table           | table           |
      | /1.4/datasets?visualization_types=chart                  | chart           |

  Scenario Outline: Test datasets with remote file resources doesn't show when filtering by resource visualization types
    Given dataset with remote file resource
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data is []

    Examples:
      | request_path                                             |
      | /1.4/datasets?visualization_types=table                  |
      | /1.4/datasets?visualization_types[terms]=table           |
      | /1.4/datasets?visualization_types=chart                  |

  Scenario Outline: Test datasets can be filtered by resource types
    Given resource of type website
    And resource of type api
    And resource with buzzfeed file
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body list /data/*/attributes/types contains any from <values>

    Examples:
    | request_path                           | values      |
    | /1.0/datasets?types=website            | website     |
    | /1.0/datasets?types=api                | api         |
    | /1.0/datasets?types=file               | file        |

    | /1.4/datasets?types=website            | website     |
    | /1.4/datasets?types=api                | api         |
    | /1.4/datasets?types=file               | file        |
    | /1.4/datasets?types[terms]=file        | file        |
    | /1.4/datasets?types[terms]=api,website | website,api |

  Scenario Outline: Test datasets can be filtered by created in API 1.4
    Given three datasets with created dates in 2018-02-02T10:00:00Z|2019-02-02T10:00:00Z|2020-02-02T10:00:00Z
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    Examples:
      | request_path                                            | number |
      | /datasets                                               | 3      |
      | /datasets?created[gte]=2019-01-01                       | 2      |
      | /datasets?created[gte]=2020-01-01                       | 1      |
      | /datasets?created[gte]=2021-01-01                       | 0      |
      | /datasets?created[lt]=2021-01-01                        | 3      |
      | /datasets?created[lt]=2020-01-01                        | 2      |
      | /datasets?created[lt]=2019-01-01                        | 1      |
      | /datasets?created[lt]=2018-01-01                        | 0      |
      | /datasets?created[gt]=2019-01-01&created[lt]=2020-01-01 | 1      |

  Scenario: Related resources regions are assigned to dataset
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    When api request path is /1.4/datasets/?id=998
    And send api request and fetch the response
    Then api's response body field data/[0]/attributes/regions/[0]/name is Polska
    And api's response body field data/[0]/attributes/regions/[0]/region_id is 85633723
    And api's response body field data/[0]/attributes/regions/[1]/name is Warszawa
    And api's response body field data/[0]/attributes/regions/[1]/region_id is 101752777

  Scenario: Dataset without regions has poland as assigned region
    Given dataset with id 999 and 3 resources
    When api request path is /1.4/datasets/?id=999
    And send api request and fetch the response
    Then api's response body field data/[0]/attributes/regions/[0]/name is Polska
    And api's response body field data/[0]/attributes/regions/[0]/region_id is 85633723

  Scenario Outline: Datasets resource relationship has proper object urls
      Given dataset created with params {"id": 1000, "title": "test dataset", "slug": "test-dataset"}
      And dataset with id 1001 and title is another test dataset and slug is another-test-dataset
      When api request path is <request_path>
      Then send api request and fetch the response
      And api's response body field /data/0/relationships/resources/links/related endswith datasets/1000,test-dataset/resources
      And api's response body field /data/0/relationships/resources/meta/count is 0
      And api's response body field /data/1/relationships/resources/links/related endswith datasets/1001,another-test-dataset/resources
      And api's response body field /data/1/relationships/resources/meta/count is 0

    Examples:
    | request_path           |
    | /1.0/datasets/?sort=id |
    | /1.4/datasets/?sort=id |

  Scenario: Promoted datasets on list
    Given dataset created with params {"id": 998, "is_promoted": true}
    And dataset with id 999
    When api request path is /datasets/?sort=-created
    And send api request and fetch the response
    Then api's response body field data/[0]/id is 998
    And api's response body field data/[0]/attributes/is_promoted is True
