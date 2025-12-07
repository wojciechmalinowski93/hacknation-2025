Feature: Resource forms
  Scenario: Maps and plots correct set
    Given form class is mcod.resources.forms.ChangeResourceForm
    And form instance is geo_tabular_data_resource
    And form geo data is {"geo_0": "label", "geo_2": "l", "geo_3": "b"}
    Then form is valid

  Scenario Outline: Map and plots invalid sets
    Given form class is mcod.resources.forms.ChangeResourceForm
    And form instance is tabular_resource
    And form <object_type> data is <form_data>
    Then form field <field_name> error is <error_msg>
    Examples:
    | object_type | form_data                                          | field_name     | error_msg                                                                                                                                                                              |
    | tabular     | {"geo_1": "l", "geo_2": "b"}                       | maps_and_plots | Brak elementów: etykieta dla zestawu danych mapowych: współrzędne geograficzne. Ponów definiowanie mapy wybierając wskazane elementy.                                                  |
    | tabular     | {"geo_1": "uaddress"}                              | maps_and_plots | Brak elementów: etykieta dla zestawu danych mapowych: adres uniwersalny. Ponów definiowanie mapy wybierając wskazane elementy.                                                         |
    | tabular     | {"geo_1": "place", "geo_2": "postal_code"}         | maps_and_plots | Brak elementów: etykieta dla zestawu danych mapowych: adres. Ponów definiowanie mapy wybierając wskazane elementy.                                                                     |
    | tabular     | {"geo_1": "label"}                                 | maps_and_plots | Zestaw danych mapowych jest niekompletny                                                                                                                                               |
    | tabular     | {"geo_1": "label", "geo_2": "label", "geo_3": "b"} | maps_and_plots | element etykieta wystąpił więcej niż raz. Ponów definiowanie mapy wybierając tylko raz wymagany element zestawu mapowego.                                                              |
    | tabular     | {"geo_1": "place", "geo_2": "b"}                   | maps_and_plots | pochodzą z różnych zestawów danych mapowych. Ponów definiowanie mapy wybierając elementy z tylko jednego zestawu danych mapowych. |

  Scenario: Change published resource with unpublished dataset
    Given form class is mcod.resources.forms.ChangeResourceForm
    And dataset created with params {"id": 999, "status": "draft", "title": "Publikacja zasobu ze zbiorem o statusie draft"}
    And form instance is tabular_resource
    And form tabular data is {"dataset": 999, "status": "published"}
    Then form field status error is Nie można ustawić status opublikowany dla tego zasobu, ponieważ zbiór do którego przynależy ma status szkic. Aby zmienić status należy najpierw opublikować zbiór: <a href="/datasets/dataset/999/change/">Publikacja zasobu ze zbiorem o statusie draft</a>
