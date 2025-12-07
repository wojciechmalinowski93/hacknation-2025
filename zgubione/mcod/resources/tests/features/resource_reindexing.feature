@elasticsearch
Feature: Resource reindexing
  Scenario: Test document formats of csv resource converted to jsonld after reindexing using regular queryset
    Given resource with csv file converted to jsonld with params {"id": 10007}
    When resource document with id 10007 is reindexed using regular queryset
    Then resource document with id 10007 field formats equals ['csv', 'jsonld']

  Scenario: Test document formats of csv resource converted to jsonld after reindexing using queryset iterator
    Given resource with csv file converted to jsonld with params {"id": 10008}
    When resource document with id 10008 is reindexed using queryset iterator
    Then resource document with id 10008 field formats equals ['csv', 'jsonld']

  Scenario: Test documents after reindexing using regular queryset vs queryset iterator
    Given resource with csv file converted to jsonld with params {"id": 10009}
    When resource document with id 10009 is reindexed using queryset iterator
    And resource document with id 10009 is reindexed using regular queryset
    Then compare resource documents reindexed using different approaches
