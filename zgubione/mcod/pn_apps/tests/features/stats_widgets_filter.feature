Feature: Statistics can be filtered by widgets

  Scenario Outline: Select widget changes data range for statistics
    Given dataset with id 999 and 3 resources
    And dataset with chart as visualization type
    And chart user admin user
    And chart panel of class <chart_cls>
    When chart select widget has set <selected_options>
    Then chart dataframe contains columns <headers>

    Examples:
    |chart_cls                                    | selected_options  | headers                      |
    |Top10ProvidersByResourcesCount               | file,api          | Nazwa dostawcy,Plik,API      |
    |ResourcesCountByTimePeriod                   | file,api          | Okres,Plik,API               |
    |NewResourcesCountByTimePeriod                | file,api          | Okres,Plik,API               |
    |Top10ProvidersByDatasetsCount                | ct_table,ct_chart | Nazwa dostawcy,Tabela,Wykres |
    |DatasetsCountByTimePeriod                    | ct_table,ct_chart | Okres,Tabela,Wykres          |
    |NewDatasetsCountByTimePeriod                 | ct_table,ct_chart | Okres,Tabela,Wykres          |
    |Top10LastMonthOrganizationNewDatasets        | ct_table,ct_chart | Instytucja,Tabela,Wykres     |

    Scenario Outline: Select widget changes data range for agent statistics
    Given institution with id 999
    And dataset created with params {"id": 998, "organization_id": 999}
    And resource with id 999 and dataset_id is 998
    And chart agent user created with params {"id": 999, "agent_organizations": [999]}
    And chart panel of class <chart_cls>
    When chart select widget has set <selected_options>
    Then chart dataframe contains columns <headers>

    Examples:
    |chart_cls                                    | selected_options  | headers             |
    |NewResourcesForInstitutionsGroupByTimePeriod | file,api          | Okres,Plik,API      |
    |DatasetsCountByTimePeriodForGroup            | ct_table,ct_chart | Okres,Tabela,Wykres |
    |NewDatasetsByTimePeriodForGroup              | ct_table,ct_chart | Okres,Tabela,Wykres |
    |ResourcesForInstitutionsGroupByTimePeriod    | file,api          | Okres,Plik,API      |
    |TopResourceCountOrgfromGroup                 | file,api          | Instytucja,Plik,API |
