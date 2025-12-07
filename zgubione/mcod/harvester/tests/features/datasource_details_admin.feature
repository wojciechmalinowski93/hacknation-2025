Feature: DataSource details page in admin panel

  Scenario: User can create CKAN datasource
    Given category created with params {"id": 999, "title": "Moja kategoria", "title_en": "My category", "description": "Opis kategorii"}
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["test ckan datasource"], "description": ["ckan description"], "source_type": ["ckan"], "api_url": ["http://api.example.com/res.json"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "categories": ["999"]}
    And admin's harvester page /harvester/datasource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test ckan datasource</a>" zostało pomyślnie dodane.

  Scenario: User can view CKAN datasource details
    Given active ckan_datasource with id 100 for data {"name": "Viewed datasource", "api_url": ["http://api.example.com/res.json"]}
    When admin's harvester page /harvester/datasource/100/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Viewed datasource

  Scenario: User can edit CKAN datasource details
    Given category created with params {"id": 999, "title": "Moja kategoria", "title_en": "My category", "description": "Opis kategorii"}
    And active ckan_datasource with id 100 for data {"name": "Viewed datasource", "description": "ckan description", "source_type": "ckan", "api_url": "http://api.example.com/res.json", "frequency_in_days": "7", "status":"inactive", "emails": "test@test.com", "category_id": 999}
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["Changed Name datasource"], "description": ["ckan description"], "source_type": ["ckan"], "api_url": ["http://api.example.com/res.json"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "categories": ["999"]}
    And admin's harvester page /harvester/datasource/100/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Changed Name datasource</a>" zostało pomyślnie zmienione.

  Scenario: User can create XML datasource
    Given institution with id 999
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["test xml datasource"], "description": ["xml description"], "source_type": ["xml"], "xml_url": ["http://api.example.com/res.xml"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "organization": ["999"] }
    And admin's harvester page /harvester/datasource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test xml datasource</a>" zostało pomyślnie dodane.

  Scenario: User can view XML datasource
    Given institution with id 999
    And active xml_datasource with id 100 for data {"name": "Viewed xml datasource"}
    When admin's harvester page /harvester/datasource/100/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Viewed xml datasource

  Scenario: User can edit XML datasource details
    Given institution with id 999
    And active xml_datasource with id 100 for data {"name": "Viewed xml datasource", "description": "xml description", "source_type": "xml", "xml_url": "http://api.example.com/res.xml", "frequency_in_days": "7", "status":"inactive", "emails": "test@test.com", "organization_id": 999}
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["Changed xml datasource"], "description": ["xml description"], "source_type": ["xml"], "xml_url": ["http://api.example.com/res.xml"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "organization": ["999"] }
    And admin's harvester page /harvester/datasource/100/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Changed xml datasource</a>" zostało pomyślnie zmienione.

  Scenario: User can create DCAT datasource
    Given institution with id 999
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["test dcat datasource"], "description": ["dcat description"], "source_type": ["dcat"], "api_url": ["http://api.example.com/dcat/endpoint"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "organization": ["999"], "sparql_query": ["SELECT * WHERE {?s <some.uri/with/id> ?o}"] }
    And admin's harvester page /harvester/datasource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">test dcat datasource</a>" zostało pomyślnie dodane.

  Scenario: User cant create DCAT datasource without sparql query
    Given institution with id 999
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["test dcat datasource"], "description": ["dcat description"], "source_type": ["dcat"], "api_url": ["http://api.example.com/dcat/endpoint"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "organization": ["999"] }
    And admin's harvester page /harvester/datasource/add/ is requested
    Then admin's response status code is 200
    And admin's response page contains Zapytanie SPARQL:</label></div><div class="controls"><div class="inline error errors">

  Scenario: User can view DCAT datasource
    Given institution with id 999
    And active dcat_datasource with id 100 for data {"name": "Viewed dcat datasource"}
    When admin's harvester page /harvester/datasource/100/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains Viewed dcat datasource

  Scenario: User can edit DCAT datasource details
    Given institution with id 999
    And active dcat_datasource with id 100 for data {"name": "Viewed dcat datasource", "description": "dcat description", "source_type": "dcat", "api_url": "http://api.example.com/dcat/endpoint", "frequency_in_days": "7", "status":"inactive", "emails": "test@test.com", "organization_id": 999, "sparql_query": "SELECT * WHERE {?s <some.uri/with/id> ?o}"}
    When admin's request method is POST
    And admin's request posted datasource data is {"name": ["Changed dcat datasource"], "description": ["dcat description"], "source_type": ["dcat"], "api_url": ["http://api.example.com/dcat/endpoint"], "frequency_in_days": ["7"], "status":["inactive"], "emails": ["test@test.com"], "organization": ["999"] }
    And admin's harvester page /harvester/datasource/100/change/ is requested
    Then admin's response status code is 200
    And admin's response page contains /change/">Changed dcat datasource</a>" zostało pomyślnie zmienione.
