Feature: Sparql API endpoint
  Scenario: Test that GET request for sparql endpoint returns list of namespaces
    When api request path is /sparql/
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field /data/[0]/type is namespace
    And api's response body has field /data/[0]/attributes/prefix
    And api's response body has field /data/[0]/attributes/url

  Scenario: Test that query parameter is required
    When api request method is POST
    # the next line is added to disable json api validation of response during the test.
    And api request header x-api-version is 1.0
    And api request path is /sparql/
    And api request sparql data has {"q": null}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/data/attributes/q is Pole nie może być puste.

  Scenario: Test that format parameter is required
    When api request method is POST
    # the next line is added to disable json api validation of response during the test.
    And api request header x-api-version is 1.0
    And api request path is /sparql/
    And api request sparql data has {"format": null}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/data/attributes/format is Pole nie może być puste.

  Scenario: Test that format parameter must be a value from predefined list of possible formats
    When api request method is POST
    # the next line is added to disable json api validation of response during the test.
    And api request header x-api-version is 1.0
    And api request path is /sparql/
    And api request sparql data has {"format": "txt"}
    And send api request and fetch the response
    Then api's response status code is 422
    And api's response body field errors/data/attributes/format is ['Nieobsługiwany format. Obsługiwane są: application/rdf+xml, text/turtle, text/csv, application/sparql-results+json, application/sparql-results+xml.']

  Scenario: Test that error is returned if passed query syntax is not valid
    When api request method is POST
    # the next line is added to disable json api validation of response during the test.
    And api request header x-api-version is 1.0
    And api request path is /sparql/
    And api request sparql data has {"q": "INVALID SYNTAX"}
    And send api request and fetch the response
    Then api's response status code is 400
    And api's response body field title is 400 Bad Request

  Scenario Outline: Test that response is ok for various requests
    Given dataset created with params {"id": 999, "slug": "sparql", "tags": ["test"]}
    When api request method is POST
    # the next line is added to disable json api validation of response during the test.
    And api request header x-api-version is 1.0
    And api request path is /sparql/
    And api request <object_type> data has <req_data>
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response body field <resp_body_field> is <resp_body_value>
    And api's response body has field data/attributes/result
    And api's response body has field data/attributes/download_url
    And api's response body has field data/attributes/content_type
    And api's response body has field data/attributes/has_previous
    And api's response body has field data/attributes/has_next
    And api's response body has field meta/count
    Examples:
    | object_type | req_data                                                                                                      | resp_body_field              | resp_body_value                  |
    # SELECT
    | sparql      | {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "application/rdf+xml"}                               | data/attributes/content_type | application/rdf+xml             |
    | sparql      | {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "application/rdf+xml", "external_sparql_endpoint": null}                               | data/attributes/content_type | application/rdf+xml             |
    | sparql      | {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "application/sparql-results+xml"}                    | data/attributes/content_type | application/sparql-results+xml  |
    | sparql      | {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "application/sparql-results+json"}                   | data/attributes/content_type | application/sparql-results+json |
    | sparql      | {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "text/csv"}                                          | data/attributes/content_type | text/csv                        |
    | sparql      | {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "text/turtle"}                                       | data/attributes/content_type | text/turtle                     |
    # ASK
    | sparql      | {"q": "ASK {?x <http://www.w3.org/ns/dcat#keyword> 'test'}", "format": "application/rdf+xml"}                 | data/attributes/content_type | application/rdf+xml             |
    | sparql      | {"q": "ASK {?x <http://www.w3.org/ns/dcat#keyword> 'test'}", "format": "application/sparql-results+xml"}      | data/attributes/content_type | application/sparql-results+xml  |
    | sparql      | {"q": "ASK {?x <http://www.w3.org/ns/dcat#keyword> 'test'}", "format": "application/sparql-results+json"}     | data/attributes/content_type | application/sparql-results+json |
    | sparql      | {"q": "ASK {?x <http://www.w3.org/ns/dcat#keyword> 'test'}", "format": "text/csv"}                            | data/attributes/content_type | text/csv                        |
    | sparql      | {"q": "ASK {?x <http://www.w3.org/ns/dcat#keyword> 'test'}", "format": "text/turtle"}                         | data/attributes/content_type | text/turtle                     |
    # DESCRIBE
    | sparql      | {"q": "DESCRIBE <http://test.mcod/pl/dataset/999,sparql>", "format": "application/rdf+xml"}                   | data/attributes/content_type | application/rdf+xml             |
    | sparql      | {"q": "DESCRIBE <http://test.mcod/pl/dataset/999,sparql>", "format": "text/turtle"}                           | data/attributes/content_type | text/turtle                     |
    # CONSTRUCT
    | sparql      | {"q": "CONSTRUCT {<http://test.mcod/pl/dataset/999,sparql> ?p ?o} WHERE { <http://test.mcod/pl/dataset/999,sparql> ?p ?o}", "format": "application/rdf+xml"} | data/attributes/content_type | application/rdf+xml |
    | sparql      | {"q": "CONSTRUCT {<http://test.mcod/pl/dataset/999,sparql> ?p ?o} WHERE { <http://test.mcod/pl/dataset/999,sparql> ?p ?o}", "format": "text/turtle"}         | data/attributes/content_type | text/turtle         |
