@csv_download
Feature: Dataset resources download XML Metadata

  Scenario Outline: Metadata for single dataset can be downloaded as xml file
    Given dataset with id 1004 and 2 resources
    And resource with id 999 dataset id 1004 and supplement with id 999
    When api request language is <lang_code>
    And api request path is /datasets/1004/resources/metadata.xml
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    Then api's response status code is 200
    And api response is xml file with 1 datasets and 3 resources
    And api's response body conforms to <lang_code> xsd schema

    Examples:
    | lang_code |
    | en        |
    | pl        |

  Scenario Outline: Metadata for all datasets can be downloaded as xml file
    Given created catalog xml file
    When api request language is <lang_code>
    And api request path is /datasets/resources/metadata.xml
    And api request header x-api-version is 1.0
    And send api request and fetch the response
    Then api's response status code is 200
    And api response is xml file with 2 datasets and 4 resources
    And api's response body conforms to <lang_code> xsd schema

    Examples:
    | lang_code |
    | en        |
    | pl        |
