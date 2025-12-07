@csv_download
Feature: Dataset resources download CSV API

  Scenario: Single dataset resources can be downloaded as csv file
    Given dataset with id 999 and 3 resources
    When api request path is /datasets/999/resources/metadata.csv
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    Then api's response status code is 200
    And api response is csv file with 3 records

  Scenario: All datasets resources can be downloaded as csv file
    Given created catalog csv file
    When api request path is /datasets/resources/metadata.csv
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    Then api's response status code is 200
    And api response is csv file with 12 records
