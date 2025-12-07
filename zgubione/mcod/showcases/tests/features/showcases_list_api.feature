@elasticsearch
Feature: Showcases list API

  Scenario Outline: Showcase routes
    Given dataset with id 999
    And showcase created with params {"id": 999, "slug": "showcase-slug", "datasets": [999]}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    Examples:
    | request_path                          |
    | /showcases                            |
    | /showcases/999                        |
    | /showcases/999,showcase-slug          |
    | /showcases/999/datasets               |
    | /showcases/999,showcase-slug/datasets |
    | /datasets/999/showcases               |

  Scenario: Showcases list item returns slug in self link
    Given showcase created with params {"id": 999, "slug": "showcase-slug"}
    When api request path is /showcases?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/links/self endswith 999,showcase-slug

  Scenario Outline: Showcases list is sortable by views_count
    Given 3 showcases
    When api request path is <request_path>
    Then api request param <req_param_name> is <req_param_value>
    And send api request and fetch the response
    And api's response list is sorted by <sort> <sort_order>
    And api's response body has field data/*/relationships/datasets/meta/count
    And api's response body has field data/*/relationships/datasets/links/related
    Examples:
    | request_path   | req_param_name | req_param_value | sort        | sort_order   |
    | /1.0/showcases | sort           | views_count     | views_count | ascendingly  |
    | /1.0/showcases | sort           | -views_count    | views_count | descendingly |
    | /1.4/showcases | sort           | views_count     | views_count | ascendingly  |
    | /1.4/showcases | sort           | -views_count    | views_count | descendingly |

  Scenario: Showcases list contains published showcases
    Given showcase created with params {"id": 999, "title": "Ponowne wykorzystanie - test", "status": "published"}
    When api request path is /1.0/showcases?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/title is Ponowne wykorzystanie - test

  Scenario: Showcases list doesnt contains draft showcases
    Given showcase created with params {"id": 999, "title": "Ponowne wykorzystanie - test", "status": "draft"}
    When api request path is /1.0/showcases?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/title does not contain Ponowne wykorzystanie - test

  Scenario: Created draft showcase with related datasets is not pushed into index (not visible in Search)
    Given dataset with id 999
    And showcase created with params {"id": 999, "title": "Ponowne wykorzystanie - test", "status": "draft", "datasets": [999]}
    When api request path is /1.0/showcases?id=999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/title does not contain Ponowne wykorzystanie - test

  Scenario: Featured showcases
    Given featured showcases
    When api request path is /1.4/showcases
    And api request param is_featured is true
    Then send api request and fetch the response
    And api's response status code is 200
    And 4 featured showcases are returned

  Scenario Outline: Suggest showcaseproposal
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request <object_type> data has <req_data>
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/title is Suggest showcaseproposal test
    Examples:
    | object_type      | req_data                                                                                 |
    | showcaseproposal | {"title": "Suggest showcaseproposal test", "keywords": []}                               |
    | showcaseproposal | {"title": "Suggest showcaseproposal test", "image": "", "illustrative_graphics": ""}     |

  Scenario: Suggest showcaseproposal other app
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request showcaseproposal data has {"title": "Suggest showcaseproposal other test", "category": "other"}
    And send api request and fetch the response
    Then api's response status code is 201
    And api's response body field data/attributes/title is Suggest showcaseproposal other test

  Scenario: Suggest showcaseproposal without license_type
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request showcaseproposal data has {"license_type": ""}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/title is Błąd pola
    And api's response body field errors/[0]/detail is Niepoprawna wartość! Możliwe wartości: ['free', 'commercial']
    And api's response body field errors/[0]/source/pointer is /data/attributes/license_type

  Scenario: Suggest showcaseproposal without is_personal_data_processing_accepted
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request showcaseproposal data has {"is_personal_data_processing_accepted": false}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/title is Błąd pola
    And api's response body field errors/[0]/detail is To pole jest obowiązkowe
    And api's response body field errors/[0]/source/pointer is /data/attributes/is_personal_data_processing_accepted

  Scenario: Suggest showcaseproposal without is_terms_of_service_accepted
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request showcaseproposal data has {"is_terms_of_service_accepted": false}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/title is Błąd pola
    And api's response body field errors/[0]/detail is To pole jest obowiązkowe
    And api's response body field errors/[0]/source/pointer is /data/attributes/is_terms_of_service_accepted

  Scenario: Suggest showcaseproposal mobile app without any mobile url
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request showcaseproposal data has {"is_mobile_app": true, "mobile_apple_url": "", "mobile_google_url": ""}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/title is Błąd pola
    And api's response body field errors/[0]/detail is Przekazanie co najmniej jednego z: mobile_apple_url, mobile_google_url jest wymagane!
    And api's response body field errors/[0]/source/pointer is /data/attributes/is_mobile_app

  Scenario: Suggest showcaseproposal desktop app without any desktop url
    Given dataset with id 999
    When api request method is POST
    And api request path is /showcases/suggest
    And api request showcaseproposal data has {"is_desktop_app": true, "desktop_linux_url": "", "desktop_macos_url": "", "desktop_windows_url": ""}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/[0]/title is Błąd pola
    And api's response body field errors/[0]/detail is Przekazanie co najmniej jednego z: desktop_linux_url, desktop_macos_url, desktop_windows_url jest wymagane!
    And api's response body field errors/[0]/source/pointer is /data/attributes/is_desktop_app

  Scenario: Showcase is visible in search with aggregations
    Given dataset with id 999
    And showcase created with params {"id": 999, "title": "Ponowne wykorzystanie - test", "datasets": [999], "is_mobile_app": true, "mobile_apple_url": "https://example.com", "mobile_google_url": "https://example.com", "is_desktop_app": true, "desktop_linux_url": "https://example.com", "desktop_macos_url": "https://example.com", "desktop_windows_url": "https://example.com"}
    When api request path is /search?model=showcase&id=999&facet[terms]=by_showcase_category,by_showcase_platforms,by_showcase_types
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/title contains Ponowne wykorzystanie - test
    And api's response body has field meta/aggregations/by_showcase_category
    And api's response body has field meta/aggregations/by_showcase_platforms
    And api's response body has field meta/aggregations/by_showcase_types
