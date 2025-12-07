Feature: Datasource import

  Scenario: CKAN resources are properly imported
    Given active ckan_datasource with id 100 for data {"portal_url": "http://mock-portal.pl", "api_url": "http://api.mock-portal.pl/items"}
    When ckan datasource with id 100 finishes importing objects using harvester_ckan_import_example.json
    Then ckan datasource with id 100 created all data in db

  Scenario: CKAN resources are properly imported with has_ metadata
    Given active ckan_datasource_no_private_institution with id 100 for data {"portal_url": "http://mock-portal.pl", "api_url": "http://api.mock-portal.pl/items"}
    When ckan datasource with id 100 finishes importing objects using harvester_ckan_import_example_with_has_metadata.json
    Then ckan datasource with id 100 created all data in db with has metadata

  Scenario: CKAN resources are not imported - conflict dataset has_high_value_data metadata
    Given active ckan_datasource_no_private_institution with id 100 for data {"portal_url": "http://mock-portal.pl", "api_url": "http://api.mock-portal.pl/items"}
    When ckan datasource with id 100 finishes importing objects using harvester_ckan_import_example_has_high_value_dataset_metadata_conflict.json
    Then ckan datasource with id 100 import not successful

  Scenario: CKAN resources are not imported - conflict resource has_high_value_data metadata
    Given active ckan_datasource_no_private_institution with id 100 for data {"portal_url": "http://mock-portal.pl", "api_url": "http://api.mock-portal.pl/items"}
    When ckan datasource with id 100 finishes importing objects using harvester_ckan_import_example_has_high_value_resource_metadata_conflict.json
    Then ckan datasource with id 100 import not successful

  @periodic_task
  Scenario Outline: XML resources are properly imported
    Given active xml_datasource with id 101 for data {"xml_url": "http://api.mock-portal.pl/some-xml.xml"}
    When xml datasource with id <obj_id> of version <version> finishes importing objects
    Then xml datasource with id <obj_id> of version <version> created all data in db
    Examples:
    | obj_id | version |
    | 101    | 1.2     |
    | 101    | 1.5     |
    | 101    | 1.6     |
    | 101    | 1.7     |
    | 101    | 1.8     |
    | 101    | 1.9     |

  @periodic_task
  Scenario Outline: XML resources are properly imported - version xsd 1.11 and over
    Given active <xml_resource> with id 101 for data {"xml_url": "http://api.mock-portal.pl/some-xml.xml"}
    When xml datasource with id <obj_id> of version <version> finishes importing objects
    Then xml datasource with id <obj_id> of version <version> created all data in db - version xsd 1.11 and over
    Examples:
    | obj_id | version | xml_resource                                |
    | 101    | 1.11    | xml_datasource_owned_by_state_institution   |
    | 101    | 1.12    | xml_datasource_owned_by_state_institution   |
    | 101    | 1.13    | xml_datasource_owned_by_state_institution   |

  @periodic_task
  Scenario Outline: XML resources are not imported - version xsd 1.11 and over
    Given active <xml_resource> with id 101 for data {"xml_url": "http://api.mock-portal.pl/some-xml.xml"}
    When xml datasource with id <obj_id> of version <version> finishes importing objects
    Then xml datasource with id <obj_id> import not successful
    Examples:
    | obj_id | version                                           | xml_resource                                |
    # tags `hasHighValueData` and `hasHighValueDataFromEuropeanCommissionList` conflict
    | 101    | 1.11_dataset_has_high_values_metadata_conflict    | xml_datasource_owned_by_state_institution   |
    # using tag `hasHighValueDataFromEuropeanCommissionList` by private institution
    | 101    | 1.11                                              | xml_datasource_owned_by_private_institution |
    # using tag `containsProtectedData` by private institution
    | 101    | 1.12                                              | xml_datasource_owned_by_private_institution |

  Scenario: DCAT resources are properly imported
    Given active dcat_datasource with id 101 for data {"api_url": "http://api.mock-portal.pl/dcat/endpoint"}
    When dcat datasource with id 101 finishes importing objects
    Then dcat datasource with id 101 created all data in db
