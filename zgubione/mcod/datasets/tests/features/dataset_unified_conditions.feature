Feature: Datasets unified conditions in details API

    Scenario: Dataset details api doesnt return license conditions description
        Given institution created with params {"id": 1000, "slug": "test-institution-slug", "institution_type": "local"}
        And dataset with id 999 and organization_id is 1000 and license_condition_default_cc40 is True
        When api request path is /1.4/datasets/999
        And send api request and fetch the response
        Then api's response status code is 200
        And api's response body field data/attributes/current_condition_descriptions is {}

    Scenario: Dataset details api returns license conditions custom description
        Given institution created with params {"id": 1000, "slug": "test-institution-slug", "institution_type": "local"}
        And dataset with id 999 and organization_id is 1000 and license_condition_custom_description is jakis tekst
        When api request path is /1.4/datasets/999
        And send api request and fetch the response
        Then api's response status code is 200
        And api's response body field data/attributes/current_condition_descriptions/license_condition_custom_description endswith Zakres odpowiedzialności podmiotu zobowiązanego (dostawcy) za udostępniane informacje sektora publicznego
        And api's response body field data/attributes/license_condition_custom_description endswith jakis tekst
