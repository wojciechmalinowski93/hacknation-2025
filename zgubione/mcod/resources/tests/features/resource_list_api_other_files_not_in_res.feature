@elasticsearch
Feature: Resources list API other files in separate model

    Scenario: Test xls resource converted to csv on resources list with separate files model
    Given resource with id 999 and xls file converted to csv
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then api's response body field data/[0]/attributes/file_url endswith example_xls_file.xls
    And api's response body field data/[0]/attributes/files is not None
    And api's response body field data/[0]/attributes/openness_score is 3

  Scenario: Test csv resource converted to jsonld on resources list with separate files model
    Given resource with csv file converted to jsonld with params {"id": 999}
    When api request path is /1.4/resources/?id=999
    And send api request and fetch the response
    Then api's response body field data/[0]/attributes/file_url endswith csv2jsonld.csv
    And api's response body field data/[0]/attributes/files is not None
    And api's response body field data/[0]/attributes/openness_score is 4
