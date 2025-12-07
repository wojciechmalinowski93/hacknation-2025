@elasticsearch
Feature: Resource details API

  Scenario: Test resource details endpoint increments popularity of the resource in API 1.4
    Given resource with id 998 and views_count is 0
    When json api validation is skipped
    And api request path is /1.4/resources/998/
    And send api request and fetch the response
    Then api's response status code is 200
    And counter incrementing task is executed
    And resource with id 998 views_count is 1

  Scenario: Test unpublished resource details endpoint doesnt increment popularity of the resource in API 1.4
    Given unpublished resource with id 999 and views_count is 0
    When api request path is /1.4/resources/999/
    And send api request and fetch the response
    Then api's response status code is 404
    And counter incrementing task is executed
    And resource with id 999 views_count is 0

  Scenario: Downloading endpoint increases download count
    Given resource with id 999 and downloads_count is 0
    When json api validation is skipped
    And api request path is /1.0/resources/999/file
    And send api request and fetch the response
    Then api's response status code is 302
    And counter incrementing task is executed
    And resource with id 999 downloads_count is 1

  Scenario: Trying to download unpublished resource doesnt increase download count
    Given unpublished resource with id 999 and downloads_count is 0
    When json api validation is skipped
    And api request path is /1.4/resources/999/file
    And send api request and fetch the response
    Then api's response status code is 404
    And counter incrementing task is executed
    And resource with id 999 downloads_count is 0

  Scenario: Test resource details endpoint does not contain included section by default in API 1.4
    Given resource with id 999 and views_count is 0
    When api request path is /1.4/resources/999/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has no field included

  Scenario Outline: Test resource details contains resource ident in links section in API 1.4
    Given resource with id 999 and slug is resource-test-slug
    When api request path is <request_path>
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/links/self endswith 999,resource-test-slug

    Examples:
    | request_path                           |
    | /resources/999/                        |
    | /resources/999,resource-test-slug/     |
    | /1.4/resources/999/                    |
    | /1.4/resources/999,resource-test-slug/ |

  Scenario: Test resource details endpoint contains included section in API 1.4
    Given resource with id 999 and views_count is 0
    When api request path is /1.4/resources/999/
    Then api request param include is dataset
    And send api request and fetch the response
    And api's response status code is 200
    And api's response body has field included

  Scenario: Test resource details endpoint for xls resource converted to csv
    Given resource with id 1001 and xls file converted to csv
    When api request path is /1.4/resources/1001/
    And send api request and fetch the response
    Then api's response body field data/attributes/file_url endswith example_xls_file.xls
    And api's response body field data/attributes/csv_file_url endswith example_xls_file.csv
    And api's response body field data/attributes/csv_file_size is not None
    And api's response body field data/attributes/csv_download_url is not None

  Scenario: Test resource details endpoint for csv resource converted to jsonld
    Given resource with csv file converted to jsonld with params {"id": 999}
    When api request path is /1.4/resources/999/
    And send api request and fetch the response
    Then api's response body field data/attributes/file_url endswith csv2jsonld.csv
    And api's response body field data/attributes/jsonld_file_url endswith csv2jsonld.jsonld
    And api's response body field data/attributes/jsonld_file_size is not None
    And api's response body field data/attributes/jsonld_download_url is not None
    And api's response body field data/attributes/openness_score is 4

  Scenario: Resource without regions has poland shown as region
    Given resource with id 999
    When api request path is /1.4/resources/999/
    And send api request and fetch the response
    Then api's response body field data/attributes/regions/0/name is Polska
    And api's response body field data/attributes/regions/0/region_id is 85633723
    And api's response body field data/attributes/regions/0/is_additional is False
    And size of api's response body field data/attributes/regions is 1

  Scenario: Resource's region is returned by api
    Given dataset with id 998
    And resource with id 999 dataset id 998 and single main region
    When api request path is /1.4/resources/999/
    And send api request and fetch the response
    Then api's response body field data/attributes/regions/1/name is Warszawa
    And api's response body field data/attributes/regions/1/region_id is 101752777
    And api's response body field data/attributes/regions/1/is_additional is False
    Then api's response body field data/attributes/regions/0/name is Polska
    And api's response body field data/attributes/regions/0/is_additional is True
    And size of api's response body field data/attributes/regions is 5

  Scenario: Resource supplements details
    Given resource with id 999
    And supplement created with params {"id": 999, "resource_id": 999, "file": "example.txt", "name": "supplement 999 of resource 999", "language": "pl"}
    When api request path is /1.4/resources/999/
    And send api request and fetch the response
    Then api's response body has field data/attributes/supplements
    And api's response body field data/attributes/supplements/[0]/name is supplement 999 of resource 999
    And api's response body field data/attributes/supplements/[0]/language is pl
    And api's response body has field data/attributes/supplements/[0]/file_url

  Scenario: Resource file geo data are returned by api
    Given dataset with id 998
    And resource with tabular_file_with_geo_data.csv file and id 989
    When admin's request method is POST
    And admin's request posted resource data is {"title": "test geo tabular csv", "description": "<p>more than 20 characters</p>", "dataset": 998, "data_date": "2021-05-04", "status": "published", "show_tabular_view": "on", "schema_type_0": "string", "schema_type_1": "string", "schema_type_2": "string", "schema_type_3": "number", "schema_type_4": "string", "schema_type_5": "string", "schema_type_6": "string", "geo_0": "label", "geo_1": "postal_code", "geo_2": "place", "geo_3": "", "geo_4": "", "geo_5": "", "geo_6": "", "_map_save": ""}
    And admin's page with geocoder mocked api for tabular data /resources/resource/989/change/ is requested
    And api request path is /1.4/resources/989/geo?bbox=5.07568359375,56.03522578369872,33.15673828125,47.945786463687185,3,9&per_page=100
    And send api request and fetch the response
    Then api's response body has field meta/aggregations/tiles
    And api's response body field meta/aggregations/tiles/[0]/doc_count is 1

  Scenario: Resource api doc page is available
    Given resource with id 999
    When api request path is /resources/999/data/doc
    And json api validation is skipped
    And send api request and fetch the response
    Then api's response status code is 200

  Scenario: Resource with zipped file shows details about archive and main format
    Given resource with regular zip file and id 1999
    When api request path is /1.4/resources/1999/
    And send api request and fetch the response
    Then api's response body field data/attributes/files/[0]/format is zip
    And api's response body field data/attributes/files/[0]/compressed_file_format is csv
    And api's response body field data/attributes/files/[0]/openness_score is 3
