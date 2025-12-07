@elasticsearch
Feature: Global Search API
  Scenario Outline: Test that endpoint returns message about too short search phrase
    Given institution with id 777 and 2 datasets
    When api request path is /1.4/search/
    And api request language is <lang_code>
    And api request param <req_param_name> is <req_param_value>
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field <resp_body_field> is <resp_body_value>
    Examples:
    | lang_code | req_param_name | req_param_value | resp_body_field    | resp_body_value                                         |
    | en        | q              | a               | /errors/[0]/detail | The entered phrase should be at least 2 characters long |
    | pl        | q              | c               | /errors/[0]/detail | Wpisana fraza musi zawierać przynajmniej 2 znaki        |

  Scenario Outline: Test that search returns valid response for different queries
    Given <object_type> created with params <params>
    When api request path is /1.4/search/
    And api request param per_page is 100
    And api request has params <req_params>
    And api request language is <lang_code>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's search response objects have fields <fields_str>

    Examples:
    | object_type | params                                       | req_params                                    | lang_code | fields_str                     |
    | dataset     | {"id": 999, "title_en": "ds_title_en"}       | {"model": "dataset", "q": "ds_title_en"}      | en        | title,notes,is_promoted        |
    | dataset     | {"id": 999, "title": "ds_title_pl"}          | {"model": "dataset", "q": "ds_title_pl"}      | pl        | title,notes,is_promoted        |
    | dataset     | {"id": 999, "notes_en": "ds_notes_en"}       | {"model": "dataset", "q": "ds_notes_en"}      | en        | title,notes,is_promoted        |
    | dataset     | {"id": 999, "notes": "ds_notes_pl"}          | {"model": "dataset", "q": "ds_notes_pl"}      | pl        | title,notes,is_promoted        |
    | dataset     | {"id": 999, "tags": ["ds_tag_en"]}           | {"model": "dataset", "q": "ds_tag_en"}        | en        | title,notes,tags,is_promoted   |
    | dataset     | {"id": 999, "tags": ["ds_tag_pl"]}           | {"model": "dataset", "q": "ds_tag_pl"}        | pl        | title,notes,tags,is_promoted   |

    | resource    | {"id": 999, "title_en": "res_title_en"}      | {"model": "resource", "q": "res_title_en"}    | en        | title,notes              |
    | resource    | {"id": 999, "title": "res_title_pl"}         | {"model": "resource", "q": "res_title_pl"}    | pl        | title,notes              |
    | resource    | {"id": 999, "description_en": "res_desc_en"} | {"model": "resource", "q": "res_desc_en"}     | en        | title,notes              |
    | resource    | {"id": 999, "description": "res_desc_pl"}    | {"model": "resource", "q": "res_desc_pl"}     | pl        | title,notes              |

    | institution | {"id": 999, "title_en": "ins_title_en"}      | {"model": "institution", "q": "ins_title_en"} | en        | title,notes,abbreviation |
    | institution | {"id": 999, "title": "ins_title_pl"}         | {"model": "institution", "q": "ins_title_pl"} | pl        | title,notes,abbreviation |
    | institution | {"id": 999, "description_en": "ins_desc_en"} | {"model": "institution", "q": "ins_desc_en"}  | en        | title,notes,abbreviation |
    | institution | {"id": 999, "description": "ins_desc_pl"}    | {"model": "institution", "q": "ins_desc_pl"}  | pl        | title,notes,abbreviation |
    | institution | {"id": 999, "abbreviation": "abbrev"}        | {"model": "institution", "q": "abbrev"}       | en        | title,notes,abbreviation |
    | institution | {"id": 999, "abbreviation": "abbrev"}        | {"model": "institution", "q": "abbrev"}       | pl        | title,notes,abbreviation |

    | showcase    | {"id": 999, "title_en": "title_en"}          | {"model": "showcase", "q": "title_en"}     | en        | title,notes,author,image_thumb_url,image_alt,showcase_category,showcase_category_name,showcase_platforms,showcase_types      |
    | showcase    | {"id": 999, "title": "title_pl"}             | {"model": "showcase", "q": "title_pl"}     | pl        | title,notes,author,image_thumb_url,image_alt,showcase_category,showcase_category_name,showcase_platforms,showcase_types      |
    | showcase    | {"id": 999, "notes_en": "notes_en"}          | {"model": "showcase", "q": "notes_en"}     | en        | title,notes,author,image_thumb_url,image_alt,showcase_category,showcase_category_name,showcase_platforms,showcase_types      |
    | showcase    | {"id": 999, "notes": "notes_pl"}             | {"model": "showcase", "q": "notes_pl"}     | pl        | title,notes,author,image_thumb_url,image_alt,showcase_category,showcase_category_name,showcase_platforms,showcase_types      |
    | showcase    | {"id": 999, "author": "John Cleese"}         | {"model": "showcase", "q": "John Cleese"}  | en        | title,notes,author,image_thumb_url,image_alt,showcase_category,showcase_category_name,showcase_platforms,showcase_types      |
    | showcase    | {"id": 999, "author": "John Cleese"}         | {"model": "showcase", "q": "John Cleese"}  | pl        | title,notes,author,image_thumb_url,image_alt,showcase_category,showcase_category_name,showcase_platforms,showcase_types      |
    | showcase    | {"id": 999, "tags": ["app_tag_en"]}          | {"model": "showcase", "q": "app_tag_en"}   | en        | title,notes,author,image_thumb_url,image_alt,tags,showcase_category,showcase_category_name,showcase_platforms,showcase_types |
    | showcase    | {"id": 999, "tags": ["app_tag_pl"]}          | {"model": "showcase", "q": "app_tag_pl"}   | pl        | title,notes,author,image_thumb_url,image_alt,tags,showcase_category,showcase_category_name,showcase_platforms,showcase_types |

  Scenario Outline: Search filters by regions geodata
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    And 3 resources
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And has assigned Polska,Warszawa as name for regions
    And has assigned 85633723,101752777 as region_id for regions
    And has assigned 85633723,101752777 as region_id for regions
    And api's response body field meta/aggregations/map_by_regions/[0] has fields doc_count,region_name,datasets_count,resources_count,centroid

      Examples:
      | request_path                                                                                                    |
      | /1.4/search/?regions[bbox][geo_shape]=19.259214,53.481806,23.128409,51.013112,8&model[terms]=resource&per_page=10 |
      | /1.4/search/?regions[id][terms]=101752777&model[terms]=resource&per_page=10                                     |

  Scenario Outline: Institution abbrevation based search is case insensitive
    Given institution created with params {"id": 1000, "title": "test institution", "slug": "test-institution", "abbreviation": "TSTI"}
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/attributes/title is test institution

    Examples:
      | request_path                                                                  |
      | /1.4/search?page=1&per_page=20&q=tsti&sort=relevance&model[terms]=institution |
      | /1.4/search?page=1&per_page=20&q=TSTI&sort=relevance&model[terms]=institution |
      | /1.4/search?page=1&per_page=20&q=TSti&sort=relevance&model[terms]=institution |

  Scenario: Search filtered facet returns region aggregation
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    And 3 resources
    When api request path is /1.4/search?model[terms]=dataset,resource&per_page=1&filtered_facet[by_regions]=101752777
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field meta/aggregations/by_regions/[0]/id is 101752777
    And api's response body field meta/aggregations/by_regions/[0]/title is Warszawa, Gmina Warszawa, pow. Warszawa, woj. mazowieckie

  Scenario Outline: Search by region bbox returns different administrative layers based on zoom
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
    | request_path                                                                                                       |resp_body_field                                      | resp_body_value                                           |
    | /1.4/search/?regions[bbox][geo_shape]=19.259214,53.481806,23.128409,51.013112,6&model[terms]=resource&per_page=10  |meta/aggregations/map_by_regions/[0]/region_name     |Polska                                                     |
    | /1.4/search/?regions[bbox][geo_shape]=19.259214,53.481806,23.128409,51.013112,8&model[terms]=resource&per_page=10  |meta/aggregations/map_by_regions/[0]/region_name     |woj. mazowieckie                                           |
    | /1.4/search/?regions[bbox][geo_shape]=19.259214,53.481806,23.128409,51.013112,10&model[terms]=resource&per_page=10 |meta/aggregations/map_by_regions/[0]/region_name     |pow. Warszawa, woj. mazowieckie                            |
    | /1.4/search/?regions[bbox][geo_shape]=19.259214,53.481806,23.128409,51.013112,11&model[terms]=resource&per_page=10 |meta/aggregations/map_by_regions/[0]/region_name     |Gmina Warszawa, pow. Warszawa, woj. mazowieckie            |
    | /1.4/search/?regions[bbox][geo_shape]=19.259214,53.481806,23.128409,51.013112,12&model[terms]=resource&per_page=10 |meta/aggregations/map_by_regions/[0]/region_name     |Warszawa, Gmina Warszawa, pow. Warszawa, woj. mazowieckie  |

  Scenario: Search returns promoted datasets as first
    Given dataset created with params {"id": 998, "is_promoted": true}
    And dataset with id 999
    When api request path is /search?model[terms]=dataset&sort=-search_date
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field data/[0]/id is 998
    And api's response body field data/[0]/attributes/is_promoted is True
    And api's response body field data/[1]/attributes/is_promoted is False

  Scenario: Aggregations contains counters for all models event if results are filtered by model
    Given institution with id 999
    And dataset created with params {"id": 999, "title": "test institution", "organization_id": 999}
    When api request path is /search?model[terms]=dataset
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body field meta/count is 1
    And api's response body field data/[0]/id is 999
    And api's response body field data/[0]/attributes/model is dataset
    And api's response body field meta/aggregations/counters/datasets is 1
    And api's response body field meta/aggregations/counters/institutions is not 0

  Scenario Outline: Search returns resources with specified language in results and aggregations depending on request language
    Given <object_type> created with params <params>
    When api request path is <request_path>
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length <number>
    And api's response body has field data/[0]/attributes/language
    And api's response body field <resp_body_field> is <resp_body_value>

    Examples:
      | object_type | params                        | request_path                                                   | number | resp_body_field                         | resp_body_value |
      | resource    | {"id": 999, "language": "en"} | /search?language=en&id=999&facet[terms]=by_language            | 1      | meta/aggregations/by_language/[0]/title | angielski       |
      | resource    | {"id": 999, "language": "pl"} | /search?language=pl&id=999&facet[terms]=by_language            | 1      | meta/aggregations/by_language/[0]/title | polski          |
      | resource    | {"id": 999, "language": "en"} | /resources?language=en&id=999&facet[terms]=by_language&lang=en | 1      | meta/aggregations/by_language/[0]/title | English         |
      | resource    | {"id": 999, "language": "pl"} | /resources?language=pl&id=999&facet[terms]=by_language&lang=en | 1      | meta/aggregations/by_language/[0]/title | Polish          |

  @feat_dga
  Scenario: Search returns resources filtered by DGA (protected data) flag
    Given resource with id 999
    Given resource created with params {"id": 998, "contains_protected_data": true}
    Given resource created with params {"id": 997, "contains_protected_data": false}
    And dataset created with params {"id": 999, "title": "test for filtering"}
    When api request path is /search?contains_protected_data[term]=true&model[terms]=dataset,resource
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 1
    And api's response body field data/[0]/attributes/contains_protected_data is True

  @feat_dga
  Scenario: Search endpoint informs the client about possibility to filter by DGA (protected data) flag
    Given resource with id 999
    When api request path is /search?model[terms]=dataset,resource&facet[terms]=by_contains_protected_data
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response body has field meta/aggregations/by_contains_protected_data

  @feat_dga
  Scenario Outline: Search doesn't filter datasets by DGA flag
    Given dataset
    Given resource created with params {"id": 998, "contains_protected_data": true}
    Given resource created with params {"id": 997, "contains_protected_data": false}
    When api request path is /search?contains_protected_data[term]=<contains_protected_data_value>&model[terms]=dataset
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response data has length 0
    And api's response body has no field meta/aggregations/by_contains_protected_data
  Examples:
    | contains_protected_data_value |
    | true                          |
    | false                         |
