@elasticsearch
Feature: Tabular data API
  Scenario: Test resource data sum aggregation
    Given resource with id 1000 and simple csv file
    When api request path is /1.4/resources/1000/data?sum=col1,col2,col3,col4
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response sum aggregation column col1 is 26
    And api's response sum aggregation column col2 is 22
    And api's response sum aggregation column col3 is 25
    And api's response sum aggregation column col4 is 24

  Scenario: Test listing
    Given I have buzzfeed resource with tabular data
    When I search in tabular data rows
    And api request header X-API-VERSION is 1.4
    And api request header Accept-Language is pl
    And api request param page is 1
    And api request param per_page is 25
    And send api request and fetch the response
    Then api's response status code is 200
    And all list items should be of type row
    And items count should be equal to 1000

  Scenario: Test filtering by keyword
    Given I have buzzfeed resource with tabular data
    When resource api tabular data endpoint is requested
    And api request param q is col1.keyword:"Former first lady Barbara Bush dies at 92 - CNN"
    And send api request and fetch the response
    Then api's response status code is 200
    And size of api's response body field data is 1
    And api's response body field /data/*/attributes/col1/val is Former first lady Barbara Bush dies at 92 - CNN

  Scenario: Test filtering by wildcard
    Given I have buzzfeed resource with tabular data
    When resource api tabular data endpoint is requested
    And api request param q is col1:"*lady Barbara Bush dies*"
    And send api request and fetch the response
    Then api's response status code is 200
    And size of api's response body field data is 1
    And api's response body field /data/*/attributes/col1/val is Former first lady Barbara Bush dies at 92 - CNN

  Scenario: Test sorting
    Given I have buzzfeed resource with tabular data
    When resource api tabular data endpoint is requested
    And api request param sort is col2
    And send api request and fetch the response
    Then api's response status code is 200
    And size of api's response body field data is 20
    And api's response body field data is sorted by col2.val

  Scenario: Test dates schemas
    Given I have resource with date and datetime
    When resource api tabular data with date and datetime endpoint is requested
    And send api request and fetch the response
    Then api's response status code is 200
    And size of api's response body field data is 20

  Scenario: Test missing tabular data repr is not None
    Given I have buzzfeed resource with tabular data
    When resource api tabular data endpoint is requested
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/*/attributes/col6/val is None
    And api's response body field /data/*/attributes/col6/repr is not None

  Scenario Outline: Escaping functionality
    Given I have buzzfeed resource with tabular data
    When api request has params <req_params>
    And resource api tabular data endpoint is requested
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | req_params                                          | resp_body_field             | resp_body_value                                       |
    | {"q": "barbara-bush-dies-92/"}                      | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "*Bush*"}                                     | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "col1:Former*"}                               | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "NOT /lottery"}                               | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "NOT col2:/lottery"}                          | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "col1:Former AND col2:*bush*"}                | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "col1:bush AND col2:*/former-*"}              | /data/0/attributes/col1/val | Former first lady Barbara Bush dies at 92 - CNN       |
    | {"q": "Schools AND col4:2018-02-23"}                | /data/0/attributes/col1/val | Donald Trump Ends School Shootings By Banning Schools |
    | {"q": "*Schools* AND col4:2018-02-23"}              | /data/0/attributes/col1/val | Donald Trump Ends School Shootings By Banning Schools |
    | {"q": "col4:2018-02-22"}                            | /data/0/attributes/col1/val | Obama Announces Bid To Become UN Secretary General    |
    | {"q": "yournewswire.com/north AND col4:2018-05-03"} | /data/0/attributes/col1/val | North Korea Agrees To Open Its Doors To Christianity  |
    | {"q": "col2:5a53ac097d3ab/"}                        | /data/0/attributes/col1/val | Second winter storm to impact Eastern Carolinas       |
