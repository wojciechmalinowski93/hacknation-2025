Feature: Newsletter subscriptions
    Scenario: User can fetch newsletter rules info
    Given logged active user
    When api request path is /1.0/auth/newsletter/subscribe/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body has field data/attributes/personal_data_processing
    And api's response body has field data/attributes/personal_data_use
    And api's response body has field data/attributes/personal_data_use_rules

  Scenario: Logged in user can subscribe for receiving of newsletter
    Given logged active user
    When api request method is POST
    And api request path is /1.0/auth/newsletter/subscribe/
    And api request body field email is test@example.com
    And api request body field personal_data_processing is True
    And api request body field personal_data_use is True
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/is_active is False
    And logged active user attribute is_newsletter_receiver is False

  Scenario: Subscription cannot be created more than once for the same email address
    Given logged active user with email test@example.com and newsletter subscription enabled with code 119a8339-4400-4783-a048-bc66069b26a4
    When api request method is POST
    And api request header Accept-Language is pl
    And api request path is /1.0/auth/newsletter/subscribe/
    And api request body field email is test@example.com
    And api request body field personal_data_processing is True
    And api request body field personal_data_use is True
    And send api request and fetch the response
    Then api's response status code is 403
    And api's response body field code is error
    And api's response body field title is Błędna akcja!
    And api's response body field description is Adres poczty elektronicznej już istnieje

  Scenario: Logged in user can unsubscribe from receiving of newsletter
    Given logged active user with email test@example.com and newsletter subscription enabled with code 119a8339-4400-4783-a048-bc66069b26a4
    When api request method is POST
    And api request header Accept-Language is pl
    And api request body field activation_code is 119a8339-4400-4783-a048-bc66069b26a4
    And api request path is /1.0/auth/newsletter/unsubscribe/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field data/attributes/email is test@example.com
    And api's response body field data/attributes/newsletter_subscription_info is Twój adres email został usunięty z naszej listy mailingowej
    And logged active user attribute is_newsletter_receiver is False
