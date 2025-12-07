Feature: Resource RDF API
  Scenario Outline: Test that resource RDF endpoint returns data in format specified in url.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    # the next line is added to disable json api validation of response during test.
    When api request header x-api-version is 1.0
    And api request path is <request_path>
    And send api request and fetch the response
    Then api's response status code is 200
    And api's response header <resp_header_name> is <resp_header_value>

    Examples:
    | request_path                                       | resp_header_name | resp_header_value     |
    | /catalog/dataset/999/resource/999                  | content-type     | application/ld+json   |
    | /catalog/dataset/999/resource/999.jsonld           | content-type     | application/ld+json   |
    | /catalog/dataset/999/resource/999.n3               | content-type     | text/n3               |
    | /catalog/dataset/999/resource/999.nt               | content-type     | application/n-triples |
    | /catalog/dataset/999/resource/999.ntriples         | content-type     | application/n-triples |
    | /catalog/dataset/999/resource/999.nt11             | content-type     | application/n-triples |
    | /catalog/dataset/999/resource/999.nquads           | content-type     | application/n-quads   |
    | /catalog/dataset/999/resource/999.ttl              | content-type     | text/turtle           |
    | /catalog/dataset/999/resource/999.turtle           | content-type     | text/turtle           |
    | /catalog/dataset/999/resource/999.rdf              | content-type     | application/rdf+xml   |
    | /catalog/dataset/999/resource/999.trig             | content-type     | application/trig      |
    | /catalog/dataset/999/resource/999.trix             | content-type     | application/trix      |
    | /catalog/dataset/999/resource/999.xml              | content-type     | application/rdf+xml   |
    # with optional slug in url.
    | /catalog/dataset/999/resource/999,test-rdf         | content-type     | application/ld+json   |
    | /catalog/dataset/999/resource/999,test-rdf.jsonld  | content-type     | application/ld+json   |
    | /catalog/dataset/999/resource/999,test-rdf.n3      | content-type     | text/n3               |
    | /catalog/dataset/999/resource/999,test-rdf.nt      | content-type     | application/n-triples |
    | /catalog/dataset/999/resource/999,test-rdf.ntriples| content-type     | application/n-triples |
    | /catalog/dataset/999/resource/999,test-rdf.nt11    | content-type     | application/n-triples |
    | /catalog/dataset/999/resource/999,test-rdf.nquads  | content-type     | application/n-quads   |
    | /catalog/dataset/999/resource/999,test-rdf.ttl     | content-type     | text/turtle           |
    | /catalog/dataset/999/resource/999,test-rdf.turtle  | content-type     | text/turtle           |
    | /catalog/dataset/999/resource/999,test-rdf.rdf     | content-type     | application/rdf+xml   |
    | /catalog/dataset/999/resource/999,test-rdf.trig    | content-type     | application/trig      |
    | /catalog/dataset/999/resource/999,test-rdf.trix    | content-type     | application/trix      |
    | /catalog/dataset/999/resource/999,test-rdf.xml     | content-type     | application/rdf+xml   |

  Scenario Outline: Test that resource RDF endpoint returns data in format specified as Accept HTML header.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    When api request header <req_header_name> is <req_header_value>
    # the next line is added to disable json api validation of response during test.
    And api request header x-api-version is 1.0
    And api request path is /catalog/dataset/999/resource/999,test-rdf
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response header <resp_header_name> is <resp_header_value>

    Examples:
    | req_header_name | req_header_value      | resp_header_name | resp_header_value     |
    | Accept          | application/ld+json   | content-type     | application/ld+json   |
    | Accept          | text/n3               | content-type     | text/n3               |
    | Accept          | application/n-triples | content-type     | application/n-triples |
    | Accept          | application/n-quads   | content-type     | application/n-quads   |
    | Accept          | text/turtle           | content-type     | text/turtle           |
    | Accept          | application/rdf+xml   | content-type     | application/rdf+xml   |
    | Accept          | application/trix      | content-type     | application/trix      |

  Scenario: Test that RDF format passed in url is more significant than value of Accept header.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    When api request header Accept is application/n-triples
    # the next line is added to disable json api validation of response during test.
    And api request header x-api-version is 1.0
    And api request path is /catalog/dataset/999/resource/999,test-rdf.ttl
    Then send api request and fetch the response
    And api's response status code is 200
    And api's response header content-type is text/turtle

  Scenario: Test that RDF resource response has valid file-related vocabularies values set.
    Given dataset with id 999
    And resource created with params {"id": 999, "slug": "test-rdf", "dataset_id": 999}
    # the next line is added to disable json api validation of response during test.
    When api request header x-api-version is 1.0
    And api request path is /catalog/dataset/999/resource/999
    Then send api request and fetch the response
    And api's response status code is 200
    And api's jsonld response body with rdf type dcat:Distribution has field dct:format with attribute @id that equals http://publications.europa.eu/resource/authority/file-type/CSV
