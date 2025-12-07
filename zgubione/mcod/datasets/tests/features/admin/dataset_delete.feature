@elasticsearch
Feature: Delete dataset in admin panel

  @feat_dga
  Scenario: Confirmation with DGA warning pops up when deleting Dataset containing DGA Resource and Dataset is deleted
    Given dataset with pk 998 and title DGA Dataset containing dga resource
    When admin's request method is GET
    And admin's page /datasets/dataset/998/delete/ is requested
    Then admin's response status code is 200
    And admin's response page contains W zbiorze znajduje się aktualny wykaz chronionych danych. Po usunięciu zbioru dane z tego zasobu zostaną usunięte z głównego wykazu chronionych danych.
    When admin's request method is POST
    And admin confirms deleting dataset
    Then admin's response page contains Zbiór danych &quot;DGA Dataset&quot; usunięty pomyślnie.
    And dataset with id 998 is removed

  @feat_dga
  Scenario: Confirmation with DGA warning does not pops up when deleting Dataset without DGA Resource
    Given dataset with id 998 and 3 resources
    When admin's request method is GET
    And admin's page /datasets/dataset/998/delete/ is requested
    Then admin's response status code is 200
    And admin's response page not contains W zbiorze znajduje się aktualny wykaz chronionych danych. Po usunięciu zbioru dane z tego zasobu zostaną usunięte z głównego wykazu chronionych danych.

  @feat_dga
  Scenario: Confirmation with DGA warning pops up when deleting selected Datasets with DGA Resource and the Datasets are deleted
    Given dataset with pk 998 and title DGA Dataset containing dga resource
    And dataset with id 999
    When admin's request method is POST
    And admin requests to delete selected datasets with ids 998, 999
    And admin's page /datasets/dataset/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz usunąć zbiory danych
    And admin's response page contains W zbiorze DGA Dataset znajduje się aktualny wykaz chronionych danych. Po usunięciu zbioru dane z tego zasobu zostaną usunięte z głównego wykazu chronionych danych.
    When admin confirms deleting selected resources
    Then admin's response page contains Pomyślnie usunięto 2 Zbiory danych.
    And dataset with id 998 is removed
    And dataset with id 999 is removed

  @feat_dga
  Scenario: Confirmation with DGA warning does not pops up when deleting selected Datasets without DGA Resource
    Given dataset with id 999
    And dataset with id 1000
    When admin's request method is POST
    And admin requests to delete selected datasets with ids 999, 1000
    And admin's page /datasets/dataset/ is requested
    Then admin's response status code is 200
    And admin's response page not contains znajduje się aktualny wykaz chronionych danych. Po usunięciu zbioru dane z tego zasobu zostaną usunięte z głównego wykazu chronionych danych.
