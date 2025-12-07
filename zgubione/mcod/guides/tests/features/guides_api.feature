Feature: Guides API
  Scenario: Test that API returns list of guides
    Given guide created with params {"id": 999, "title": "Testowy przewodnik"}
    When api request language is pl
    And api request path is /guides
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field meta/count is 1
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/type is guide
    And api's response body field data/[0]/attributes/name is Testowy przewodnik

  Scenario: Test that API returns details of specified guide
    Given guide created with params {"id": 999, "title": "Testowy przewodnik"}
    When api request language is pl
    And api request path is /guides/999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/id is 999
    And api's response body field data/type is guide
    And api's response body field data/attributes/name is Testowy przewodnik

  Scenario: Test that API returns details of specified guide with GuideItem data
    Given guide with id 998
    And guide item created with params {"id": 998, "title": "test Item", "content": "jakaś treść", "route": "/dataset/", "css_selector": "h1", "position": "top", "order": 0, "is_optional": true, "is_clickable": true, "is_expandable": true, "guide_id": 998}
    When api request language is pl
    And api request path is /guides/998?include=item
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/id is 998
    And api's response body field data/type is guide
    And api's response body field included/0/attributes/name is test Item
    And api's response body field included/0/attributes/content is jakaś treść
    And api's response body field included/0/attributes/route is /dataset/
    And api's response body field included/0/attributes/is_clickable is True
    And api's response body field included/0/attributes/is_expandable is True
