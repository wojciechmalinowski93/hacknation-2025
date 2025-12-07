Feature: Resource link validation

  Scenario Outline: Resource type discovery
    When response is <resp_name> type is <resp_type>
    Examples:
    | resp_name                  | resp_type |
    | xml_resource_file_response | file      |
    | xml_resource_api_response  | api       |
    | json_resource_response     | api       |
    | jsonstat_resource_response | api       |
    | html_resource_response     | website   |

  Scenario: DangerousContentError is raised
    When response is malicious php DangerousContentError is raised
