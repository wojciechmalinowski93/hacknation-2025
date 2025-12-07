@elasticsearch
Feature: Search suggestions

  Scenario: Invalid value of max_length parameter returns proper error message in response
    Given resource with id 999 and title is Test search suggestion resource 999
    And resource with id 998 and title is Test search suggestion resource 998
    When api request path is /search/suggest/?q=suggestion&models=resource&per_model=2&max_length=101
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is Invalid maximum list length

  Scenario: Invalid value of models parameter returns proper error message in response
    Given resource with id 999 and title is test
    When api request path is /search/suggest/?models=INVALID
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/detail is Wprowadzony model - INVALID, nie jest wspierany

  Scenario: Published dataset is visible as suggestion
    Given dataset created with params {"id": 999, "title": "dataset's suggestion"}
    When api request path is /search/suggest/?models=dataset&q=dataset's suggestion
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes/title is dataset's suggestion

  Scenario: Draft dataset is not visible as suggestion
    Given dataset created with params {"id": 999, "title": "dataset's suggestion", "status": "draft"}
    When api request path is /search/suggest/?models=dataset&q=dataset's suggestion
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response data has length 0

  Scenario: Unpublished dataset is not visible as suggestion
    Given dataset created with params {"id": 999, "title": "dataset's suggestion"}
    When change status to draft for dataset with id 999
    And api request path is /search/suggest/?models=dataset&q=dataset's suggestion
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response data has length 0

  Scenario: Unpublished resources regions are not visible as suggestion
    Given dataset with id 998
    And draft resource with id 111 dataset id 998 and single main region
    When api request path is /search/suggest/?models=region&q=Warsz
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response data has length 0

  Scenario: Restored from draft resources regions are visible as suggestion
    Given dataset with id 998
    And draft resource with id 111 dataset id 998 and single main region
    And set status to published on resource with id 111
    When api request path is /search/suggest/?models=region&q=Warsz
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response data has length 1

  Scenario Outline: Changed to draft resource deletes proper regions from suggestion
    Given dataset with id 998
    And resource with id 112 dataset id 998 and wroclaw main region
    And set status to draft on resource with id 112
    When api request path is <request_path>
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response data has length <number>

    Examples:
    | request_path                                            | number |
    | /1.4/search/suggest/?models=region&q=Polsk&per_model=1  | 1      |
    | /1.4/search/suggest/?models=region&q=Wroc &per_model=1  | 0      |
