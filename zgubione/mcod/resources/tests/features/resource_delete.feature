@elasticsearch
Feature: Delete resource in admin panel

  @feat_dga
  Scenario: Confirmation with DGA warning pops up when deleting a DGA Resource and the Resource is deleted
    Given dataset with pk 998 containing dga resource with pk 999 and title Main DGA
    When admin's request method is GET
    And admin's page /resources/resource/999/delete/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz usunąć (Zasób): <b>"Main DGA"</b>?
    And admin's response page contains Usuwasz aktualny wykaz chronionych danych. Po usunięciu dane z tego wykazu zostaną usunięte z głównego wykazu chronionych danych.
    When admin's request method is POST
    And admin confirms deleting resource
    Then admin's response page contains Zasób &quot;Main DGA&quot; usunięty pomyślnie
    And resource with id 999 is removed

  @feat_dga
  Scenario: Confirmation with DGA warning does not pops up when deleting a non DGA Resource
    Given resource with id 999
    When admin's request method is GET
    And admin's page /resources/resource/999/delete/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz usunąć (Zasób)
    And admin's response page not contains Usuwasz aktualny wykaz chronionych danych. Po usunięciu dane z tego wykazu zostaną usunięte z głównego wykazu chronionych danych.

  @feat_dga
  Scenario: Confirmation with DGA warning pops up when deleting selected resources with the DGA and the resources are deleted
    Given dataset with pk 998 containing dga resource with pk 999 and title Main DGA
    And resource with id 1000
    When admin's request method is POST
    And admin requests to delete selected datasets with ids 999, 1000
    And admin's page /resources/resource/ is requested
    Then admin's response status code is 200
    And admin's response page contains Czy na pewno chcesz usunąć zasoby
    And admin's response page contains Main DGA to aktualny wykaz chronionych danych. Jeżeli go usuniesz, dane z tego zasobu zostaną usunięte z głównego wykazu chronionych danych.
    When admin confirms deleting selected resources
    Then admin's response page contains Pomyślnie usunięto 2 Zasoby.
    And resource with id 999 is removed
    And resource with id 1000 is removed

  @feat_dga
  Scenario: Confirmation with DGA warning does not pops up when deleting selected non-DGA resources
    Given resource with id 999
    And resource with id 1000
    When admin's request method is POST
    And admin requests to delete selected datasets with ids 999, 1000
    And admin's page /resources/resource/ is requested
    Then admin's response status code is 200
    And admin's response page not contains to aktualny wykaz chronionych danych. Jeżeli go usuniesz, dane z tego zasobu zostaną usunięte z głównego wykazu chronionych danych.
