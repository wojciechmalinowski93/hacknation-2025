Feature: Api spec endpoint

  Scenario Outline: Request for spec api is ok
    When api request path is <request_path>
    And json api validation is skipped
    And send api request and fetch the response
    Then api's response status code is 200

        Examples:
      | request_path    |
      | /1.0/spec/      |
      | /1.4/spec/      |
      | /1.0/spec/1.4   |
      | /1.4/spec/1.4   |
