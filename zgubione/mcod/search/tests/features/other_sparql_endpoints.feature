Feature: Other providers SPARQL API feature

    Scenario: Response is ok for request to other sparql endpoint
    Given dataset created with params {"id": 999, "slug": "sparql", "tags": ["test"]}
    When api request method is POST
    # the next line is added to disable json api validation of response during the test.
    And api request header x-api-version is 1.0
    And api request path is /sparql/
    And api request sparql data has {"q": "SELECT * WHERE { ?s ?p ?o . } LIMIT 1", "format": "application/rdf+xml", "external_sparql_endpoint": "kronika"}
    And send api request and fetch the response with mocked_url http://kronik.gov.pl and mocked_rdf_data <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="http://www.w3.org/TR/rdf-syntax-grammar">RDF 1.1 XML Syntax</rdf:Description></rdf:RDF>
    Then api's response status code is 200
    And api's response body field data/attributes/content_type is application/rdf+xml
    And api's response body has field data/attributes/result
    And api's response body has field data/attributes/download_url
    And api's response body has field data/attributes/content_type
    And api's response body has field data/attributes/has_previous
    And api's response body has field data/attributes/has_next
    And api's response body has field meta/count
