@elasticsearch
Feature: Resource validation

  Scenario: Revalidated draft resource is not published in suggest api
    Given resource created with params {"id": 1999, "status": "draft", "title": "draft_res"}
    When resource with id 1999 is revalidated
    And api request path is /1.4/search/suggest/?q=draft_res&models=resource,dataset
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data is []

  Scenario: Revalidated draft resource is not published search api
    Given resource created with params {"id": 1999, "status": "draft", "title": "draft_res"}
    When resource with id 1999 is revalidated
    And api request path is /1.4/search/?page=1&per_page=20&q=draft_res&sort=-date&model[terms]=resource
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data is []
